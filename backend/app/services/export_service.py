"""Report export service."""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime

from app.services.analytics_service import build_summary
from app.services.data_store import data_store
from app.services.hotspot_service import get_priority_zones


def export_summary_json() -> dict:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": data_store.analytics_cache or build_summary(
            data_store.violations, data_store.grid_cells, data_store.clusters
        ),
        "forecast_metrics": data_store.forecast_metrics,
        "priority_zones": get_priority_zones(top=50),
        "clusters": data_store.clusters[:50],
    }


def export_priority_csv() -> str:
    zones = get_priority_zones(top=100)
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "h3_index",
            "police_station",
            "eps_score",
            "pii_score",
            "violations_7d",
            "predicted_count",
            "recommended_action",
        ],
    )
    writer.writeheader()
    for zone in zones:
        writer.writerow(
            {
                "h3_index": zone["h3_index"],
                "police_station": zone["police_station"],
                "eps_score": zone["eps_score"],
                "pii_score": zone["pii_score"],
                "violations_7d": zone["violations_7d"],
                "predicted_count": zone["predicted_count"],
                "recommended_action": zone["recommended_action"],
            }
        )
    return buffer.getvalue()


def export_geojson() -> dict:
    from app.services.hotspot_service import get_heatmap

    return get_heatmap(metric="eps", limit=500)
