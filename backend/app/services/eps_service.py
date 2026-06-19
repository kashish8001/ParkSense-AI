"""Enforcement Priority Score (EPS) engine."""

from __future__ import annotations

import pandas as pd

from app.config import settings


def _normalize(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return pd.Series(0.0, index=series.index)
    return (series - min_val) / (max_val - min_val)


def apply_eps_scores(grid: pd.DataFrame) -> pd.DataFrame:
    weights = settings.eps_weights
    result = grid.copy()
    device_gap = 1.0 / (result["device_coverage_7d"] + 1.0)
    components = pd.DataFrame(
        {
            "density_7d": _normalize(result["violations_7d"]),
            "severity_7d": _normalize(result["severity_weighted_7d"]),
            "repeat_rate": _normalize(result["repeat_location_rate"]),
            "forecast_24h": _normalize(result.get("predicted_count", pd.Series(0, index=result.index))),
            "device_gap": _normalize(device_gap),
            "junction_spillover": result["junction_spillover_flag"].astype(float),
        }
    )
    result["eps_score"] = sum(components[key] * weights[key] for key in weights)
    for key in components.columns:
        result[f"eps_{key}"] = components[key]
    return result.sort_values("eps_score", ascending=False).reset_index(drop=True)


def build_priority_zone(row: pd.Series) -> dict:
    components = {
        "density_7d": round(float(row.get("eps_density_7d", 0)), 4),
        "severity_7d": round(float(row.get("eps_severity_7d", 0)), 4),
        "repeat_rate": round(float(row.get("eps_repeat_rate", 0)), 4),
        "forecast_24h": round(float(row.get("eps_forecast_24h", 0)), 4),
        "device_gap": round(float(row.get("eps_device_gap", 0)), 4),
        "junction_spillover": round(float(row.get("eps_junction_spillover", 0)), 4),
    }
    return {
        "h3_index": row["h3_index"],
        "centroid": {"lat": float(row["centroid_lat"]), "lon": float(row["centroid_lon"])},
        "eps_score": round(float(row["eps_score"]), 4),
        "pii_score": round(float(row["pii_score"]), 4),
        "components": components,
        "police_station": row["dominant_station"],
        "violations_7d": int(row["violations_7d"]),
        "predicted_count": round(float(row.get("predicted_count", 0)), 2),
        "recommended_action": "HIGH_PRIORITY_PATROL" if row["eps_score"] >= 0.7 else "SCHEDULED_PATROL",
    }
