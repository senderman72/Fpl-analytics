"""Lightweight ridge regression points prediction model.

Trained on historical GW data, predicts expected points per player per fixture.
Intentionally simple — 10 features, refit after each GW in under 1s.
"""

import logging
from decimal import Decimal

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from app.core.database import sync_session_factory
from app.models.fixture import Fixture
from app.models.gameweek import Gameweek
from app.models.player import Player
from app.models.player_form_cache import PlayerFormCache
from app.models.player_gw_stats import PlayerGWStats
from app.models.player_gw_xg import PlayerSeasonXG
from app.models.team import Team

logger = logging.getLogger(__name__)

FPL_SHIRTS = "https://fantasy.premierleague.com/dist/img/shirts/standard"

# Module-level model cache
_model: Ridge | None = None
_scaler: StandardScaler | None = None


def _shirt_url(team_code: int, position: int) -> str:
    if position == 1:  # GK
        return f"{FPL_SHIRTS}/shirt_{team_code}_1-110.webp"
    return f"{FPL_SHIRTS}/shirt_{team_code}-110.webp"


def train_model() -> tuple[Ridge, StandardScaler]:
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
            return Ridge(), StandardScaler()

        # Train only on last 6 GWs
        stats = (
            session.query(PlayerGWStats)
            .filter(
                PlayerGWStats.minutes > 0,
                PlayerGWStats.gameweek_id.in_(recent_gw_ids),
            )
            .all()
        )

        form_cache = {}
        for fc in (
            session.query(PlayerFormCache).filter(PlayerFormCache.gw_window == 6).all()
        ):
            form_cache[fc.player_id] = fc

        xg_data = {}
        for xg in session.query(PlayerSeasonXG).all():
            xg_data[xg.player_id] = xg

        players = {}
        for p in session.query(Player).all():
            players[p.id] = p

        # Get fixture info for home/away
        fixtures = {}
        for f in session.query(Fixture).all():
            fixtures[f.id] = f

        # Get DGW flags
        gw_double = {}
        for gw in session.query(Gameweek).all():
            gw_double[gw.id] = gw.is_double

    X_rows = []
    y_rows = []

    for s in stats:
        player = players.get(s.player_id)
        form = form_cache.get(s.player_id)
        xg = xg_data.get(s.player_id)
        fixture = fixtures.get(s.fixture_id)

        if not player or not form:
            continue

        xgi_per_90 = (
            float(xg.xgi / (Decimal(xg.minutes) / 90)) if xg and xg.minutes > 0 else 0
        )
        season_xgi = float(xg.xgi) if xg else 0
        is_home = 1.0 if fixture and fixture.home_team_id == player.team_id else 0.0
        fdr = (
            float(fixture.home_difficulty if is_home else fixture.away_difficulty)
            if fixture
            else 3.0
        )
        is_dgw = 1.0 if gw_double.get(s.gameweek_id) else 0.0

        features = [
            xgi_per_90,
            float(form.minutes_pct) / 100,  # xMins proxy
            fdr,
            is_home,
            0.5,  # CS probability placeholder
            float(form.bps_avg),
            is_dgw,
            float(s.saves) if player.position == 1 else 0,  # saves/90 for GK
            1.0 if player.is_penalty_taker or player.is_set_piece_taker else 0,
            season_xgi,
        ]
        X_rows.append(features)
        y_rows.append(float(s.total_points))

    if len(X_rows) < 100:
        logger.warning(
            "Not enough training data (%d rows), skipping model fit", len(X_rows)
        )
        return Ridge(), StandardScaler()

    X = np.array(X_rows)
    y = np.array(y_rows)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = Ridge(alpha=1.0)
    model.fit(X_scaled, y)

    _model = model
    _scaler = scaler

    logger.info(
        "Points model trained on %d samples from GWs %s, R²=%.3f",
        len(X_rows),
        sorted(recent_gw_ids),
        model.score(X_scaled, y),
    )
    return model, scaler


def predict_gw(gw_id: int) -> list[dict]:
    """Generate predicted points for all active players for a given GW."""
    global _model, _scaler

    if _model is None or _scaler is None:
        train_model()

    if _model is None:
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

        xg_data = {}
        for xg in session.query(PlayerSeasonXG).all():
            xg_data[xg.player_id] = xg

        # Get GW fixtures
        gw_fixtures = session.query(Fixture).filter(Fixture.gameweek_id == gw_id).all()

        gw_info = session.query(Gameweek).filter(Gameweek.id == gw_id).first()
        is_dgw = gw_info.is_double if gw_info else False

    # Map teams to fixtures
    team_fixtures: dict[int, list[Fixture]] = {}
    for f in gw_fixtures:
        team_fixtures.setdefault(f.home_team_id, []).append(f)
        team_fixtures.setdefault(f.away_team_id, []).append(f)

    predictions = []
    for player, team_short, team_code, form in players_data:
        if not form or form.minutes_pct < 20:
            continue

        xg = xg_data.get(player.id)
        xgi_per_90 = (
            float(xg.xgi / (Decimal(xg.minutes) / 90)) if xg and xg.minutes > 0 else 0
        )
        season_xgi = float(xg.xgi) if xg else 0

        player_fixtures = team_fixtures.get(player.team_id, [])
        if not player_fixtures:
            continue

        total_predicted = 0.0
        for fix in player_fixtures:
            is_home = fix.home_team_id == player.team_id
            fdr = (
                float(fix.home_difficulty if is_home else fix.away_difficulty)
                if fix
                else 3.0
            )

            features = np.array(
                [
                    [
                        xgi_per_90,
                        float(form.minutes_pct) / 100,
                        fdr,
                        1.0 if is_home else 0.0,
                        0.5,
                        float(form.bps_avg),
                        1.0 if is_dgw else 0.0,
                        0,  # saves placeholder
                        1.0
                        if player.is_penalty_taker or player.is_set_piece_taker
                        else 0,
                        season_xgi,
                    ]
                ]
            )
            features_scaled = _scaler.transform(features)
            pred = max(0, float(_model.predict(features_scaled)[0]))
            total_predicted += pred

        predictions.append(
            {
                "player_id": player.id,
                "web_name": player.web_name,
                "shirt_url": _shirt_url(team_code, player.position),
                "team_short_name": team_short,
                "position": player.position,
                "predicted_points": round(Decimal(str(total_predicted)), 1),
                "now_cost": player.now_cost,
            }
        )

    predictions.sort(key=lambda p: float(p["predicted_points"]), reverse=True)
    return predictions


def predict_upcoming(horizon: int = 5) -> list[dict]:
    """Predict points across the next N upcoming gameweeks (capped at remaining GWs).

    Uses last-6-GW form data and fixture difficulty for each upcoming GW.
    Returns enriched dicts with per-GW breakdowns.
    """
    global _model, _scaler

    if _model is None or _scaler is None:
        train_model()

    if _model is None:
        return []

    with sync_session_factory() as session:
        # Find upcoming GWs (unfinished, ordered)
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

        # Player data with 6-GW form
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

        xg_data = {}
        for xg in session.query(PlayerSeasonXG).all():
            xg_data[xg.player_id] = xg

        # Fixtures for all upcoming GWs
        all_fixtures = (
            session.query(Fixture)
            .filter(Fixture.gameweek_id.in_(gw_ids))
            .all()
        )

    # Map: gw_id -> team_id -> list[Fixture]
    gw_team_fixtures: dict[int, dict[int, list[Fixture]]] = {}
    for f in all_fixtures:
        gw_map = gw_team_fixtures.setdefault(f.gameweek_id, {})
        gw_map.setdefault(f.home_team_id, []).append(f)
        gw_map.setdefault(f.away_team_id, []).append(f)

    predictions = []
    for player, team_short, team_code, form in players_data:
        if not form or form.minutes_pct < 20:
            continue

        xg = xg_data.get(player.id)
        xgi_per_90 = (
            float(xg.xgi / (Decimal(xg.minutes) / 90)) if xg and xg.minutes > 0 else 0
        )
        season_xgi = float(xg.xgi) if xg else 0

        total_predicted = 0.0
        per_gw: list[dict] = []

        for gw_id in gw_ids:
            team_fixtures = gw_team_fixtures.get(gw_id, {})
            player_fixtures = team_fixtures.get(player.team_id, [])
            is_dgw = gw_double_map.get(gw_id, False)

            gw_predicted = 0.0
            for fix in player_fixtures:
                is_home = fix.home_team_id == player.team_id
                fdr = float(
                    fix.home_difficulty if is_home else fix.away_difficulty
                ) if fix.home_difficulty is not None else 3.0

                features = np.array(
                    [
                        [
                            xgi_per_90,
                            float(form.minutes_pct) / 100,
                            fdr,
                            1.0 if is_home else 0.0,
                            0.5,
                            float(form.bps_avg),
                            1.0 if is_dgw else 0.0,
                            0,
                            1.0
                            if player.is_penalty_taker or player.is_set_piece_taker
                            else 0,
                            season_xgi,
                        ]
                    ]
                )
                features_scaled = _scaler.transform(features)
                pred = max(0, float(_model.predict(features_scaled)[0]))
                gw_predicted += pred

            # Players with no fixtures in a GW (blank GW) score 0 for that GW
            per_gw.append({
                "gw_id": gw_id,
                "predicted_points": round(Decimal(str(gw_predicted)), 1),
            })
            total_predicted += gw_predicted

        if total_predicted == 0.0:
            continue

        predictions.append(
            {
                "player_id": player.id,
                "web_name": player.web_name,
                "shirt_url": _shirt_url(team_code, player.position),
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
