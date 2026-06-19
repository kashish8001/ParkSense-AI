"""Violation forecasting service."""

from __future__ import annotations

import pandas as pd

from app.services.data_store import data_store


def get_forecast_top(station: str | None = None, limit: int = 20) -> list[dict]:
    grid = data_store.grid_cells.copy()
    if station:
        grid = grid[grid["dominant_station"] == station]
    grid = grid.sort_values("predicted_count", ascending=False).head(limit)
    results = []
    for _, row in grid.iterrows():
        risk_tier = "HIGH" if row["predicted_count"] >= grid["predicted_count"].quantile(0.75) else "MEDIUM"
        if row["predicted_count"] <= grid["predicted_count"].quantile(0.25):
            risk_tier = "LOW"
        results.append(
            {
                "h3_index": row["h3_index"],
                "centroid": {"lat": float(row["centroid_lat"]), "lon": float(row["centroid_lon"])},
                "predicted_count": round(float(row["predicted_count"]), 2),
                "pii_score": round(float(row["pii_score"]), 4),
                "eps_score": round(float(row["eps_score"]), 4),
                "police_station": row["dominant_station"],
                "risk_tier": risk_tier,
            }
        )
    return results


def get_forecast_metrics() -> dict:
    return data_store.forecast_metrics
