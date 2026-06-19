"""Central in-memory data store backed by parquet artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import settings
from app.ml.train_forecast import ViolationForecaster


@dataclass
class DataStore:
    ready: bool = False
    source_file: str | None = None
    processed_at: str | None = None
    violations: pd.DataFrame = field(default_factory=pd.DataFrame)
    grid_cells: pd.DataFrame = field(default_factory=pd.DataFrame)
    hourly_features: pd.DataFrame = field(default_factory=pd.DataFrame)
    officer_stats: pd.DataFrame = field(default_factory=pd.DataFrame)
    station_stats: pd.DataFrame = field(default_factory=pd.DataFrame)
    junction_stats: pd.DataFrame = field(default_factory=pd.DataFrame)
    clusters: list[dict[str, Any]] = field(default_factory=list)
    forecaster: ViolationForecaster = field(default_factory=ViolationForecaster)
    forecast_metrics: dict[str, Any] = field(default_factory=dict)
    analytics_cache: dict[str, Any] = field(default_factory=dict)

    @property
    def storage_dir(self) -> Path:
        return settings.storage_dir

    def artifact_paths(self) -> dict[str, Path]:
        base = self.storage_dir
        return {
            "violations": base / "violations.parquet",
            "grid": base / "grid_cells.parquet",
            "hourly": base / "hourly_features.parquet",
            "officers": base / "officer_stats.parquet",
            "stations": base / "station_stats.parquet",
            "junctions": base / "junction_stats.parquet",
            "clusters": base / "clusters.json",
            "model": base / "forecast_model.joblib",
            "metadata": base / "metadata.json",
        }

    def save(self) -> None:
        paths = self.artifact_paths()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.violations.to_parquet(paths["violations"], index=False)
        self.grid_cells.to_parquet(paths["grid"], index=False)
        self.hourly_features.to_parquet(paths["hourly"], index=False)
        self.officer_stats.to_parquet(paths["officers"], index=False)
        self.station_stats.to_parquet(paths["stations"], index=False)
        self.junction_stats.to_parquet(paths["junctions"], index=False)
        self.forecaster.save(paths["model"])
        import json

        with open(paths["clusters"], "w", encoding="utf-8") as handle:
            json.dump(self.clusters, handle)
        metadata = {
            "ready": self.ready,
            "source_file": self.source_file,
            "processed_at": self.processed_at,
            "forecast_metrics": self.forecast_metrics,
            "analytics_cache": self.analytics_cache,
        }
        with open(paths["metadata"], "w", encoding="utf-8") as handle:
            json.dump(metadata, handle)

    def load(self) -> bool:
        paths = self.artifact_paths()
        if not paths["violations"].exists() or not paths["grid"].exists():
            return False
        self.violations = pd.read_parquet(paths["violations"])
        self.grid_cells = pd.read_parquet(paths["grid"])
        self.hourly_features = pd.read_parquet(paths["hourly"]) if paths["hourly"].exists() else pd.DataFrame()
        self.officer_stats = pd.read_parquet(paths["officers"]) if paths["officers"].exists() else pd.DataFrame()
        self.station_stats = pd.read_parquet(paths["stations"]) if paths["stations"].exists() else pd.DataFrame()
        self.junction_stats = pd.read_parquet(paths["junctions"]) if paths["junctions"].exists() else pd.DataFrame()
        if paths["model"].exists():
            self.forecaster.load(paths["model"])
        import json

        if paths["clusters"].exists():
            with open(paths["clusters"], encoding="utf-8") as handle:
                self.clusters = json.load(handle)
        if paths["metadata"].exists():
            with open(paths["metadata"], encoding="utf-8") as handle:
                metadata = json.load(handle)
            self.ready = metadata.get("ready", True)
            self.source_file = metadata.get("source_file")
            self.processed_at = metadata.get("processed_at")
            self.forecast_metrics = metadata.get("forecast_metrics", {})
            self.analytics_cache = metadata.get("analytics_cache", {})
        else:
            self.ready = True
        return True


data_store = DataStore()
