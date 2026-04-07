"""Ridge regression points prediction model — v2.

Trained on historical GW data with 25+ features, predicts expected points
per player per fixture. Uses recency weighting and RidgeCV for alpha tuning.
"""

import logging
import threading
from decimal import Decimal

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.preprocessing import StandardScaler

from app.core.database import sync_session_factory
from app.models.fixture import Fixture
from app.models.gameweek import Gameweek
from app.models.player import Player
from app.models.player_form_cache import PlayerFormCache
from app.models.player_gw_stats import PlayerGWStats
from app.models.player_gw_xg import PlayerSeasonXG
from app.models.prediction_log import PredictionLog
from app.models.team import Team
from app.services.fpl_urls import shirt_url

logger = logging.getLogger(__name__)

MODEL_VERSION = "v3.1"

# Position IDs: 1=GK, 2=DEF, 3=MID, 4=FWD
_POSITIONS = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

# Statuses eligible for predictions — active + doubtful with valid chance
_ELIGIBLE_STATUSES = {"a", "d"}


def _should_include_player(
    status: str,
    chance: int | None,
    minutes_pct: float,
) -> bool:
    """Determine if a player should receive predictions.

    Includes active players and doubtful players with chance >= 50.
    Excludes unavailable, injured, suspended, and low-minutes players.
    """
    if minutes_pct < 50:
        return False
    if status == "a":
        return True
    return status == "d" and chance is not None and chance >= 50


# Module-level model cache, guarded by _model_lock
# Maps position (1-4) → (model, scaler) pairs
_model_lock = threading.Lock()
_models: dict[int, RidgeCV] = {}
_scalers: dict[int, StandardScaler] = {}
# Fallback single model for positions with too few samples
_model: RidgeCV | None = None
_scaler: StandardScaler | None = None
# HGBR ensemble — same pattern per position + fallback
_hgbr_models: dict[int, HistGradientBoostingRegressor] = {}
_hgbr_model: HistGradientBoostingRegressor | None = None

# Canonical feature order — train and predict MUST match exactly
_FEATURE_NAMES: list[str] = [
    # Form features (6-GW window)
    "pts_per_90",
    "pts_per_game",
    "minutes_pct",
    "goal_rate",
    "assist_rate",
    "bps_avg",
    "ict_avg",
    "threat_avg",
    "creativity_avg",
    "cs_rate",
    "saves_avg",
    "goals_conceded_avg",
    # xG features (season per-90 rates)
    "xgi_per_90",
    "npxg_per_90",
    "key_passes_per_90",
    "xg_chain_per_90",
    # FPL signals
    "ep_next",
    "form_fpl",
    "chance_of_playing",
    "selected_by_percent",
    # Fixture context
    "fdr",
    "is_home",
    "is_dgw",
    "team_attack_strength",
    "opponent_defence_strength",
    # Player attributes
    "is_penalty_taker",
    "is_set_piece_taker",
]


def _build_xg_rates(xg: PlayerSeasonXG | None) -> tuple[float, float, float, float]:
    """Extract per-90 xG rates from season data."""
    if not xg or not xg.minutes or xg.minutes <= 0:
        return 0.0, 0.0, 0.0, 0.0
    mins_90 = float(Decimal(xg.minutes) / 90)
    xgi_per_90 = float(xg.xgi) / mins_90
    npxg_per_90 = float(xg.npxg) / mins_90
    kp_per_90 = float(xg.key_passes) / mins_90
    xgc_per_90 = float(xg.xg_chain) / mins_90
    return xgi_per_90, npxg_per_90, kp_per_90, xgc_per_90


def _build_form_features(form: PlayerFormCache) -> list[float]:
    """Extract form-window features from cache."""
    ppg = float(form.pts_per_game)
    games = max(1, form.total_points / ppg) if ppg > 0 else 1
    return [
        float(form.pts_per_90),
        float(form.pts_per_game),
        float(form.minutes_pct) / 100,
        float(form.goals) / games,
        float(form.assists) / games,
        float(form.bps_avg),
        float(form.ict_avg),
        float(form.threat_avg),
        float(form.creativity_avg),
        float(form.clean_sheets) / games,
        float(form.saves_avg),
        float(form.goals_conceded_avg),
    ]


def _build_feature_vector(
    form: PlayerFormCache,
    xg: PlayerSeasonXG | None,
    player: Player,
    fdr: float,
    is_home: float,
    is_dgw: float,
    team_attack: float,
    opp_defence: float,
) -> list[float]:
    """Build the full 27-feature vector for one player-fixture pair."""
    xgi_90, npxg_90, kp_90, xgc_90 = _build_xg_rates(xg)
    form_feats = _build_form_features(form)

    features = [
        *form_feats,
        # xG rates
        xgi_90,
        npxg_90,
        kp_90,
        xgc_90,
        # FPL signals
        float(player.ep_next or 0),
        float(player.form or 0),
        float(player.chance_of_playing_next_round or 100),
        float(player.selected_by_percent),
        # Fixture context
        fdr,
        is_home,
        is_dgw,
        team_attack,
        opp_defence,
        # Player attributes
        1.0 if player.is_penalty_taker else 0.0,
        1.0 if player.is_set_piece_taker else 0.0,
    ]
    assert len(features) == len(_FEATURE_NAMES), (
        f"Feature count mismatch: {len(features)} vs {len(_FEATURE_NAMES)}"
    )
    return features


def _collect_training_data() -> tuple[
    dict[int, list[list[float]]],
    dict[int, list[float]],
    dict[int, list[float]],
    list[list[float]],
    list[float],
    list[float],
    list[int],
]:
    """Collect and split training data by position.

    Returns per-position X/y/weights and combined X/y/weights plus GW IDs.
    """
    with sync_session_factory() as session:
        finished_gws = (
            session.query(Gameweek.id)
            .filter(Gameweek.is_finished == True)  # noqa: E712
            .order_by(Gameweek.id.desc())
            .limit(6)
            .all()
        )
        recent_gw_ids = [gw[0] for gw in finished_gws]

        if not recent_gw_ids:
            return {}, {}, {}, [], [], [], []

        stats = (
            session.query(PlayerGWStats)
            .filter(
                PlayerGWStats.minutes > 0,
                PlayerGWStats.gameweek_id.in_(recent_gw_ids),
            )
            .all()
        )

        form_cache: dict[int, PlayerFormCache] = {}
        for fc in (
            session.query(PlayerFormCache)
            .filter(PlayerFormCache.gw_window == 6)
            .all()
        ):
            form_cache[fc.player_id] = fc

        xg_data: dict[int, PlayerSeasonXG] = {}
        for xg in session.query(PlayerSeasonXG).all():
            xg_data[xg.player_id] = xg

        players: dict[int, Player] = {}
        for p in session.query(Player).all():
            players[p.id] = p

        fixtures: dict[int, Fixture] = {}
        for f in session.query(Fixture).all():
            fixtures[f.id] = f

        teams: dict[int, Team] = {}
        for t in session.query(Team).all():
            teams[t.id] = t

        gw_double: dict[int, bool] = {}
        for gw in session.query(Gameweek).all():
            gw_double[gw.id] = gw.is_double

    gw_min = min(recent_gw_ids)
    gw_max = max(recent_gw_ids)

    # Split by position
    pos_x: dict[int, list[list[float]]] = {i: [] for i in range(1, 5)}
    pos_y: dict[int, list[float]] = {i: [] for i in range(1, 5)}
    pos_w: dict[int, list[float]] = {i: [] for i in range(1, 5)}
    all_x: list[list[float]] = []
    all_y: list[float] = []
    all_w: list[float] = []

    for s in stats:
        player = players.get(s.player_id)
        form = form_cache.get(s.player_id)
        xg = xg_data.get(s.player_id)
        fixture = fixtures.get(s.fixture_id)

        if not player or not form or form.minutes_pct < 50:
            continue

        is_home = (
            1.0
            if fixture and fixture.home_team_id == player.team_id
            else 0.0
        )
        fdr = (
            float(
                fixture.home_difficulty if is_home else fixture.away_difficulty,
            )
            if fixture and fixture.home_difficulty is not None
            else 3.0
        )
        is_dgw = 1.0 if gw_double.get(s.gameweek_id) else 0.0

        team = teams.get(player.team_id)
        if is_home:
            team_attack = (
                float(team.strength_attack_home) if team else 1000.0
            )
        else:
            team_attack = (
                float(team.strength_attack_away) if team else 1000.0
            )

        opp_team_id = (
            fixture.away_team_id
            if is_home
            else fixture.home_team_id
            if fixture
            else None
        )
        opp_team = teams.get(opp_team_id) if opp_team_id else None
        opp_defence = (
            float(
                opp_team.strength_defence_away
                if is_home
                else opp_team.strength_defence_home,
            )
            if opp_team
            else 1000.0
        )

        features = _build_feature_vector(
            form, xg, player, fdr, is_home, is_dgw,
            team_attack, opp_defence,
        )
        target = float(s.total_points)

        gw_range = gw_max - gw_min
        weight = (
            1 + 5 * (s.gameweek_id - gw_min) / gw_range
            if gw_range > 0
            else 1.0
        )

        pos = player.position
        pos_x[pos].append(features)
        pos_y[pos].append(target)
        pos_w[pos].append(weight)

        all_x.append(features)
        all_y.append(target)
        all_w.append(weight)

    return pos_x, pos_y, pos_w, all_x, all_y, all_w, recent_gw_ids


def _fit_ridge(
    x_rows: list[list[float]],
    y_rows: list[float],
    weights: list[float],
) -> tuple[RidgeCV, StandardScaler] | None:
    """Fit a RidgeCV model. Returns None if insufficient data."""
    if len(x_rows) < 30:
        return None
    x = np.array(x_rows)
    y = np.array(y_rows)
    w = np.array(weights)
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)
    model = RidgeCV(alphas=[0.1, 0.5, 1.0, 5.0, 10.0])
    model.fit(x_scaled, y, sample_weight=w)
    return model, scaler


_HGBR_MIN_SAMPLES = 100


def _fit_hgbr(
    x_rows: list[list[float]],
    y_rows: list[float],
    weights: list[float],
) -> HistGradientBoostingRegressor | None:
    """Fit a HistGradientBoostingRegressor. None if insufficient data.

    Requires more samples than Ridge because tree splits need
    enough data per leaf (min_samples_leaf=10, max_depth=4).
    """
    if len(x_rows) < _HGBR_MIN_SAMPLES:
        return None
    x = np.array(x_rows)
    y = np.array(y_rows)
    w = np.array(weights)
    model = HistGradientBoostingRegressor(
        max_iter=200,
        max_depth=4,
        learning_rate=0.1,
        min_samples_leaf=10,
        random_state=42,
    )
    model.fit(x, y, sample_weight=w)
    return model


def train_model() -> None:
    """Train position-specific Ridge models + a fallback global model."""
    global _model, _scaler, _models, _scalers, _hgbr_models, _hgbr_model

    (
        pos_x, pos_y, pos_w,
        all_x, all_y, all_w,
        recent_gw_ids,
    ) = _collect_training_data()

    if not recent_gw_ids or len(all_x) < 100:
        logger.warning(
            "Not enough training data (%d rows), skipping",
            len(all_x),
        )
        return

    # Train per-position models
    new_models: dict[int, RidgeCV] = {}
    new_scalers: dict[int, StandardScaler] = {}

    for pos in range(1, 5):
        result = _fit_ridge(pos_x[pos], pos_y[pos], pos_w[pos])
        if result:
            m, s = result
            r2 = m.score(s.transform(np.array(pos_x[pos])), np.array(pos_y[pos]))
            new_models[pos] = m
            new_scalers[pos] = s
            logger.info(
                "Model %s trained: %d samples, R²=%.3f, alpha=%.1f",
                _POSITIONS[pos],
                len(pos_x[pos]),
                r2,
                m.alpha_,
            )
        else:
            logger.warning(
                "Not enough data for %s (%d samples), using fallback",
                _POSITIONS[pos],
                len(pos_x[pos]),
            )

    # Train HGBR per-position models
    new_hgbr: dict[int, HistGradientBoostingRegressor] = {}
    for pos in range(1, 5):
        hgbr = _fit_hgbr(pos_x[pos], pos_y[pos], pos_w[pos])
        if hgbr:
            new_hgbr[pos] = hgbr
            x_pos = np.array(pos_x[pos])
            y_pos = np.array(pos_y[pos])
            r2 = hgbr.score(x_pos, y_pos)
            logger.info(
                "HGBR %s trained: %d samples, R²=%.3f",
                _POSITIONS[pos],
                len(pos_x[pos]),
                r2,
            )

    # Train global fallbacks (Ridge + HGBR)
    fallback = _fit_ridge(all_x, all_y, all_w)
    if not fallback:
        return

    fb_model, fb_scaler = fallback
    fb_hgbr = _fit_hgbr(all_x, all_y, all_w)

    r2 = fb_model.score(
        fb_scaler.transform(np.array(all_x)), np.array(all_y),
    )
    logger.info(
        "Fallback Ridge trained: %d samples from GWs %s, R²=%.3f",
        len(all_x),
        sorted(recent_gw_ids),
        r2,
    )

    with _model_lock:
        _models = new_models
        _scalers = new_scalers
        _model = fb_model
        _scaler = fb_scaler
        _hgbr_models = new_hgbr
        _hgbr_model = fb_hgbr


def _get_model_for_position(
    pos: int,
) -> tuple[RidgeCV, StandardScaler] | None:
    """Return the position-specific model or the global fallback."""
    if pos in _models and pos in _scalers:
        return _models[pos], _scalers[pos]
    if _model is not None and _scaler is not None:
        return _model, _scaler
    return None


def _predict_one(
    pos: int, features: list[float],
) -> float:
    """Predict points using Ridge+HGBR ensemble (averaged).

    Falls back to Ridge-only if no HGBR is available.
    """
    ridge_pair = _get_model_for_position(pos)
    if ridge_pair is None:
        return 0.0

    ridge_model, scaler = ridge_pair
    x_raw = np.array([features])
    x_scaled = scaler.transform(x_raw)
    ridge_pred = float(ridge_model.predict(x_scaled)[0])

    # Only blend HGBR when it matches the Ridge specificity level:
    # position-specific HGBR with position-specific Ridge, or
    # global HGBR fallback with global Ridge fallback.
    has_pos_ridge = pos in _models
    hgbr = _hgbr_models.get(pos) if has_pos_ridge else _hgbr_model
    if hgbr is not None:
        hgbr_pred = float(hgbr.predict(x_raw)[0])
        return max(0, (ridge_pred + hgbr_pred) / 2)

    return max(0, ridge_pred)


def get_model_diagnostics() -> dict | None:
    """Return model diagnostics for inspection."""
    if _model is None or _scaler is None:
        return None

    per_position = {}
    for pos in range(1, 5):
        if pos in _models:
            m = _models[pos]
            coefs = dict(
                zip(
                    _FEATURE_NAMES,
                    [round(float(c), 4) for c in m.coef_],
                    strict=True,
                )
            )
            per_position[_POSITIONS[pos]] = {
                "alpha": round(float(m.alpha_), 2),
                "coefficients": coefs,
            }

    fallback_coefs = dict(
        zip(
            _FEATURE_NAMES,
            [round(float(c), 4) for c in _model.coef_],
            strict=True,
        )
    )
    hgbr_per_position: dict[str, str] = {}
    for pos in range(1, 5):
        if pos in _hgbr_models:
            hgbr_per_position[_POSITIONS[pos]] = "trained"

    return {
        "model_version": MODEL_VERSION,
        "ensemble": bool(_hgbr_models or _hgbr_model),
        "n_features": len(_FEATURE_NAMES),
        "feature_names": _FEATURE_NAMES,
        "fallback_alpha": round(float(_model.alpha_), 2),
        "fallback_coefficients": fallback_coefs,
        "position_models": per_position,
        "hgbr_position_models": hgbr_per_position,
    }


def _ensure_trained() -> bool:
    """Ensure at least the fallback model is trained."""
    if _model is None or _scaler is None:
        train_model()
    return _model is not None and _scaler is not None


def predict_gw(gw_id: int) -> list[dict]:
    """Generate predicted points for all active players for a given GW."""
    if not _ensure_trained():
        return []

    with sync_session_factory() as session:
        players_data = (
            session.query(Player, Team.short_name, Team.code, PlayerFormCache)
            .join(Team, Player.team_id == Team.id)
            .outerjoin(
                PlayerFormCache,
                (PlayerFormCache.player_id == Player.id)
                & (PlayerFormCache.gw_window == 6),
            )
            .filter(Player.status.in_(_ELIGIBLE_STATUSES))
            .all()
        )

        xg_data: dict[int, PlayerSeasonXG] = {}
        for xg in session.query(PlayerSeasonXG).all():
            xg_data[xg.player_id] = xg

        gw_fixtures = session.query(Fixture).filter(Fixture.gameweek_id == gw_id).all()
        gw_info = session.query(Gameweek).filter(Gameweek.id == gw_id).first()
        is_dgw = gw_info.is_double if gw_info else False

        teams: dict[int, Team] = {}
        for t in session.query(Team).all():
            teams[t.id] = t

    # Map teams to fixtures
    team_fixtures: dict[int, list[Fixture]] = {}
    for f in gw_fixtures:
        team_fixtures.setdefault(f.home_team_id, []).append(f)
        team_fixtures.setdefault(f.away_team_id, []).append(f)

    predictions = []
    for player, team_short, team_code, form in players_data:
        if not form or not _should_include_player(
            status=player.status,
            chance=player.chance_of_playing_next_round,
            minutes_pct=float(form.minutes_pct),
        ):
            continue

        xg = xg_data.get(player.id)
        player_fixtures = team_fixtures.get(player.team_id, [])
        if not player_fixtures:
            continue

        total_predicted = 0.0
        for fix in player_fixtures:
            is_home = fix.home_team_id == player.team_id
            fdr = (
                float(fix.home_difficulty if is_home else fix.away_difficulty)
                if fix.home_difficulty is not None
                else 3.0
            )

            team = teams.get(player.team_id)
            if is_home:
                team_attack = float(team.strength_attack_home) if team else 1000.0
            else:
                team_attack = float(team.strength_attack_away) if team else 1000.0

            opp_team_id = fix.away_team_id if is_home else fix.home_team_id
            opp_team = teams.get(opp_team_id)
            if opp_team:
                opp_defence = (
                    float(opp_team.strength_defence_away)
                    if is_home
                    else float(opp_team.strength_defence_home)
                )
            else:
                opp_defence = 1000.0

            fv = _build_feature_vector(
                form, xg, player, fdr,
                1.0 if is_home else 0.0,
                1.0 if is_dgw else 0.0,
                team_attack, opp_defence,
            )
            total_predicted += _predict_one(player.position, fv)

        predictions.append(
            {
                "player_id": player.id,
                "web_name": player.web_name,
                "shirt_url": shirt_url(team_code, player.position),
                "team_short_name": team_short,
                "position": player.position,
                "predicted_points": round(
                    Decimal(str(total_predicted)), 1,
                ),
                "now_cost": player.now_cost,
            }
        )

    predictions.sort(
        key=lambda p: float(p["predicted_points"]), reverse=True,
    )
    return predictions


def predict_upcoming(horizon: int = 5) -> list[dict]:
    """Predict points across the next N upcoming gameweeks.

    Uses last-6-GW form data and fixture difficulty for each upcoming GW.
    Returns enriched dicts with per-GW breakdowns.
    """
    if not _ensure_trained():
        return []

    with sync_session_factory() as session:
        upcoming_gws = (
            session.query(Gameweek)
            .filter(Gameweek.is_finished == False)  # noqa: E712
            .order_by(Gameweek.id)
            .limit(horizon)
            .all()
        )

        if not upcoming_gws:
            return []

        gw_ids = [gw.id for gw in upcoming_gws]
        gw_double_map = {gw.id: gw.is_double for gw in upcoming_gws}
        actual_horizon = len(gw_ids)

        players_data = (
            session.query(Player, Team.short_name, Team.code, PlayerFormCache)
            .join(Team, Player.team_id == Team.id)
            .outerjoin(
                PlayerFormCache,
                (PlayerFormCache.player_id == Player.id)
                & (PlayerFormCache.gw_window == 6),
            )
            .filter(Player.status.in_(_ELIGIBLE_STATUSES))
            .all()
        )

        xg_data: dict[int, PlayerSeasonXG] = {}
        for xg in session.query(PlayerSeasonXG).all():
            xg_data[xg.player_id] = xg

        all_fixtures = (
            session.query(Fixture).filter(Fixture.gameweek_id.in_(gw_ids)).all()
        )

        teams: dict[int, Team] = {}
        for t in session.query(Team).all():
            teams[t.id] = t

    # Map: gw_id -> team_id -> list[Fixture]
    gw_team_fixtures: dict[int, dict[int, list[Fixture]]] = {}
    for f in all_fixtures:
        gw_map = gw_team_fixtures.setdefault(f.gameweek_id, {})
        gw_map.setdefault(f.home_team_id, []).append(f)
        gw_map.setdefault(f.away_team_id, []).append(f)

    predictions = []
    for player, team_short, team_code, form in players_data:
        if not form or not _should_include_player(
            status=player.status,
            chance=player.chance_of_playing_next_round,
            minutes_pct=float(form.minutes_pct),
        ):
            continue

        xg = xg_data.get(player.id)

        total_predicted = 0.0
        per_gw: list[dict] = []

        for gw_id in gw_ids:
            team_fix_map = gw_team_fixtures.get(gw_id, {})
            player_fixtures = team_fix_map.get(player.team_id, [])
            is_dgw = gw_double_map.get(gw_id, False)

            gw_predicted = 0.0
            for fix in player_fixtures:
                is_home = fix.home_team_id == player.team_id
                fdr = (
                    float(fix.home_difficulty if is_home else fix.away_difficulty)
                    if fix.home_difficulty is not None
                    else 3.0
                )

                team = teams.get(player.team_id)
                if is_home:
                    team_attack = (
                        float(team.strength_attack_home) if team else 1000.0
                    )
                else:
                    team_attack = (
                        float(team.strength_attack_away) if team else 1000.0
                    )

                opp_team_id = fix.away_team_id if is_home else fix.home_team_id
                opp_team = teams.get(opp_team_id)
                if opp_team:
                    opp_defence = (
                        float(opp_team.strength_defence_away)
                        if is_home
                        else float(opp_team.strength_defence_home)
                    )
                else:
                    opp_defence = 1000.0

                fv = _build_feature_vector(
                    form, xg, player, fdr,
                    1.0 if is_home else 0.0,
                    1.0 if is_dgw else 0.0,
                    team_attack, opp_defence,
                )
                gw_predicted += _predict_one(player.position, fv)

            per_gw.append(
                {
                    "gw_id": gw_id,
                    "predicted_points": round(Decimal(str(gw_predicted)), 1),
                }
            )
            total_predicted += gw_predicted

        if total_predicted == 0.0:
            continue

        predictions.append(
            {
                "player_id": player.id,
                "web_name": player.web_name,
                "shirt_url": shirt_url(team_code, player.position),
                "team_short_name": team_short,
                "position": player.position,
                "predicted_points": round(Decimal(str(total_predicted)), 1),
                "predicted_per_gw": per_gw,
                "horizon": actual_horizon,
                "now_cost": player.now_cost,
            }
        )

    predictions.sort(key=lambda p: float(p["predicted_points"]), reverse=True)
    return predictions


def store_prediction_logs(
    predictions: list[dict], gw_id: int
) -> int:
    """Store prediction results in PredictionLog for accuracy tracking."""
    from sqlalchemy.dialects.postgresql import insert

    rows = [
        {
            "player_id": p["player_id"],
            "gameweek_id": gw_id,
            "predicted_points": p["predicted_points"],
            "position": p["position"],
            "model_version": MODEL_VERSION,
        }
        for p in predictions
    ]

    if not rows:
        return 0

    with sync_session_factory() as session:
        stmt = insert(PredictionLog).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_predlog_player_gw_ver",
            set_={
                "predicted_points": stmt.excluded.predicted_points,
            },
        )
        session.execute(stmt)
        session.commit()

    logger.info("Stored %d prediction logs for GW %d", len(rows), gw_id)
    return len(rows)
