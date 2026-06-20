"""CSV ingestion and violation record normalization."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import settings
from app.ml.severity import (
    HEAVY_VEHICLE_TYPES,
    get_severity,
    is_carriageway_blocking,
)

PIN_CODE_PATTERN = re.compile(r"Pin-(\d{6})", re.IGNORECASE)


def parse_violation_list(value: object) -> list[str]:
    if pd.isna(value) or value is None:
        return []
    text = str(value).strip()
    if not text or text.upper() == "NULL":
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [str(item).strip().upper() for item in parsed]
        return [str(parsed).strip().upper()]
    except (ValueError, SyntaxError):
        return [text.upper()]


def parse_offence_codes(value: object) -> list[int]:
    if pd.isna(value) or value is None:
        return []
    text = str(value).strip()
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [int(item) for item in parsed]
        return [int(parsed)]
    except (ValueError, SyntaxError):
        return []


def extract_pin_code(location: object) -> str | None:
    if pd.isna(location):
        return None
    match = PIN_CODE_PATTERN.search(str(location))
    return match.group(1) if match else None


def extract_location_flags(location: object) -> dict[str, bool]:
    if pd.isna(location):
        return {"has_metro_keyword": False, "has_market_keyword": False, "has_main_road": False}
    text = str(location).upper()
    return {
        "has_metro_keyword": "METRO" in text,
        "has_market_keyword": "MARKET" in text,
        "has_main_road": "MAIN ROAD" in text or "RING ROAD" in text,
    }


def load_raw_csv(csv_path: Path | None = None) -> pd.DataFrame:
    path = csv_path or (settings.data_dir / settings.default_csv)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    return pd.read_csv(path, low_memory=False)


def transform_violations(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and enrich raw violation records."""
    result = df.copy()
    
    # Drop 100% null columns to optimize memory usage
    result = result.drop(columns=["description", "closed_datetime", "action_taken_timestamp"], errors="ignore")

    result["latitude"] = pd.to_numeric(result["latitude"], errors="coerce")
    result["longitude"] = pd.to_numeric(result["longitude"], errors="coerce")
    result["created_datetime"] = pd.to_datetime(result["created_datetime"], utc=True, errors="coerce")
    result["modified_datetime"] = pd.to_datetime(result["modified_datetime"], utc=True, errors="coerce")
    result["validation_timestamp"] = pd.to_datetime(result["validation_timestamp"], utc=True, errors="coerce")

    labels = result["violation_type"].apply(parse_violation_list)
    result["violation_labels"] = labels
    result["offence_codes_list"] = result["offence_code"].apply(parse_offence_codes)
    result["offence_count"] = labels.apply(len).clip(lower=1)
    result["severity_score"] = labels.apply(
        lambda items: float(sum(get_severity(label) for label in items)) if items else 0.5
    )
    result["is_carriageway_blocking"] = labels.apply(
        lambda items: any(is_carriageway_blocking(label) for label in items)
    )
    result["is_multi_offence"] = result["offence_count"] > 1

    status = result["validation_status"].astype(str).str.strip().str.lower()
    result["is_approved"] = np.where(status == "approved", True, np.where(status.isin(["rejected", "duplicate"]), False, np.nan))
    result["validation_status_clean"] = status.replace("nan", np.nan)

    result["pin_code"] = result["location"].apply(extract_pin_code)
    # Optimized: pd.DataFrame of list of dicts is ~100x faster than applying pd.Series row-by-row
    flags = pd.DataFrame(list(result["location"].apply(extract_location_flags)), index=result.index)
    result = pd.concat([result, flags], axis=1)

    result["vehicle_type"] = result["vehicle_type"].astype(str).str.strip().str.upper()
    result["police_station"] = result["police_station"].fillna("Unknown").astype(str).str.strip()
    result["junction_name"] = result["junction_name"].fillna("No Junction").astype(str).str.strip()
    result["has_junction"] = result["junction_name"] != "No Junction"
    result["is_heavy_vehicle"] = result["vehicle_type"].isin(HEAVY_VEHICLE_TYPES)

    result["hour_of_day"] = result["created_datetime"].dt.hour
    result["day_of_week"] = result["created_datetime"].dt.dayofweek
    result["day_name"] = result["created_datetime"].dt.day_name()
    result["month"] = result["created_datetime"].dt.month
    result["is_weekend"] = result["day_of_week"].isin([5, 6])

    result["is_outlier"] = (
        result["latitude"].lt(settings.bbox_lat_min)
        | result["latitude"].gt(settings.bbox_lat_max)
        | result["longitude"].lt(settings.bbox_lon_min)
        | result["longitude"].gt(settings.bbox_lon_max)
    )

    result = result.dropna(subset=["latitude", "longitude", "created_datetime"])
    return result.reset_index(drop=True)


def ingest_csv(csv_path: Path | None = None) -> pd.DataFrame:
    raw = load_raw_csv(csv_path)
    return transform_violations(raw)
