import pandas as pd
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import PlainTextResponse, Response

from app.schemas.models import DeploymentRequest, SimulationRequest
from app.services.analytics_service import build_summary
from app.services.data_store import data_store
from app.services.deployment_service import recommend_deployment
from app.services.export_service import export_geojson, export_priority_csv, export_summary_json
from app.services.forecast_service import get_forecast_metrics, get_forecast_top
from app.services.hotspot_service import get_clusters, get_heatmap, get_priority_zones
from app.services.pii_service import compute_zone_impact, violation_breakdown_for_cluster, violation_breakdown_for_h3
from app.services.pipeline_service import run_pipeline
from app.services.simulation_service import run_simulation

router = APIRouter()


def _ensure_ready() -> None:
    if not data_store.ready or data_store.violations.empty:
        raise HTTPException(status_code=503, detail="Dataset not processed. POST /api/v1/ingest/run-pipeline first.")


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "ready": data_store.ready, "records": len(data_store.violations)}


@router.post("/ingest/run-pipeline")
def trigger_pipeline() -> dict:
    return run_pipeline()


@router.post("/ingest/upload")
async def upload_csv(file: UploadFile = File(...)) -> dict:
    from app.config import settings

    target = settings.storage_dir / "uploaded.csv"
    content = await file.read()
    target.write_bytes(content)
    return run_pipeline(target)


@router.get("/analytics/summary")
def analytics_summary() -> dict:
    _ensure_ready()
    if data_store.analytics_cache:
        return data_store.analytics_cache
    return build_summary(data_store.violations, data_store.grid_cells, data_store.clusters)


@router.get("/violations")
def list_violations(
    station: str | None = None,
    h3_index: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    _ensure_ready()
    df = data_store.violations.copy()
    if station:
        df = df[df["police_station"] == station]
    if h3_index:
        df = df[df["h3_index"] == h3_index]
    total = len(df)
    start = (page - 1) * limit
    end = start + limit
    rows = df.iloc[start:end]
    records = []
    for row in rows.itertuples(index=False):
        records.append(
            {
                "id": row.id,
                "latitude": float(row.latitude),
                "longitude": float(row.longitude),
                "vehicle_type": row.vehicle_type,
                "violation_labels": list(row.violation_labels),
                "police_station": row.police_station,
                "junction_name": row.junction_name,
                "created_datetime": row.created_datetime.isoformat(),
                "severity_score": float(row.severity_score),
                "h3_index": row.h3_index,
            }
        )
    return {"total": total, "page": page, "limit": limit, "records": records}


@router.get("/hotspots")
def hotspots(
    station: str | None = None,
    min_eps: float = 0.0,
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    _ensure_ready()
    return {"hotspots": get_clusters(station=station, min_eps=min_eps, limit=limit)}


@router.get("/hotspots/heatmap")
def heatmap(
    metric: str = Query("pii", pattern="^(pii|eps|count|pii_score|eps_score|violations_7d|predicted_count)$"),
    station: str | None = None,
    limit: int = Query(500, ge=1, le=2000),
) -> dict:
    _ensure_ready()
    metric_map = {"pii": "pii_score", "eps": "eps_score", "count": "violations_7d"}
    return get_heatmap(metric=metric_map.get(metric, metric), station=station, limit=limit)


@router.get("/zones/priority")
def priority_zones(station: str | None = None, top: int = Query(20, ge=1, le=100)) -> dict:
    _ensure_ready()
    return {"zones": get_priority_zones(station=station, top=top)}


@router.get("/impact")
def parking_impact(h3_index: str | None = None, cluster_id: int | None = None) -> dict:
    _ensure_ready()
    if cluster_id is not None:
        cluster = next((item for item in data_store.clusters if item["cluster_id"] == cluster_id), None)
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        grid = data_store.grid_cells[data_store.grid_cells["h3_index"].isin(cluster["h3_cells"])]
        aggregate = {
            "pii_score": float(grid["pii_score"].mean()),
            "multi_offence_rate": float(grid["multi_offence_rate"].mean()),
            "heavy_vehicle_share": float(grid["heavy_vehicle_share"].mean()),
            "carriageway_blocking_rate": float(grid["carriageway_blocking_rate"].mean()),
            "junction_spillover_flag": bool(grid["junction_spillover_flag"].any()),
            "violations_7d": int(grid["violations_7d"].sum()),
        }
        breakdown = violation_breakdown_for_cluster(data_store.violations, cluster["h3_cells"])
        return compute_zone_impact(pd.Series(aggregate), breakdown)
    if not h3_index:
        raise HTTPException(status_code=400, detail="Provide h3_index or cluster_id")
    row = data_store.grid_cells[data_store.grid_cells["h3_index"] == h3_index]
    if row.empty:
        raise HTTPException(status_code=404, detail="Zone not found")
    breakdown = violation_breakdown_for_h3(data_store.violations, h3_index)
    return compute_zone_impact(row.iloc[0], breakdown)


@router.get("/forecast/top")
def forecast_top(station: str | None = None, limit: int = Query(20, ge=1, le=100)) -> dict:
    _ensure_ready()
    return {"forecasts": get_forecast_top(station=station, limit=limit), "metrics": get_forecast_metrics()}


@router.get("/forecast/metrics")
def forecast_metrics() -> dict:
    _ensure_ready()
    return get_forecast_metrics()


@router.post("/deployment/recommend")
def deployment_recommend(payload: DeploymentRequest) -> dict:
    _ensure_ready()
    return recommend_deployment(
        police_station=payload.police_station,
        officers_available=payload.officers_available,
        shift_start_hour=payload.shift_start_hour,
        max_zones_per_officer=payload.max_zones_per_officer,
    )


@router.get("/junctions")
def junctions(top: int = Query(20, ge=1, le=200)) -> dict:
    _ensure_ready()
    stats = data_store.junction_stats.head(top)
    return {
        "junctions": stats.to_dict(orient="records"),
    }


@router.get("/stations")
def stations(top: int = Query(20, ge=1, le=100)) -> dict:
    _ensure_ready()
    stats = data_store.station_stats.head(top)
    return {"stations": stats.to_dict(orient="records")}


@router.post("/simulation/run")
def simulation(payload: SimulationRequest) -> dict:
    _ensure_ready()
    return run_simulation(
        police_station=payload.police_station,
        officer_count=payload.officer_count,
        patrol_hours=payload.patrol_hours,
        target_eps_threshold=payload.target_eps_threshold,
    )


@router.get("/export/summary")
def export_summary() -> dict:
    _ensure_ready()
    return export_summary_json()


@router.get("/export/priority.csv")
def export_priority() -> PlainTextResponse:
    _ensure_ready()
    return PlainTextResponse(export_priority_csv(), media_type="text/csv")


@router.get("/export/heatmap.geojson")
def export_heatmap_geojson() -> Response:
    _ensure_ready()
    import json

    return Response(json.dumps(export_geojson()), media_type="application/geo+json")
