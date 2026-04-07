"""Tests for prediction model: filtering, HGBR fitting, and ensemble logic."""

import numpy as np


class TestPredictionStatusFilter:
    """Verify that the prediction queries include doubtful players
    who have a valid chance_of_playing >= 50."""

    def test_status_filter_includes_doubtful(self) -> None:
        """Players with status 'd' (doubtful) but chance >= 50 should be included."""
        from app.services.points_model import _should_include_player

        # Doubtful but 75% chance — should include
        assert _should_include_player(status="d", chance=75, minutes_pct=80.0) is True

    def test_status_filter_includes_active(self) -> None:
        """Players with status 'a' (active) should always be included."""
        from app.services.points_model import _should_include_player

        assert _should_include_player(status="a", chance=None, minutes_pct=80.0) is True

    def test_status_filter_excludes_unavailable(self) -> None:
        """Players with status 'u' (unavailable) should be excluded."""
        from app.services.points_model import _should_include_player

        assert _should_include_player(status="u", chance=0, minutes_pct=0.0) is False

    def test_status_filter_excludes_injured(self) -> None:
        """Players with status 'i' (injured) should be excluded."""
        from app.services.points_model import _should_include_player

        assert _should_include_player(status="i", chance=0, minutes_pct=50.0) is False

    def test_status_filter_excludes_doubtful_low_chance(self) -> None:
        """Doubtful players with chance < 50 should be excluded."""
        from app.services.points_model import _should_include_player

        assert _should_include_player(status="d", chance=25, minutes_pct=80.0) is False

    def test_status_filter_excludes_low_minutes(self) -> None:
        """Players with < 50% minutes should be excluded regardless of status."""
        from app.services.points_model import _should_include_player

        result = _should_include_player(status="a", chance=None, minutes_pct=30.0)
        assert result is False

    def test_status_filter_suspended(self) -> None:
        """Players with status 's' (suspended) should be excluded."""
        from app.services.points_model import _should_include_player

        assert _should_include_player(status="s", chance=0, minutes_pct=80.0) is False

    def test_status_filter_doubtful_exactly_50(self) -> None:
        from app.services.points_model import _should_include_player

        assert _should_include_player(status="d", chance=50, minutes_pct=80.0) is True

    def test_status_filter_doubtful_49(self) -> None:
        from app.services.points_model import _should_include_player

        assert _should_include_player(status="d", chance=49, minutes_pct=80.0) is False

    def test_status_filter_doubtful_none_chance(self) -> None:
        """Doubtful with None chance — FPL sometimes has this, treat as excluded."""
        from app.services.points_model import _should_include_player

        result = _should_include_player(status="d", chance=None, minutes_pct=80.0)
        assert result is False


class TestFitHGBR:
    """Test HistGradientBoostingRegressor fitting."""

    def test_fit_hgbr_sufficient_data(self) -> None:
        from app.services.points_model import _fit_hgbr

        rng = np.random.default_rng(42)
        x = rng.standard_normal((150, 27)).tolist()
        y = rng.standard_normal(150).tolist()
        w = [1.0] * 150
        result = _fit_hgbr(x, y, w)
        assert result is not None
        # Verify it can predict
        pred = result.predict(rng.standard_normal((1, 27)))
        assert len(pred) == 1

    def test_fit_hgbr_insufficient_data(self) -> None:
        from app.services.points_model import _fit_hgbr

        x = [[0.0] * 27] * 50
        y = [1.0] * 50
        w = [1.0] * 50
        result = _fit_hgbr(x, y, w)
        assert result is None


class TestEnsemblePrediction:
    """Test ensemble averaging in _predict_one."""

    def test_ensemble_averages_both_models(self) -> None:
        import app.services.points_model as pm

        rng = np.random.default_rng(42)
        x = rng.standard_normal((100, 27)).tolist()
        y = rng.standard_normal(100).tolist()
        w = [1.0] * 100

        ridge_result = pm._fit_ridge(x, y, w)
        assert ridge_result is not None
        ridge_model, ridge_scaler = ridge_result

        hgbr = pm._fit_hgbr(x, y, w)
        assert hgbr is not None

        # Install models for position 3 (MID)
        old_models = pm._models.copy()
        old_scalers = pm._scalers.copy()
        old_hgbr = pm._hgbr_models.copy()
        try:
            pm._models = {3: ridge_model}
            pm._scalers = {3: ridge_scaler}
            pm._hgbr_models = {3: hgbr}

            features = [0.0] * 27
            result = pm._predict_one(3, features)
            assert isinstance(result, (int, float))
            assert result >= 0.0

            # Verify it's actually the average
            x_arr = np.array([features])
            ridge_pred = float(
                ridge_model.predict(ridge_scaler.transform(x_arr))[0],
            )
            hgbr_pred = float(hgbr.predict(x_arr)[0])
            expected = max(0, (ridge_pred + hgbr_pred) / 2)
            assert abs(result - expected) < 0.001
        finally:
            pm._models = old_models
            pm._scalers = old_scalers
            pm._hgbr_models = old_hgbr

    def test_ridge_only_when_no_hgbr(self) -> None:
        import app.services.points_model as pm

        rng = np.random.default_rng(42)
        x = rng.standard_normal((100, 27)).tolist()
        y = rng.standard_normal(100).tolist()
        w = [1.0] * 100

        ridge_result = pm._fit_ridge(x, y, w)
        assert ridge_result is not None
        ridge_model, ridge_scaler = ridge_result

        old_models = pm._models.copy()
        old_scalers = pm._scalers.copy()
        old_hgbr = pm._hgbr_models.copy()
        old_hgbr_fb = pm._hgbr_model
        try:
            pm._models = {3: ridge_model}
            pm._scalers = {3: ridge_scaler}
            pm._hgbr_models = {}
            pm._hgbr_model = None

            features = [0.0] * 27
            result = pm._predict_one(3, features)

            x_arr = np.array([features])
            ridge_pred = max(
                0,
                float(
                    ridge_model.predict(
                        ridge_scaler.transform(x_arr),
                    )[0],
                ),
            )
            assert abs(result - ridge_pred) < 0.001
        finally:
            pm._models = old_models
            pm._scalers = old_scalers
            pm._hgbr_models = old_hgbr
            pm._hgbr_model = old_hgbr_fb

    def test_returns_zero_when_no_models(self) -> None:
        import app.services.points_model as pm

        old = (
            pm._models.copy(),
            pm._scalers.copy(),
            pm._hgbr_models.copy(),
            pm._model,
            pm._scaler,
        )
        try:
            pm._models = {}
            pm._scalers = {}
            pm._hgbr_models = {}
            pm._model = None
            pm._scaler = None
            assert pm._predict_one(3, [0.0] * 27) == 0.0
        finally:
            pm._models = old[0]
            pm._scalers = old[1]
            pm._hgbr_models = old[2]
            pm._model = old[3]
            pm._scaler = old[4]
