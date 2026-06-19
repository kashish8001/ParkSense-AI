"""Hotspot and heatmap services."""

from __future__ import annotations

import pandas as pd

from app.ml.features import grid_to_geojson
from app.services.data_store import data_store
from app.services.eps_service import build_priority_zone


def get_clusters(
    station: str | None = None,
    min_eps: float = 0.0,
    limit: int = 50,
) -> list[dict]:
    clusters = data_store.clusters
    if station:
        clusters = [cluster for cluster in clusters if cluster["dominant_station"] == station]
    if min_eps > 0:
        clusters = [cluster for cluster in clusters if cluster["eps_score"] >= min_eps]
    return clusters[:limit]


def get_heatmap(metric: str = "pii", limit: int = 500, station: str | None = None) -> dict:
    grid = data_store.grid_cells.copy()
    if station:
        grid = grid[grid["dominant_station"] == station]
    grid = grid.sort_values(metric if metric in grid.columns else "pii_score", ascending=False).head(limit)
    column = metric if metric in {"pii_score", "eps_score", "violations_7d", "predicted_count"} else "pii_score"
    return grid_to_geojson(grid, value_column=column)


def get_priority_zones(station: str | None = None, top: int = 20) -> list[dict]:
    grid = data_store.grid_cells.copy()
    if station:
        grid = grid[grid["dominant_station"] == station]
    grid = grid.sort_values("eps_score", ascending=False).head(top)
    return [build_priority_zone(row) for _, row in grid.iterrows()]
