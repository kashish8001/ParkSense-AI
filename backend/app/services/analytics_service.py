"""Analytics summary service."""

from __future__ import annotations

from collections import Counter

import pandas as pd

from app.ml.clustering import HotspotCluster


def build_summary(
    violations: pd.DataFrame,
    grid: pd.DataFrame,
    clusters: list[HotspotCluster] | list[dict],
) -> dict:
    labels: list[str] = []
    for items in violations["violation_labels"]:
        labels.extend(items)
    top_types = Counter(labels).most_common(10)
    hourly = violations["hour_of_day"].value_counts().sort_index()
    weekday = violations["day_name"].value_counts()
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return {
        "total_violations": int(len(violations)),
        "date_range": {
            "start": violations["created_datetime"].min().isoformat(),
            "end": violations["created_datetime"].max().isoformat(),
        },
        "top_police_station": violations["police_station"].value_counts().idxmax(),
        "top_junction": violations[violations["has_junction"]]["junction_name"].value_counts().idxmax()
        if violations["has_junction"].any()
        else "No Junction",
        "carriageway_blocking_pct": round(float(violations["is_carriageway_blocking"].mean() * 100), 2),
        "approved_rate": round(float((violations["is_approved"] == True).mean() * 100), 2),  # noqa: E712
        "active_hotspots": len(clusters),
        "avg_pii_score": round(float(grid["pii_score"].mean()), 4),
        "avg_eps_score": round(float(grid["eps_score"].mean()), 4) if "eps_score" in grid else 0.0,
        "top_violation_types": [{"label": label, "count": count} for label, count in top_types],
        "top_vehicle_types": [
            {"label": label, "count": int(count)}
            for label, count in violations["vehicle_type"].value_counts().head(10).items()
        ],
        "hourly_distribution": {str(int(k)): int(v) for k, v in hourly.items()},
        "weekday_distribution": {day: int(weekday.get(day, 0)) for day in weekday_order},
        "station_counts": [
            {"station": station, "count": int(count)}
            for station, count in violations["police_station"].value_counts().head(20).items()
        ],
    }
