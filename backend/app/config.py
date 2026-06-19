from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PARKSENSE_", env_file=".env", extra="ignore")

    app_name: str = "ParkSense AI"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    root_dir: Path = Path(__file__).resolve().parents[2]
    data_dir: Path = root_dir / "data"
    storage_dir: Path = Path(__file__).resolve().parents[1] / "storage"
    default_csv: str = "jan to may police violation_anonymized791b166.csv"

    h3_resolution: int = 8
    bbox_lat_min: float = 12.7
    bbox_lat_max: float = 13.2
    bbox_lon_min: float = 77.3
    bbox_lon_max: float = 77.9

    dbscan_eps_km: float = 0.15
    dbscan_min_samples: int = 15
    forecast_top_cells: int = 300
    eps_weights: dict[str, float] = {
        "density_7d": 0.25,
        "severity_7d": 0.25,
        "repeat_rate": 0.15,
        "forecast_24h": 0.20,
        "device_gap": 0.10,
        "junction_spillover": 0.05,
    }


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
