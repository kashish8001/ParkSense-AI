"""Simulation service for patrol impact what-if analysis."""

from __future__ import annotations

from app.services.data_store import data_store


def run_simulation(
    police_station: str | None,
    officer_count: int,
    patrol_hours: int,
    target_eps_threshold: float,
) -> dict:
    grid = data_store.grid_cells.copy()
    if police_station:
        grid = grid[grid["dominant_station"] == police_station]
    high_risk = grid[grid["eps_score"] >= target_eps_threshold]
    zones_coverable = min(officer_count * 2, len(high_risk))
    selected = high_risk.sort_values("eps_score", ascending=False).head(zones_coverable)
    baseline_violations = float(selected["violations_7d"].sum())
    baseline_severity = float(selected["severity_weighted_7d"].sum())
    effectiveness = min(0.15 * patrol_hours * officer_count, 0.65)
    projected_reduction = baseline_violations * effectiveness
    projected_severity_reduction = baseline_severity * effectiveness
    return {
        "inputs": {
            "police_station": police_station or "City-wide",
            "officer_count": officer_count,
            "patrol_hours": patrol_hours,
            "target_eps_threshold": target_eps_threshold,
        },
        "baseline": {
            "high_risk_zones": int(len(high_risk)),
            "zones_selected": int(len(selected)),
            "weekly_violations": round(baseline_violations, 2),
            "severity_weighted_total": round(baseline_severity, 2),
        },
        "projected_outcomes": {
            "effectiveness_rate": round(effectiveness, 4),
            "violations_prevented_weekly": round(projected_reduction, 2),
            "severity_reduction_weekly": round(projected_severity_reduction, 2),
            "residual_violations_weekly": round(baseline_violations - projected_reduction, 2),
        },
        "selected_zones": [
            {
                "h3_index": row.h3_index,
                "eps_score": round(float(row.eps_score), 4),
                "violations_7d": int(row.violations_7d),
                "police_station": row.dominant_station,
            }
            for row in selected.itertuples(index=False)
        ],
    }
