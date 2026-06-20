"""Spatial grid features, aggregations, and training datasets."""

from __future__ import annotations

import json
from math import cos, radians

import h3
import numpy as np
import pandas as pd

from app.config import settings


def assign_h3(lat: float, lon: float, resolution: int | None = None) -> str:
    res = resolution or settings.h3_resolution
    return h3.latlng_to_cell(lat, lon, res)


def add_h3_index(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["h3_index"] = [
        assign_h3(lat, lon) for lat, lon in zip(result["latitude"], result["longitude"], strict=False)
    ]
    return result


def _normalize(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return pd.Series(0.0, index=series.index)
    return (series - min_val) / (max_val - min_val)


def build_grid_cells(violations: pd.DataFrame) -> pd.DataFrame:
    """Aggregate violation metrics per H3 cell."""
    max_date = violations["created_datetime"].max()
    cutoff_7d = max_date - pd.Timedelta(days=7)
    cutoff_30d = max_date - pd.Timedelta(days=30)

    recent_7d = violations[violations["created_datetime"] >= cutoff_7d]
    recent_30d = violations[violations["created_datetime"] >= cutoff_30d]

    grouped = violations.groupby("h3_index", as_index=False).agg(
        centroid_lat=("latitude", "mean"),
        centroid_lon=("longitude", "mean"),
        total_violations=("id", "count"),
        severity_total=("severity_score", "sum"),
        carriageway_blocking_count=("is_carriageway_blocking", "sum"),
        multi_offence_count=("is_multi_offence", "sum"),
        heavy_vehicle_count=("is_heavy_vehicle", "sum"),
        junction_spillover_count=("has_junction", "sum"),
        dominant_station=("police_station", lambda s: s.mode().iloc[0] if not s.mode().empty else "Unknown"),
        dominant_junction=("junction_name", lambda s: s.mode().iloc[0] if not s.mode().empty else "No Junction"),
    )

    counts_7d = recent_7d.groupby("h3_index").size().rename("violations_7d")
    counts_30d = recent_30d.groupby("h3_index").size().rename("violations_30d")
    severity_7d = recent_7d.groupby("h3_index")["severity_score"].sum().rename("severity_weighted_7d")
    devices_7d = recent_7d.groupby("h3_index")["device_id"].nunique().rename("device_coverage_7d")
    officers_7d = recent_7d.groupby("h3_index")["created_by_id"].nunique().rename("officer_coverage_7d")

    grid = grouped.set_index("h3_index")
    for frame in (counts_7d, counts_30d, severity_7d, devices_7d, officers_7d):
        grid = grid.join(frame, how="left")
    grid = grid.fillna(
        {
            "violations_7d": 0,
            "violations_30d": 0,
            "severity_weighted_7d": 0.0,
            "device_coverage_7d": 0,
            "officer_coverage_7d": 0,
        }
    ).reset_index()

    coord_counts = (
        violations.groupby([violations["latitude"].round(4), violations["longitude"].round(4)])
        .size()
        .reset_index(name="coord_count")
    )
    repeat_rate_map: dict[str, float] = {}
    for h3_index, group in violations.groupby("h3_index"):
        coords = group[["latitude", "longitude"]].round(4)
        merged = coords.merge(coord_counts, on=["latitude", "longitude"], how="left")
        repeat_rate_map[h3_index] = float((merged["coord_count"] > 1).mean()) if len(merged) else 0.0
    grid["repeat_location_rate"] = grid["h3_index"].map(repeat_rate_map).fillna(0.0)
    grid["heavy_vehicle_share"] = grid["heavy_vehicle_count"] / grid["total_violations"].clip(lower=1)
    grid["multi_offence_rate"] = grid["multi_offence_count"] / grid["total_violations"].clip(lower=1)
    grid["carriageway_blocking_rate"] = grid["carriageway_blocking_count"] / grid["total_violations"].clip(lower=1)
    grid["junction_spillover_flag"] = (grid["dominant_junction"] != "No Junction") | (
        grid["junction_spillover_count"] / grid["total_violations"].clip(lower=1) > 0.2
    )

    h3_area = 0.74
    grid["pii_score"] = (
        grid["severity_weighted_7d"] / h3_area
        + 0.2 * grid["multi_offence_rate"]
        + 0.15 * grid["heavy_vehicle_share"]
        + 0.1 * grid["junction_spillover_flag"].astype(float)
    )
    grid["pii_score"] = _normalize(grid["pii_score"])

    return grid.sort_values("pii_score", ascending=False).reset_index(drop=True)


def build_hourly_training_frame(violations: pd.DataFrame, top_n: int | None = None) -> pd.DataFrame:
    """Build hourly aggregates for forecasting model."""
    hourly = (
        violations.assign(hour_bucket=violations["created_datetime"].dt.floor("h"))
        .groupby(["h3_index", "hour_bucket"], as_index=False)
        .agg(
            violation_count=("id", "count"),
            severity_weighted=("severity_score", "sum"),
            approved_count=("is_approved", lambda s: int((s == True).sum())),  # noqa: E712
        )
    )

    top_cells = (
        violations["h3_index"].value_counts().head(top_n or settings.forecast_top_cells).index.tolist()
    )
    hourly = hourly[hourly["h3_index"].isin(top_cells)].copy()
    if hourly.empty:
        return pd.DataFrame()

    # Reconstruct a complete dense hourly range for each cell to align lag features correctly
    min_time = hourly["hour_bucket"].min()
    max_time = hourly["hour_bucket"].max()
    all_hours = pd.date_range(start=min_time, end=max_time, freq="h")

    # Cartesian product of top_cells and all_hours
    mux = pd.MultiIndex.from_product([top_cells, all_hours], names=["h3_index", "hour_bucket"])
    dense_df = pd.DataFrame(index=mux).reset_index()

    # Merge sparse data into dense frame
    dense_df = dense_df.merge(hourly, on=["h3_index", "hour_bucket"], how="left")
    dense_df["violation_count"] = dense_df["violation_count"].fillna(0.0)
    dense_df["severity_weighted"] = dense_df["severity_weighted"].fillna(0.0)
    dense_df["approved_count"] = dense_df["approved_count"].fillna(0)

    # Sort to ensure group shifts are in correct chronological order
    dense_df = dense_df.sort_values(["h3_index", "hour_bucket"]).reset_index(drop=True)

    # Compute vectorized lag and rolling window features per cell group
    grouped = dense_df.groupby("h3_index")
    dense_df["lag_1h"] = grouped["violation_count"].shift(1).fillna(0.0)
    dense_df["lag_24h"] = grouped["violation_count"].shift(24).fillna(0.0)
    dense_df["lag_168h"] = grouped["violation_count"].shift(168).fillna(0.0)

    # Use transform with lambda for rolling mean within groups
    dense_df["rolling_7d_mean"] = (
        grouped["violation_count"]
        .transform(lambda x: x.rolling(window=24 * 7, min_periods=1).mean())
        .fillna(0.0)
    )
    dense_df["rolling_30d_mean"] = (
        grouped["violation_count"]
        .transform(lambda x: x.rolling(window=24 * 30, min_periods=1).mean())
        .fillna(0.0)
    )

    # Compute temporal features
    hours = dense_df["hour_bucket"].dt.hour
    dows = dense_df["hour_bucket"].dt.dayofweek
    dense_df["hour_sin"] = np.sin(2 * np.pi * hours / 24)
    dense_df["hour_cos"] = np.cos(2 * np.pi * hours / 24)
    dense_df["dow_sin"] = np.sin(2 * np.pi * dows / 7)
    dense_df["dow_cos"] = np.cos(2 * np.pi * dows / 7)
    dense_df["is_weekend"] = (dows >= 5).astype(int)
    dense_df["month"] = dense_df["hour_bucket"].dt.month

    # Filter back to only the sparse hour records to preserve the exact training record count and shape
    # ALSO ensure that the absolute latest hour is included for all cells so we can predict for the same latest hour!
    sparse_keys = hourly[["h3_index", "hour_bucket"]]
    latest_keys = pd.DataFrame({
        "h3_index": top_cells,
        "hour_bucket": max_time
    })
    combined_keys = pd.concat([sparse_keys, latest_keys]).drop_duplicates(subset=["h3_index", "hour_bucket"]).reset_index(drop=True)

    result = combined_keys.merge(dense_df, on=["h3_index", "hour_bucket"], how="left")
    return result



def build_officer_stats(violations: pd.DataFrame) -> pd.DataFrame:
    valid = violations.dropna(subset=["created_by_id"])
    stats = (
        valid.groupby("created_by_id", as_index=False)
        .agg(
            total_records=("id", "count"),
            approval_rate=("is_approved", lambda s: float(s.mean()) if not s.isnull().all() else 0.0),
            dominant_station=("police_station", lambda s: s.mode().iloc[0] if not s.mode().empty else "Unknown"),
            avg_severity=("severity_score", "mean"),
        )
        .sort_values("total_records", ascending=False)
    )
    stats["productivity_score"] = stats["total_records"] / stats["total_records"].max()
    return stats


def build_station_stats(violations: pd.DataFrame, grid: pd.DataFrame) -> pd.DataFrame:
    station_counts = violations["police_station"].value_counts().rename("total_violations").reset_index()
    station_counts.columns = ["police_station", "total_violations"]

    # Calculate violations in the last 7 days for each station
    max_date = violations["created_datetime"].max()
    cutoff_7d = max_date - pd.Timedelta(days=7)
    recent_7d = violations[violations["created_datetime"] >= cutoff_7d]
    recent_counts = recent_7d["police_station"].value_counts().rename("violations_7d").reset_index()
    recent_counts.columns = ["police_station", "violations_7d"]

    station_pii = grid.groupby("dominant_station")["pii_score"].mean().rename("avg_pii").reset_index()
    station_pii.columns = ["police_station", "avg_pii"]

    stats = station_counts.merge(recent_counts, on="police_station", how="left").fillna({"violations_7d": 0})
    stats["violations_7d"] = stats["violations_7d"].astype(int)
    stats = stats.merge(station_pii, on="police_station", how="left").fillna({"avg_pii": 0.0})
    
    # Sort by recent 7-day violations, then by total violations
    return stats.sort_values(by=["violations_7d", "total_violations"], ascending=False).reset_index(drop=True)


def build_junction_stats(violations: pd.DataFrame) -> pd.DataFrame:
    tagged = violations[violations["has_junction"]].copy()
    stats = (
        tagged.groupby("junction_name", as_index=False)
        .agg(
            total_violations=("id", "count"),
            centroid_lat=("latitude", "mean"),
            centroid_lon=("longitude", "mean"),
            carriageway_blocking_rate=("is_carriageway_blocking", "mean"),
            severity_total=("severity_score", "sum"),
            dominant_station=("police_station", lambda s: s.mode().iloc[0] if not s.mode().empty else "Unknown"),
        )
        .sort_values("total_violations", ascending=False)
    )
    stats["pii_score"] = _normalize(stats["severity_total"] / stats["total_violations"].clip(lower=1))
    return stats


def km_to_deg_lat(km: float) -> float:
    return km / 110.574


def km_to_deg_lon(km: float, latitude: float) -> float:
    return km / (111.320 * cos(radians(latitude)))


def grid_to_geojson(grid: pd.DataFrame, value_column: str = "pii_score") -> dict:
    features = []
    for row in grid.itertuples(index=False):
        boundary = h3.cell_to_boundary(row.h3_index)
        coordinates = [[[lon, lat] for lat, lon in boundary] + [[boundary[0][1], boundary[0][0]]]]
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "h3_index": row.h3_index,
                    "value": float(getattr(row, value_column)),
                    "violations_7d": int(row.violations_7d),
                    "pii_score": float(row.pii_score),
                    "eps_score": float(getattr(row, "eps_score", 0.0)),
                    "police_station": row.dominant_station,
                },
                "geometry": {"type": "Polygon", "coordinates": coordinates},
            }
        )
    return {"type": "FeatureCollection", "features": features}


def save_json(data: object, path) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle)
