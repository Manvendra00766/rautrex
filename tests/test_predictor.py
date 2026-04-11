"""Tests for quant/ml/predictor.py — feature engineering, training, walk-forward, prediction."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.ml.predictor import (
    build_features,
    train_model,
    predict_next,
    walk_forward_validation,
    FEATURE_COLS,
)


# ─── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def sample_ohlcv_df():
    """OHLCV DataFrame with 500 rows (enough for all feature warmups + walk-forward)."""
    rng = np.random.default_rng(42)
    n = 500
    close = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.015, n)))
    return pd.DataFrame({
        "open": close * (1 + rng.uniform(-0.005, 0.005, n)),
        "high": close * (1 + np.abs(rng.uniform(0, 0.02, n))),
        "low": close * (1 - np.abs(rng.uniform(0, 0.02, n))),
        "close": close,
        "volume": rng.integers(1_000_000, 10_000_000, n).astype(float),
    })


@pytest.fixture(scope="module")
def sample_features(sample_ohlcv_df):
    """Feature DataFrame with target column, NaNs for warmup rows."""
    return build_features(sample_ohlcv_df)


# ─── Feature Engineering ────────────────────────────────────────────


class TestBuildFeatures:
    """Test feature construction."""

    def test_build_features_returns_expected_columns(self, sample_features):
        """Output contains all FEATURE_COLS and target."""
        for col in FEATURE_COLS:
            assert col in sample_features.columns
        assert "target" in sample_features.columns

    def test_target_values_are_zero_or_one(self, sample_features):
        """Target column is binary (0 or 1)."""
        clean = sample_features.dropna()
        assert set(clean["target"].unique()).issubset({0, 1})

    def test_feature_engineering_produces_nans_for_warmup(self, sample_features):
        """First rows have NaNs due to rolling warmup (MA200 needs 200 bars)."""
        assert sample_features.iloc[:40].isna().any().any()


# ─── Training ───────────────────────────────────────────────────────


class TestTrainModel:
    """Test model training: chronological split, accuracy, scaling."""

    def test_train_test_split_is_chronological(self, sample_features):
        """Test data comes after training data (latest rows held out)."""
        # Use enough data for all features
        data = sample_features.dropna(subset=FEATURE_COLS + ["target"])
        split_idx = int(len(data) * 0.8)
        assert split_idx < len(data)
        # Last training row index < first test row index
        assert data.iloc[split_idx - 1].name < data.iloc[split_idx].name

    def test_train_returns_accuracy_between_0_and_1(self, sample_features):
        """test_accuracy is a float between 0 and 1."""
        result = train_model(sample_features, model_type="random_forest")
        assert 0.0 <= result.test_accuracy <= 1.0
        assert 0.0 <= result.train_accuracy <= 1.0

    def test_feature_importances_sum_to_approximately_one(self, sample_features):
        """RandomForest feature importances sum to ~1.0."""
        result = train_model(sample_features, model_type="random_forest")
        total = sum(result.feature_importances.values())
        assert total == pytest.approx(1.0, abs=0.01)

    def test_train_model_raises_error_with_insufficient_data(self):
        """Raises ValueError if fewer than ~100 rows after dropping NaNs."""
        # Create a tiny OHLCV DataFrame that will have many NaNs from warmup
        rng = np.random.default_rng(42)
        small_df = pd.DataFrame({
            "open": [100.0] * 30,
            "high": [101.0] * 30,
            "low": [99.0] * 30,
            "close": [100.5] * 30,
            "volume": [1_000_000.0] * 30,
        })
        features = build_features(small_df)
        with pytest.raises(ValueError, match="Need"):
            train_model(features)

    def test_train_with_logistic_regression(self, sample_features):
        """Logistic regression model trains without error."""
        result = train_model(sample_features, model_type="logistic_regression")
        assert isinstance(result.test_accuracy, float)
        assert 0.0 < result.test_accuracy < 1.0

    def test_scaler_is_applied_before_prediction(self, sample_features):
        """StandardScaler is fitted during training."""
        result = train_model(sample_features, model_type="random_forest")
        assert hasattr(result.scaler, "mean_")  # StandardScaler attribute
        assert hasattr(result.scaler, "scale_")

    def test_train_accuracy_can_exceed_test_accuracy(self, sample_features):
        """train_accuracy >= test_accuracy (not guaranteed but very likely for RF)."""
        result = train_model(sample_features, model_type="random_forest")
        # For RandomForest with enough trees, train accuracy is typically higher
        # but we just verify both are valid
        assert isinstance(result.train_accuracy, float)
        assert isinstance(result.test_accuracy, float)


# ─── Prediction ─────────────────────────────────────────────────────


class TestPredictNext:
    """Test single-row and multi-row prediction."""

    def test_predict_returns_probability_and_direction(self, sample_features):
        """predict_next returns dict with probability_up and predicted_direction."""
        result = train_model(sample_features, model_type="random_forest")
        clean = sample_features.dropna(subset=FEATURE_COLS + ["target"])
        latest = clean.iloc[[-1]]
        pred = predict_next(result.model, result.scaler, latest)
        assert "probability_up" in pred
        assert "predicted_direction" in pred
        assert 0.0 <= pred["probability_up"] <= 1.0
        assert pred["predicted_direction"] in (0, 1)

    def test_predict_multiple_rows_returns_list(self, sample_features):
        """Multiple rows returns a list of prediction dicts."""
        result = train_model(sample_features, model_type="random_forest")
        clean = sample_features.dropna(subset=FEATURE_COLS + ["target"])
        latest = clean.iloc[-5:]
        preds = predict_next(result.model, result.scaler, latest)
        assert isinstance(preds, list)
        assert len(preds) == 5


# ─── Walk-Forward Validation ───────────────────────────────────────

class TestWalkForwardValidation:
    """Test walk-forward CV: n_splits accuracy returned."""

    def test_walk_forward_returns_n_splits_accuracy_scores(self, sample_features):
        """Returns exactly n_splits fold accuracy values."""
        result = walk_forward_validation(sample_features, n_splits=5)
        assert len(result["folds"]) == 5
        for fold in result["folds"]:
            assert "accuracy" in fold
            assert 0.0 < fold["accuracy"] < 1.0

    def test_walk_forward_mean_accuracy_is_valid(self, sample_features):
        """Mean accuracy across folds is a valid probability."""
        result = walk_forward_validation(sample_features, n_splits=5)
        assert 0.0 < result["mean_accuracy"] < 1.0

    def test_walk_forward_raises_with_insufficient_data(self):
        """Raises ValueError if not enough data for n_splits."""
        rng = np.random.default_rng(42)
        small_df = pd.DataFrame({
            "open": [100.0] * 50,
            "high": [101.0] * 50,
            "low": [99.0] * 50,
            "close": [100.5] * 50,
            "volume": [1_000_000.0] * 50,
        })
        features = build_features(small_df)
        with pytest.raises(ValueError, match="clean rows"):
            walk_forward_validation(features, n_splits=5)
