"""ML Prediction Module — Direction prediction for OHLCV data.

WARNING: ML in finance is fundamentally limited. Keep these realities
front and centre:

• Non-stationarity — market dynamics shift constantly. A model trained on
  2020-2021 data will fail on 2022+ data because the data-generating
  process itself changes. Past accuracy ≠ future edge.
• Regime changes — volatility regimes, monetary policy shifts, and macro
  shocks can invalidate learned patterns overnight.
• Transaction costs — even 55% accuracy can lose money after slippage,
  commissions, and bid-ask spread. Always backtest with cost models.
• Overfitting — financial signals are extremely noisy. A model with 90%
  in-sample accuracy on daily directions is almost certainly memorizing
  noise, not finding signal.
• Look-ahead bias — any feature that leaks future information will inflate
  backtest results. Feature construction here deliberately lags by design.

This module is a research scaffold, not a trading system.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit


# ---------------------------------------------------------------------------
# 1. Feature Engineering
# ---------------------------------------------------------------------------


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Transform raw OHLCV into predictive features + target.

    Expects: columns ['open', 'high', 'low', 'close', 'volume'].
    Returns features shifted to avoid look-ahead — the target is the
    *next*-day return direction, so all features use only past/current data
    as of the current bar.

    Args:
        df: DataFrame with OHLCV columns, sorted chronologically.

    Returns:
        DataFrame (with NaNs for lookback warmup) of features + 'target'.
    """
    f = df.copy()

    # Returns
    f["ret_1d"] = f["close"].pct_change(1)
    f["ret_5d"] = f["close"].pct_change(5)
    f["ret_20d"] = f["close"].pct_change(20)

    # Rolling volatility (std of daily returns)
    f["vol_10d"] = f["close"].pct_change().rolling(10).std()
    f["vol_20d"] = f["close"].pct_change().rolling(20).std()

    # RSI (14-period)
    f["rsi"] = _rsi(f["close"], period=14)

    # Price distance from moving averages (as %)
    ma50 = f["close"].rolling(50).mean()
    ma200 = f["close"].rolling(200).mean()
    f["dist_ma50"] = (f["close"] - ma50) / ma50 * 100
    f["dist_ma200"] = (f["close"] - ma200) / ma200 * 100

    # Volume change vs 20-day average
    vol_avg = f["volume"].rolling(20).mean()
    f["vol_chg"] = (f["volume"] - vol_avg) / vol_avg * 100

    # Target: next-day return direction (1 if positive, 0 otherwise)
    f["target"] = (f["close"].shift(-1) > f["close"]).astype(int)

    return f


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder smoothing)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


# ---------------------------------------------------------------------------
# 2. Train Model
# ---------------------------------------------------------------------------


@dataclass
class TrainResult:
    model: object
    scaler: StandardScaler
    train_accuracy: float
    test_accuracy: float
    classification_report_str: str
    feature_importances: dict[str, float]


FEATURE_COLS = [
    "ret_1d", "ret_5d", "ret_20d",
    "vol_10d", "vol_20d",
    "rsi",
    "dist_ma50", "dist_ma200",
    "vol_chg",
]


def train_model(
    df: pd.DataFrame,
    test_size: float = 0.2,
    model_type: str = "random_forest",
) -> TrainResult:
    """Train a directional classifier with chronological split.

    IMPORTANT: The train/test split is chronological, NOT random.
    Random shuffling would create look-ahead bias — the model would "see"
    future data as training examples, inflating apparent accuracy.

    Args:
        df: Feature DataFrame (output of build_features), NaNs dropped.
        test_size: Fraction of *latest* data held out as test set.
        model_type: 'random_forest' or 'logistic_regression'.

    Returns:
        TrainResult with model, metrics, and feature importances.

    Raises:
        ValueError: If not enough data after dropping NaNs.
    """
    data = df.dropna(subset=FEATURE_COLS + ["target"]).copy()
    if len(data) < 100:
        raise ValueError(
            f"Need ≥100 rows after warmup, got {len(data)}. "
            "Provide more historical data or use wider intervals."
        )

    split_idx = int(len(data) * (1 - test_size))
    train_data = data.iloc[:split_idx]
    test_data = data.iloc[split_idx:]

    X_train = train_data[FEATURE_COLS].values
    y_train = train_data["target"].values
    X_test = test_data[FEATURE_COLS].values
    y_test = test_data["target"].values

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    if model_type == "logistic_regression":
        model = LogisticRegression(max_iter=1000, random_state=42)
    else:
        model = RandomForestClassifier(
            n_estimators=100, random_state=42, n_jobs=-1
        )

    model.fit(X_train_s, y_train)

    y_train_pred = model.predict(X_train_s)
    y_test_pred = model.predict(X_test_s)

    report_str = classification_report(
        y_test, y_test_pred, target_names=["down", "up"]
    )

    importances = dict(
        zip(
            FEATURE_COLS,
            (
                model.feature_importances_.tolist()
                if hasattr(model, "feature_importances_")
                else np.abs(model.coef_[0]).tolist()
            ),
        )
    )

    return TrainResult(
        model=model,
        scaler=scaler,
        train_accuracy=float(accuracy_score(y_train, y_train_pred)),
        test_accuracy=float(accuracy_score(y_test, y_test_pred)),
        classification_report_str=report_str,
        feature_importances=importances,
    )


# ---------------------------------------------------------------------------
# 3. Prediction
# ---------------------------------------------------------------------------


def predict_next(
    model: object, scaler: StandardScaler, latest_features: pd.DataFrame
) -> dict:
    """Predict next-day direction from the latest row of features.

    Args:
        model: Trained classifier.
        scaler: Fitted StandardScaler from train_model.
        latest_features: DataFrame (any rows, typically last 1–5) with
            columns FEATURE_COLS.

    Returns:
        Dict with probability_up and predicted_direction for each row.
    """
    data = latest_features[FEATURE_COLS].values
    data_s = scaler.transform(data)
    probabilities = model.predict_proba(data_s)[:, 1]  # P(up)
    predictions = model.predict(data_s)

    results = []
    for i in range(len(data)):
        results.append({
            "probability_up": float(probabilities[i]),
            "predicted_direction": int(predictions[i]),
        })
    return results[0] if len(results) == 1 else results


# ---------------------------------------------------------------------------
# 4. Walk-Forward Validation
# ---------------------------------------------------------------------------


def walk_forward_validation(
    df: pd.DataFrame, n_splits: int = 5
) -> dict:
    """TimeSeriesSplit cross-validation.

    This is the only honest way to evaluate an ML model on financial data.
    Each fold trains on a growing window and tests on the immediate
    *future* — simulating what would actually happen if you deployed the
    model at that point in time.

    WARNING: If walk-forward accuracy hovers around 50%, the model has no
    predictive edge. This is the EXPECTED outcome for most feature sets on
    daily equity data. Don't cherry-pick the best fold.

    Args:
        df: Feature DataFrame (output of build_features).
        n_splits: Number of CV folds.

    Returns:
        Dict with fold-level and aggregate accuracy metrics.
    """
    data = df.dropna(subset=FEATURE_COLS + ["target"]).copy()
    if len(data) < n_splits * 50:
        raise ValueError(
            f"Need ≥{n_splits * 50} clean rows for {n_splits}-fold walk-forward."
        )

    X = data[FEATURE_COLS].values
    y = data["target"].values

    tscv = TimeSeriesSplit(n_splits=n_splits)
    fold_results = []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X), 1):
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X[train_idx])
        X_test_s = scaler.transform(X[test_idx])

        clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        clf.fit(X_train_s, y[train_idx])
        acc = accuracy_score(y[test_idx], clf.predict(X_test_s))
        fold_results.append({"fold": fold, "accuracy": float(acc), "test_size": len(test_idx)})

    accs = [r["accuracy"] for r in fold_results]

    return {
        "folds": fold_results,
        "mean_accuracy": float(np.mean(accs)),
        "std_accuracy": float(np.std(accs)),
    }
