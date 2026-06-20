"""Officer deployment recommendation engine."""

from __future__ import annotations
import pandas as pd
from app.services.data_store import data_store
from app.services.eps_service import build_priority_zone


def recommend_deployment(
    police_station: str,
    officers_available: list[str],
    shift_start_hour: int = 18,
    max_zones_per_officer: int = 3,
) -> dict:
    grid = data_store.grid_cells
    zones = grid[grid["dominant_station"] == police_station].sort_values("eps_score", ascending=False)
    if zones.empty:
        zones = grid.sort_values("eps_score", ascending=False)
    zones = zones.head(max(len(officers_available) * max_zones_per_officer, max_zones_per_officer))

    officer_stats = data_store.officer_stats.set_index("created_by_id") if not data_store.officer_stats.empty else None
    recommendations = []
    zone_iter = iter(zones.itertuples(index=False))
    for officer_id in officers_available:
        productivity = 1.0
        if officer_stats is not None and officer_id in officer_stats.index:
            productivity = float(officer_stats.loc[officer_id, "productivity_score"])
        assignments = []
        expected_total = 0.0
        for _ in range(max_zones_per_officer):
            try:
                zone = next(zone_iter)
            except StopIteration:
                break
            zone_dict = build_priority_zone(pd.Series(zone._asdict()))
            expected = float(zone.predicted_count) * productivity
            expected_total += expected
            assignments.append(
                {
                    **zone_dict,
                    "expected_violations": round(expected, 2),
                    "rationale": (
                        f"High EPS ({zone_dict['eps_score']}); forecast {zone_dict['predicted_count']} violations; "
                        f"device coverage {int(zone.device_coverage_7d)}"
                    ),
                }
            )
        recommendations.append(
            {
                "officer_id": officer_id,
                "assignments": assignments,
                "expected_total_violations": round(expected_total, 2),
            }
        )

    assigned_cells = {
        assignment["h3_index"]
        for rec in recommendations
        for assignment in rec["assignments"]
    }
    uncovered = zones[~zones["h3_index"].isin(assigned_cells)].head(5)
    return {
        "shift_start_hour": shift_start_hour,
        "police_station": police_station,
        "recommendations": recommendations,
        "uncovered_high_risk_zones": [
            build_priority_zone(row) for _, row in uncovered.iterrows()
        ],
    }
