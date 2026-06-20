"""DBSCAN hotspot clustering on H3-weighted centroids."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

from app.config import settings
from app.ml.features import km_to_deg_lat, km_to_deg_lon


@dataclass
class HotspotCluster:
    cluster_id: int
    centroid_lat: float
    centroid_lon: float
    violation_count: int
    pii_score: float
    eps_score: float
    dominant_station: str
    dominant_junction: str
    carriageway_blocking_rate: float
    top_violation_types: list[str]
    h3_cells: list[str]
    location_desc: str


def run_dbscan_clusters(violations: pd.DataFrame, grid: pd.DataFrame) -> list[HotspotCluster]:
    """Cluster active H3 cells using weighted DBSCAN."""
    active = grid[grid["violations_7d"] > 0].copy()
    if active.empty:
        return []

    mean_lat = active["centroid_lat"].mean()
    eps_lat = km_to_deg_lat(settings.dbscan_eps_km)
    eps_lon = km_to_deg_lon(settings.dbscan_eps_km, mean_lat)
    coords = active[["centroid_lat", "centroid_lon"]].to_numpy()
    scaled = np.column_stack([coords[:, 0] / eps_lat, coords[:, 1] / eps_lon])

    sample_weights = np.sqrt(active["violations_7d"].to_numpy())
    clustering = DBSCAN(eps=1.0, min_samples=settings.dbscan_min_samples).fit(scaled, sample_weight=sample_weights)
    active = active.assign(cluster_label=clustering.labels_)

    violation_lookup = violations.groupby("h3_index")["violation_labels"].apply(
        lambda series: [label for labels in series for label in labels]
    )

    clusters: list[HotspotCluster] = []
    for cluster_id, group in active[active["cluster_label"] >= 0].groupby("cluster_label"):
        total = int(group["violations_7d"].sum())
        pii = float(group["pii_score"].mean())
        eps = float(group["eps_score"].mean()) if "eps_score" in group else pii
        station = group.sort_values("violations_7d", ascending=False)["dominant_station"].iloc[0]
        junction = group.sort_values("violations_7d", ascending=False)["dominant_junction"].iloc[0]

        labels: list[str] = []
        for h3_index in group["h3_index"]:
            labels.extend(violation_lookup.get(h3_index, []))
        top_types = pd.Series(labels).value_counts().head(5).index.tolist() if labels else []

        # Identify top locations / address description from geocoded locations in violations
        cluster_violations = violations[violations["h3_index"].isin(group["h3_index"])]
        valid_locations = cluster_violations["location"].dropna()
        top_locations = valid_locations.value_counts().index[:2].tolist()
        location_desc = " / ".join(top_locations) if top_locations else "Unknown Location"
        if len(location_desc) > 80:
            location_desc = location_desc[:77] + "..."

        blocking_rate = float(group["carriageway_blocking_rate"].mean())
        clusters.append(
            HotspotCluster(
                cluster_id=int(cluster_id),
                centroid_lat=float(np.average(group["centroid_lat"], weights=group["violations_7d"])),
                centroid_lon=float(np.average(group["centroid_lon"], weights=group["violations_7d"])),
                violation_count=total,
                pii_score=pii,
                eps_score=eps,
                dominant_station=station,
                dominant_junction=junction,
                carriageway_blocking_rate=blocking_rate,
                top_violation_types=top_types,
                h3_cells=group["h3_index"].tolist(),
                location_desc=location_desc,
            )
        )

    clusters.sort(key=lambda item: item.eps_score, reverse=True)
    for idx, cluster in enumerate(clusters, start=1):
        cluster.cluster_id = idx
    return clusters


def clusters_to_dict(clusters: list[HotspotCluster]) -> list[dict]:
    return [
        {
            "cluster_id": cluster.cluster_id,
            "centroid": {"lat": cluster.centroid_lat, "lon": cluster.centroid_lon},
            "violation_count": cluster.violation_count,
            "pii_score": round(cluster.pii_score, 4),
            "eps_score": round(cluster.eps_score, 4),
            "dominant_station": cluster.dominant_station,
            "dominant_junction": cluster.dominant_junction,
            "carriageway_blocking_rate": round(cluster.carriageway_blocking_rate, 4),
            "top_violation_types": cluster.top_violation_types,
            "h3_cells": cluster.h3_cells,
            "location_desc": cluster.location_desc,
        }
        for cluster in clusters
    ]
