"""LightGBM violation count forecaster."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error

FEATURE_COLUMNS = [
    "lag_1h",
    "lag_24h",
    "lag_168h",
    "rolling_7d_mean",
    "rolling_30d_mean",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "is_weekend",
    "month",
]


@dataclass
class ForecastMetrics:
    train_mae: float
    val_mae: float
    test_mae: float
    train_rows: int
    val_rows: int
    test_rows: int


class ViolationForecaster:
    def __init__(self) -> None:
        self.model: lgb.LGBMRegressor | None = None
        self.metrics: ForecastMetrics | None = None

    def train(self, frame: pd.DataFrame) -> ForecastMetrics:
        data = frame.dropna(subset=FEATURE_COLUMNS + ["violation_count"]).copy()
        data = data.sort_values("hour_bucket")
        train = data[data["hour_bucket"] < "2024-03-01"]
        val = data[(data["hour_bucket"] >= "2024-03-01") & (data["hour_bucket"] < "2024-04-01")]
        test = data[data["hour_bucket"] >= "2024-04-01"]

        self.model = lgb.LGBMRegressor(
            n_estimators=200,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
        )
        self.model.fit(train[FEATURE_COLUMNS], train["violation_count"])

        def mae(split: pd.DataFrame) -> float:
            if split.empty:
                return 0.0
            preds = self.model.predict(split[FEATURE_COLUMNS])
            return float(mean_absolute_error(split["violation_count"], preds))

        self.metrics = ForecastMetrics(
            train_mae=mae(train),
            val_mae=mae(val),
            test_mae=mae(test),
            train_rows=len(train),
            val_rows=len(val),
            test_rows=len(test),
        )
        return self.metrics

    def predict_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        if self.model is None:
            raise RuntimeError("Forecast model is not trained.")
        result = frame.copy()
        result["predicted_count"] = np.clip(self.model.predict(result[FEATURE_COLUMNS]), 0, None)
        return result

    def predict_latest_by_cell(self, frame: pd.DataFrame) -> pd.DataFrame:
        max_time = frame["hour_bucket"].max()
        latest = frame[frame["hour_bucket"] == max_time].copy()
        predicted = self.predict_frame(latest)
        return predicted[["h3_index", "hour_bucket", "predicted_count"]]

    def save(self, path: Path) -> None:
        if self.model is None:
            raise RuntimeError("Forecast model is not trained.")
        joblib.dump({"model": self.model, "metrics": self.metrics, "features": FEATURE_COLUMNS}, path)

    def load(self, path: Path) -> None:
        payload = joblib.load(path)
        self.model = payload["model"]
        self.metrics = payload["metrics"]
