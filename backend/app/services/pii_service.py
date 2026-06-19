"""Parking Impact Index calculations."""

from __future__ import annotations

import pandas as pd

from app.ml.severity import get_severity


def compute_zone_impact(grid_row: pd.Series, violation_breakdown: dict[str, int] | None = None) -> dict:
    breakdown = violation_breakdown or {}
    return {
        "pii_score": round(float(grid_row["pii_score"]), 4),
        "severity_breakdown": breakdown,
        "multi_offence_rate": round(float(grid_row["multi_offence_rate"]), 4),
        "heavy_vehicle_share": round(float(grid_row["heavy_vehicle_share"]), 4),
        "carriageway_blocking_rate": round(float(grid_row["carriageway_blocking_rate"]), 4),
        "junction_spillover": bool(grid_row["junction_spillover_flag"]),
        "violations_7d": int(grid_row["violations_7d"]),
        "interpretation": _interpret(grid_row),
    }


def _interpret(row: pd.Series) -> str:
    parts = []
    if row["carriageway_blocking_rate"] > 0.1:
        parts.append("elevated carriageway-blocking offences")
    if row["multi_offence_rate"] > 0.1:
        parts.append(" frequent multi-offence incidents")
    if row["heavy_vehicle_share"] > 0.35:
        parts.append(" high share of space-consuming vehicle types")
    if row["junction_spillover_flag"]:
        parts.append(" junction spillover pressure")
    if not parts:
        return "Moderate parking pressure based on recent violation severity and density."
    return "Zone shows " + ", ".join(parts) + "."


def violation_breakdown_for_h3(violations: pd.DataFrame, h3_index: str) -> dict[str, int]:
    subset = violations[violations["h3_index"] == h3_index]
    labels: list[str] = []
    for items in subset["violation_labels"]:
        labels.extend(items)
    counts = pd.Series(labels).value_counts().head(10)
    return {label: int(count) for label, count in counts.items()}


def violation_breakdown_for_cluster(violations: pd.DataFrame, h3_cells: list[str]) -> dict[str, int]:
    subset = violations[violations["h3_index"].isin(h3_cells)]
    labels = [label for items in subset["violation_labels"] for label in items]
    counts = pd.Series(labels).value_counts().head(10)
    return {label: int(count) for label, count in counts.items()}
