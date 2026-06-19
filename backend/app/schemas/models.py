from pydantic import BaseModel, Field


class Centroid(BaseModel):
    lat: float
    lon: float


class DeploymentRequest(BaseModel):
    police_station: str = "Upparpet"
    officers_available: list[str] = Field(default_factory=lambda: ["FKUSR00021", "FKUSR00332"])
    shift_start_hour: int = 18
    shift_duration_hours: int = 4
    max_zones_per_officer: int = 3


class SimulationRequest(BaseModel):
    police_station: str | None = None
    officer_count: int = 4
    patrol_hours: int = 4
    target_eps_threshold: float = 0.6


class PipelineResponse(BaseModel):
    status: str
    records: int
    grid_cells: int
    clusters: int
    forecast_metrics: dict
    processed_at: str
