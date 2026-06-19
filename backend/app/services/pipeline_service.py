"""End-to-end data processing pipeline."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from app.ml.clustering import clusters_to_dict, run_dbscan_clusters
from app.ml.etl import ingest_csv
from app.ml.features import (
    add_h3_index,
    build_grid_cells,
    build_hourly_training_frame,
    build_junction_stats,
    build_officer_stats,
    build_station_stats,
)
from app.ml.train_forecast import ViolationForecaster
from app.services.analytics_service import build_summary
from app.services.data_store import data_store
from app.services.eps_service import apply_eps_scores


def run_pipeline(csv_path: Path | None = None) -> dict:
    violations = ingest_csv(csv_path)
    violations = add_h3_index(violations)
    grid = build_grid_cells(violations)
    hourly = build_hourly_training_frame(violations)
    officers = build_officer_stats(violations)
    stations = build_station_stats(violations, grid)
    junctions = build_junction_stats(violations)

    forecaster = ViolationForecaster()
    metrics = forecaster.train(hourly)
    forecast_latest = forecaster.predict_latest_by_cell(hourly)
    grid = grid.merge(
        forecast_latest[["h3_index", "predicted_count"]],
        on="h3_index",
        how="left",
    ).fillna({"predicted_count": 0.0})
    grid = apply_eps_scores(grid)
    clusters = run_dbscan_clusters(violations, grid)

    data_store.violations = violations
    data_store.grid_cells = grid
    data_store.hourly_features = hourly
    data_store.officer_stats = officers
    data_store.station_stats = stations
    data_store.junction_stats = junctions
    data_store.clusters = clusters_to_dict(clusters)
    data_store.forecaster = forecaster
    data_store.ready = True
    data_store.source_file = str(csv_path) if csv_path else str(violations.attrs.get("source", "default"))
    data_store.processed_at = datetime.now(UTC).isoformat()
    data_store.forecast_metrics = {
        "train_mae": round(metrics.train_mae, 4),
        "val_mae": round(metrics.val_mae, 4),
        "test_mae": round(metrics.test_mae, 4),
        "train_rows": metrics.train_rows,
        "val_rows": metrics.val_rows,
        "test_rows": metrics.test_rows,
    }
    data_store.analytics_cache = build_summary(violations, grid, clusters)
    data_store.save()
    return {
        "status": "ok",
        "records": len(violations),
        "grid_cells": len(grid),
        "clusters": len(clusters),
        "forecast_metrics": data_store.forecast_metrics,
        "processed_at": data_store.processed_at,
    }
