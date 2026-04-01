"""Ridge regression points prediction model — v2.

Trained on historical GW data with 25+ features, predicts expected points
per player per fixture. Uses recency weighting and RidgeCV for alpha tuning.
"""

import logging
import threading
from decimal import Decimal

import numpy as np
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

MODEL_VERSION = "v2"

# Module-level model cache, guarded by _model_lock
_model_lock = threading.Lock()
_model: RidgeCV | None = None
_scaler: StandardScaler | None = None

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


def train_model() -> tuple[RidgeCV, StandardScaler]:
    """Train the ridge regression model on the last 6 gameweeks of data."""
    global _model, _scaler

    with sync_session_factory() as session:
        # Find the last 6 finished GWs
        finished_gws = (
            session.query(Gameweek.id)
            .filter(Gameweek.is_finished == True)  # noqa: E712
            .order_by(Gameweek.id.desc())
            .limit(6)
            .all()
        )
        recent_gw_ids = [gw[0] for gw in finished_gws]

        if not recent_gw_ids:
            logger.warning("No finished GWs, skipping model fit")
            return RidgeCV(), StandardScaler()

        gw_min = min(recent_gw_ids)
        gw_max = max(recent_gw_ids)

        # Train on all stats from recent GWs where player played
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

    x_rows: list[list[float]] = []
    y_rows: list[float] = []
    weights: list[float] = []

    for s in stats:
        player = players.get(s.player_id)
        form = form_cache.get(s.player_id)
        xg = xg_data.get(s.player_id)
        fixture = fixtures.get(s.fixture_id)

        if not player or not form:
            continue

        # Bug #7: skip players with low chance of playing
        cop = player.chance_of_playing_next_round
        if cop is not None and cop < 50:
            continue

        # Bug #2: skip players with < 50% minutes
        if form.minutes_pct < 50:
            continue

        is_home = 1.0 if fixture and fixture.home_team_id == player.team_id else 0.0
        fdr = (
            float(fixture.home_difficulty if is_home else fixture.away_difficulty)
            if fixture and fixture.home_difficulty is not None
            else 3.0
        )
        is_dgw = 1.0 if gw_double.get(s.gameweek_id) else 0.0

        # Team strength features
        team = teams.get(player.team_id)
        if is_home:
            team_attack = float(team.strength_attack_home) if team else 1000.0
        else:
            team_attack = float(team.strength_attack_away) if team else 1000.0

        opp_team_id = (
            fixture.away_team_id
            if is_home
            else fixture.home_team_id
            if fixture
            else None
        )
        opp_team = teams.get(opp_team_id) if opp_team_id else None
        if opp_team:
            opp_defence = (
                float(opp_team.strength_defence_away)
                if is_home
                else float(opp_team.strength_defence_home)
            )
        else:
            opp_defence = 1000.0

        features = _build_feature_vector(
            form, xg, player, fdr, is_home, is_dgw, team_attack, opp_defence
        )
        x_rows.append(features)
        y_rows.append(float(s.total_points))

        # Bug #6: recency weighting — most recent GW = 6x, oldest = 1x
        gw_range = gw_max - gw_min
        weight = (
            1 + 5 * (s.gameweek_id - gw_min) / gw_range
            if gw_range > 0
            else 1.0
        )
        weights.append(weight)

    if len(x_rows) < 100:
        logger.warning(
            "Not enough training data (%d rows), skipping model fit", len(x_rows)
        )
        return RidgeCV(), StandardScaler()

    x = np.array(x_rows)
    y = np.array(y_rows)
    w = np.array(weights)

    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)

    model = RidgeCV(alphas=[0.1, 0.5, 1.0, 5.0, 10.0])
    model.fit(x_scaled, y, sample_weight=w)

    with _model_lock:
        _model = model
        _scaler = scaler

    logger.info(
        "Points model v2 trained on %d samples from GWs %s, R²=%.3f, alpha=%.1f",
        len(x_rows),
        sorted(recent_gw_ids),
        model.score(x_scaled, y),
        model.alpha_,
    )
    return model, scaler


def predict_gw(gw_id: int) -> list[dict]:
    """Generate predicted points for all active players for a given GW."""
    if _model is None or _scaler is None:
        train_model()

    if _model is None or _scaler is None:
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
            .filter(Player.status == "a")
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
        # Bug #2: raised threshold from 20% to 50%
        if not form or form.minutes_pct < 50:
            continue

        # Bug #7: skip injured/doubtful players
        cop = player.chance_of_playing_next_round
        if cop is not None and cop < 50:
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

            features = np.array(
                [
                    _build_feature_vector(
                        form,
                        xg,
                        player,
                        fdr,
                        1.0 if is_home else 0.0,
                        1.0 if is_dgw else 0.0,
                        team_attack,
                        opp_defence,
                    )
                ]
            )
            features_scaled = _scaler.transform(features)
            pred = max(0, float(_model.predict(features_scaled)[0]))
            total_predicted += pred

        predictions.append(
            {
                "player_id": player.id,
                "web_name": player.web_name,
                "shirt_url": shirt_url(team_code, player.position),
                "team_short_name": team_short,
                "position": player.position,
                "predicted_points": round(Decimal(str(total_predicted)), 1),
                "now_cost": player.now_cost,
            }
        )

    predictions.sort(key=lambda p: float(p["predicted_points"]), reverse=True)
    return predictions


def predict_upcoming(horizon: int = 5) -> list[dict]:
    """Predict points across the next N upcoming gameweeks.

    Uses last-6-GW form data and fixture difficulty for each upcoming GW.
    Returns enriched dicts with per-GW breakdowns.
    """
    global _model, _scaler

    if _model is None or _scaler is None:
        train_model()

    if _model is None or _scaler is None:
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
            .filter(Player.status == "a")
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
        # Bug #2: raised threshold
        if not form or form.minutes_pct < 50:
            continue

        # Bug #7: skip injured/doubtful
        cop = player.chance_of_playing_next_round
        if cop is not None and cop < 50:
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

                features = np.array(
                    [
                        _build_feature_vector(
                            form,
                            xg,
                            player,
                            fdr,
                            1.0 if is_home else 0.0,
                            1.0 if is_dgw else 0.0,
                            team_attack,
                            opp_defence,
                        )
                    ]
                )
                features_scaled = _scaler.transform(features)
                pred = max(0, float(_model.predict(features_scaled)[0]))
                gw_predicted += pred

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
