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

# Module-level model cache
_model: Ridge | None = None
_scaler: StandardScaler | None = None


def train_model() -> tuple[Ridge, StandardScaler]:
    """Train (or retrain) the ridge regression model on all historical GW data."""
    global _model, _scaler

    with sync_session_factory() as session:
        # Get all GW stats with form and xG data
        stats = session.query(PlayerGWStats).filter(
            PlayerGWStats.minutes > 0
        ).all()

        form_cache = {}
        for fc in session.query(PlayerFormCache).filter(
            PlayerFormCache.gw_window == 6
        ).all():
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

        xgi_per_90 = float(xg.xgi / (Decimal(xg.minutes) / 90)) if xg and xg.minutes > 0 else 0
        season_xgi = float(xg.xgi) if xg else 0
        is_home = 1.0 if fixture and fixture.home_team_id == player.team_id else 0.0
        fdr = float(fixture.home_difficulty if is_home else fixture.away_difficulty) if fixture else 3.0
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
        logger.warning("Not enough training data (%d rows), skipping model fit", len(X_rows))
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
        "Points model trained on %d samples, R²=%.3f",
        len(X_rows), model.score(X_scaled, y),
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
            session.query(Player, Team.short_name, PlayerFormCache)
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
        gw_fixtures = session.query(Fixture).filter(
            Fixture.gameweek_id == gw_id
        ).all()

        gw_info = session.query(Gameweek).filter(Gameweek.id == gw_id).first()
        is_dgw = gw_info.is_double if gw_info else False

    # Map teams to fixtures
    team_fixtures: dict[int, list[Fixture]] = {}
    for f in gw_fixtures:
        team_fixtures.setdefault(f.home_team_id, []).append(f)
        team_fixtures.setdefault(f.away_team_id, []).append(f)

    predictions = []
    for player, team_short, form in players_data:
        if not form or form.minutes_pct < 20:
            continue

        xg = xg_data.get(player.id)
        xgi_per_90 = float(xg.xgi / (Decimal(xg.minutes) / 90)) if xg and xg.minutes > 0 else 0
        season_xgi = float(xg.xgi) if xg else 0

        player_fixtures = team_fixtures.get(player.team_id, [])
        if not player_fixtures:
            continue

        total_predicted = 0.0
        for fix in player_fixtures:
            is_home = fix.home_team_id == player.team_id
            fdr = float(fix.home_difficulty if is_home else fix.away_difficulty) if fix else 3.0

            features = np.array([[
                xgi_per_90,
                float(form.minutes_pct) / 100,
                fdr,
                1.0 if is_home else 0.0,
                0.5,
                float(form.bps_avg),
                1.0 if is_dgw else 0.0,
                0,  # saves placeholder
                1.0 if player.is_penalty_taker or player.is_set_piece_taker else 0,
                season_xgi,
            ]])
            features_scaled = _scaler.transform(features)
            pred = max(0, float(_model.predict(features_scaled)[0]))
            total_predicted += pred

        predictions.append({
            "player_id": player.id,
            "web_name": player.web_name,
            "team_short_name": team_short,
            "position": player.position,
            "predicted_points": round(Decimal(str(total_predicted)), 1),
            "now_cost": player.now_cost,
        })

    predictions.sort(key=lambda p: float(p["predicted_points"]), reverse=True)
    return predictions
