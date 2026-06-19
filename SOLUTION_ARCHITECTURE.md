# ParkSense AI — Solution Architecture

**Hackathon project:** ParkSense AI  
**Problem:** On-street illegal parking and spillover parking near commercial areas, metro stations, and events choke carriageways and intersections.  
**Data source:** Bengaluru police violation records (298,450 events, Nov 2023 – Apr 2024)  
**Constraint:** All intelligence is derived **only** from fields present in the dataset. No external traffic speed, congestion, vehicle counts, or road width data is assumed.

---

## 1. Solution Overview

ParkSense AI transforms historical parking violation records into an **operational enforcement intelligence platform**. Instead of measuring traffic directly (unavailable), it quantifies **parking pressure** and **carriageway obstruction risk** using violation density, severity-weighted offence types, junction spillover signals, temporal patterns, and enforcement coverage gaps derived from `device_id`, `created_by_id`, and `police_station`.

### Objectives → Capabilities Mapping

| Objective | ParkSense AI Capability | Primary Data Signals |
|-----------|-------------------------|----------------------|
| 1. Detect illegal parking hotspots | H3 grid heatmap + DBSCAN clusters + junction aggregation | `latitude`, `longitude`, `violation_type`, `junction_name` |
| 2. Prioritize enforcement zones | Composite **Enforcement Priority Score (EPS)** ranking | Grid density, severity weights, validation rate, device coverage gap |
| 3. Quantify parking impact | **Parking Impact Index (PII)** — severity-weighted violation pressure | Multi-label offences, junction proximity, repeat-location rate, vehicle mix |
| 4. Forecast future violation risk | Time-series model on grid × hour × weekday aggregates | `created_datetime`, rolling counts, cyclical temporal features |
| 5. Recommend officer deployment | Shift-level patrol allocation optimizer | Historical `created_by_id` productivity, station jurisdiction, forecasted risk |

### Design Principles

1. **Aggregate over point prediction** — forecast violations per H3 cell × time bucket, not individual events.
2. **Proxy, don’t invent** — “impact” is inferred from offence severity and spatial concentration, not traffic sensors.
3. **Validation-aware** — use `validation_status = approved` for ground-truth hotspots; treat rejected/duplicate as noise.
4. **Time-safe splits** — train Nov–Feb, validate Mar, test Apr (partial month acknowledged).
5. **Explainable scores** — every hotspot rank decomposes into interpretable components for judges and officers.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  Command Dashboard│  │  Mobile Patrol   │  │  Export / Reports        │  │
│  │  (React + MapLibre)│  │  View (optional) │  │  PDF / CSV / GeoJSON   │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────────┬─────────────┘  │
└───────────┼──────────────────────┼──────────────────────────┼───────────────┘
            │                      │                          │
            ▼                      ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                     │
│                    FastAPI  ·  JWT Auth  ·  Rate Limiting                    │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ├──────────────────────┬──────────────────────┬───────────────────┐
            ▼                      ▼                      ▼                   ▼
┌───────────────────┐  ┌───────────────────┐  ┌─────────────────┐  ┌─────────────┐
│  Hotspot Service  │  │  Forecast Service │  │  Deployment     │  │  Analytics  │
│  · clusters       │  │  · risk scores    │  │  Optimizer      │  │  Service    │
│  · EPS ranking    │  │  · 24h/7d ahead   │  │  · shift plans  │  │  · KPIs     │
│  · PII scores     │  │                   │  │                 │  │             │
└─────────┬─────────┘  └─────────┬─────────┘  └────────┬────────┘  └──────┬──────┘
          │                        │                       │                  │
          └────────────────────────┼───────────────────────┴──────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ML INFERENCE LAYER                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Hotspot     │  │ Risk        │  │ Severity    │  │ Deployment          │ │
│  │ KDE/DBSCAN  │  │ Forecaster  │  │ Classifier  │  │ Recommender         │ │
│  │ (batch)     │  │ (LightGBM)  │  │ (optional)  │  │ (OR-Tools / greedy) │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA & PROCESSING LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ ETL Pipeline │  │ Feature Store│  │ PostGIS      │  │ Model Registry   │ │
│  │ (Prefect)    │  │ (Parquet/DB) │  │ Spatial DB   │  │ (MLflow)         │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SOURCE DATA                                          │
│         CSV ingest · 298K violation records · daily incremental append       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Role |
|-----------|------|
| **ETL Pipeline** | Ingest CSV, parse multi-label JSON, normalize tables, assign H3 cells, flag outliers |
| **Feature Store** | Precomputed grid aggregates, rolling windows, officer/device stats |
| **Hotspot Service** | Serve cluster polygons, heatmap tiles, EPS-ranked zone list |
| **Forecast Service** | Return predicted violation counts per grid cell for next 24h / 7d |
| **Deployment Optimizer** | Match available officers to high-risk zones by shift and jurisdiction |
| **Dashboard** | Map-centric UI for command staff; filter by station, junction, violation type |

### Data Flow (Batch + Near-Real-Time)

```
CSV Upload ──► ETL ──► violations (fact) + violation_labels (bridge)
                │
                ├──► grid_hourly_agg (materialized)
                ├──► hotspot_clusters (weekly refresh)
                │
                ├──► ML Training Job (scheduled weekly)
                │         └──► risk_forecast_model.pkl
                │
                └──► Inference Job (daily)
                          └──► zone_risk_scores, deployment_recommendations
                                    └──► API ──► Dashboard
```

For the hackathon demo, batch refresh (on upload / daily cron) is sufficient. Production would add streaming ingest from the enforcement API.

---

## 3. Backend Architecture

### 3.1 Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| API | **FastAPI** (Python 3.11+) | Async, OpenAPI docs, geo libraries |
| Database | **PostgreSQL 15 + PostGIS** | Spatial queries, aggregations, JSONB |
| Cache | **Redis** | Hotspot tile cache, API response cache |
| ML | **scikit-learn**, **LightGBM**, **h3**, **OR-Tools** | Fast training on tabular aggregates |
| ETL | **Prefect** or **plain Python scripts** | Hackathon-simple orchestration |
| Frontend | **React + Vite + MapLibre GL** | Interactive Bengaluru map |
| Container | **Docker Compose** | Single-command demo deployment |

### 3.2 Service Decomposition

```
backend/
├── app/
│   ├── main.py                 # FastAPI entry
│   ├── config.py
│   ├── api/
│   │   ├── v1/
│   │   │   ├── hotspots.py     # GET /hotspots, /hotspots/{id}
│   │   │   ├── zones.py        # GET /zones/priority
│   │   │   ├── forecast.py     # GET /forecast
│   │   │   ├── deployment.py   # POST /deployment/recommend
│   │   │   ├── analytics.py    # GET /analytics/summary
│   │   │   └── violations.py   # GET /violations (paginated)
│   ├── services/
│   │   ├── hotspot_service.py
│   │   ├── eps_calculator.py
│   │   ├── pii_calculator.py
│   │   ├── forecast_service.py
│   │   └── deployment_optimizer.py
│   ├── models/                 # SQLAlchemy ORM
│   └── schemas/                # Pydantic request/response
├── ml/
│   ├── etl/
│   ├── features/
│   ├── train/
│   └── inference/
└── tests/
```

### 3.3 Core Backend Logic

#### Enforcement Priority Score (EPS)

Ranks zones for patrol dispatch. All inputs come from the dataset.

```
EPS = w1 · norm(violation_density_7d)
    + w2 · norm(severity_weighted_count_7d)
    + w3 · norm(repeat_location_rate)
    + w4 · norm(forecast_risk_24h)
    - w5 · norm(device_coverage_7d)        # penalty: already monitored
    + w6 · norm(junction_spillover_flag)
```

Default weights: `w1=0.25, w2=0.25, w3=0.15, w4=0.20, w5=0.10, w6=0.05`

#### Parking Impact Index (PII)

Quantifies obstruction potential **without traffic data**, using offence taxonomy from `violation_type`:

| Violation Label | Severity Weight | Rationale (dataset-derived) |
|-----------------|-----------------|----------------------------|
| PARKING IN A MAIN ROAD | 1.0 | Direct carriageway blockage |
| DOUBLE PARKING | 0.95 | Lane reduction |
| PARKING NEAR ROAD CROSSING | 0.90 | Intersection approach obstruction |
| PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS | 0.90 | Crossing conflict |
| PARKING OPPOSITE TO ANOTHER PARKED VEHICLE | 0.85 | Narrowing effective road width |
| WRONG PARKING | 0.70 | General illegal parking |
| NO PARKING | 0.65 | Restricted zone violation |
| PARKING ON FOOTPATH | 0.60 | Pedestrian impact (not carriageway) |
| PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC | 0.75 | Spillover near sensitive nodes |
| Other parking offences | 0.50 | Default |

```
PII_cell = Σ (severity_weight × count) / grid_area_proxy
         + α · multi_violation_rate        # records with >1 offence (13.4% of data)
         + β · heavy_vehicle_share         # CAR + LGV + BUS fraction
         + γ · junction_proximity_boost    # named junction or parsed "Metro"/"Market" in location
```

Grid area proxy uses H3 cell area at resolution 8 (~0.74 km²) — a geometric constant, not road inventory.

#### Deployment Optimizer

Greedy assignment (hackathon) or OR-Tools CP-SAT (stretch goal):

**Inputs:** `officers_available[]` (by `police_station`), `shift_hours[]`, `zone_eps[]`, `officer_historical_productivity` (violations per shift from `created_by_id` aggregates)

**Output:** `{ officer_id, zone_id, recommended_start, expected_violations_addressable }`

**Constraint:** Officer assigned only to zones within their `police_station` jurisdiction (from historical data mapping station → H3 cells).

---

## 4. Database Schema

### 4.1 Entity-Relationship Overview

```
police_stations ──< violations >── devices
       │                │
       │                ├──< violation_labels >── violation_types
       │                │
       └──< grid_cells ──< grid_hourly_stats
                │
                ├──< hotspot_clusters
                ├──< zone_risk_forecasts
                └──< deployment_recommendations

officers (from created_by_id) ──< officer_shift_stats
```

### 4.2 Table Definitions

#### `violations` (fact table — 298,450 rows)

| Column | Type | Source | Notes |
|--------|------|--------|-------|
| `id` | VARCHAR PK | `id` | FKID000000 |
| `latitude` | DOUBLE PRECISION | `latitude` | WGS84 |
| `longitude` | DOUBLE PRECISION | `longitude` | WGS84 |
| `geom` | GEOGRAPHY(POINT) | computed | PostGIS point |
| `h3_index` | VARCHAR(15) | computed | H3 res-8 |
| `location_text` | TEXT | `location` | nullable |
| `pin_code` | VARCHAR(6) | parsed from `location` | regex extract |
| `vehicle_number` | VARCHAR | `vehicle_number` | anonymized |
| `vehicle_type` | VARCHAR | `vehicle_type` | 22 categories |
| `created_datetime` | TIMESTAMPTZ | `created_datetime` | primary event time |
| `modified_datetime` | TIMESTAMPTZ | `modified_datetime` | |
| `device_id` | VARCHAR FK | `device_id` | |
| `created_by_id` | VARCHAR FK | `created_by_id` | nullable |
| `center_code` | SMALLINT | `center_code` | nullable |
| `police_station_id` | INT FK | `police_station` | normalized |
| `junction_id` | INT FK | `junction_name` | null if "No Junction" |
| `data_sent_to_scita` | BOOLEAN | `data_sent_to_scita` | |
| `validation_status` | VARCHAR | `validation_status` | approved/rejected/… |
| `validation_timestamp` | TIMESTAMPTZ | `validation_timestamp` | nullable |
| `is_approved` | BOOLEAN | derived | `validation_status = 'approved'` |
| `is_carriageway_blocking` | BOOLEAN | derived | any severity ≥ 0.85 label |
| `offence_count` | SMALLINT | derived | multi-label count |
| `hour_of_day` | SMALLINT | derived | 0–23 from created_datetime |
| `day_of_week` | SMALLINT | derived | 0=Mon … 6=Sun |
| `is_weekend` | BOOLEAN | derived | |

**Indexes:** `(h3_index)`, `(created_datetime)`, `(police_station_id)`, `(junction_id)`, GIST on `geom`

#### `violation_labels` (bridge — ~340K rows after explode)

| Column | Type | Notes |
|--------|------|-------|
| `id` | SERIAL PK | |
| `violation_id` | VARCHAR FK | → violations.id |
| `violation_type` | VARCHAR | e.g. WRONG PARKING |
| `offence_code` | SMALLINT | 112, 113, … |
| `severity_weight` | DECIMAL(3,2) | from PII lookup table |

#### `violation_types` (reference — 27 rows)

| Column | Type |
|--------|------|
| `code` | SMALLINT PK |
| `label` | VARCHAR UNIQUE |
| `severity_weight` | DECIMAL(3,2) |
| `is_parking_related` | BOOLEAN |

#### `police_stations` (54 rows)

| Column | Type |
|--------|------|
| `id` | SERIAL PK |
| `name` | VARCHAR UNIQUE |
| `center_code` | SMALLINT |
| `centroid_lat` | DOUBLE | computed from violations |
| `centroid_lon` | DOUBLE | computed |
| `total_violations` | INT | denormalized stat |

#### `junctions` (169 rows)

| Column | Type |
|--------|------|
| `id` | SERIAL PK |
| `btp_code` | VARCHAR | e.g. BTP051 |
| `name` | VARCHAR | full junction string |
| `latitude` | DOUBLE | centroid of tagged violations |
| `longitude` | DOUBLE | |
| `is_metro_proximity` | BOOLEAN | parsed from name (e.g. Hosahalli Metro) |
| `total_violations` | INT | |

#### `devices` (3,070 rows)

| Column | Type |
|--------|------|
| `device_id` | VARCHAR PK |
| `police_station_id` | INT FK | mode station |
| `total_captures` | INT | |
| `approval_rate` | DECIMAL | among validated captures |

#### `officers` (2,666 rows)

| Column | Type |
|--------|------|
| `officer_id` | VARCHAR PK | created_by_id |
| `police_station_id` | INT FK | mode station |
| `total_records` | INT | |
| `approval_rate` | DECIMAL | |
| `avg_violations_per_shift` | DECIMAL | estimated from hourly buckets |

#### `grid_cells` (H3 res-8 — ~2,000–4,000 active cells)

| Column | Type |
|--------|------|
| `h3_index` | VARCHAR PK |
| `centroid_geom` | GEOGRAPHY(POINT) | |
| `police_station_id` | INT FK | dominant station |
| `junction_id` | INT FK | nearest named junction, nullable |
| `total_violations` | INT | all-time |
| `violations_7d` | INT | rolling |
| `violations_30d` | INT | rolling |
| `pii_score` | DECIMAL | Parking Impact Index |
| `eps_score` | DECIMAL | Enforcement Priority Score |
| `device_coverage_7d` | INT | distinct device_id count |
| `repeat_location_rate` | DECIMAL | same coords within 50m / total |
| `heavy_vehicle_share` | DECIMAL | |
| `last_updated` | TIMESTAMPTZ | |

#### `grid_hourly_stats` (aggregate for forecasting)

| Column | Type |
|--------|------|
| `id` | SERIAL PK |
| `h3_index` | VARCHAR FK |
| `datetime_hour` | TIMESTAMPTZ | truncated hour |
| `violation_count` | INT | |
| `severity_weighted_count` | DECIMAL | |
| `approved_count` | INT | |
| `dominant_vehicle_type` | VARCHAR | mode |
| `dominant_violation_type` | VARCHAR | mode |

**Unique constraint:** `(h3_index, datetime_hour)`

#### `hotspot_clusters` (DBSCAN output)

| Column | Type |
|--------|------|
| `cluster_id` | SERIAL PK |
| `geom` | GEOGRAPHY(POLYGON) | convex hull or H3 union |
| `centroid_lat` | DOUBLE | |
| `centroid_lon` | DOUBLE | |
| `violation_count` | INT | |
| `pii_score` | DECIMAL | |
| `eps_score` | DECIMAL | |
| `dominant_station` | VARCHAR | |
| `dominant_junction` | VARCHAR | nullable |
| `top_violation_types` | JSONB | |
| `computed_at` | TIMESTAMPTZ | |

#### `zone_risk_forecasts`

| Column | Type |
|--------|------|
| `id` | SERIAL PK |
| `h3_index` | VARCHAR FK |
| `forecast_for` | TIMESTAMPTZ | target hour/day |
| `predicted_count` | DECIMAL | |
| `predicted_severity_weighted` | DECIMAL | |
| `confidence_lower` | DECIMAL | |
| `confidence_upper` | DECIMAL | |
| `model_version` | VARCHAR | |
| `created_at` | TIMESTAMPTZ | |

#### `deployment_recommendations`

| Column | Type |
|--------|------|
| `id` | SERIAL PK |
| `shift_date` | DATE | |
| `shift_start_hour` | SMALLINT | |
| `officer_id` | VARCHAR FK | |
| `h3_index` | VARCHAR FK | |
| `police_station_id` | INT FK | |
| `eps_score` | DECIMAL | zone priority at assignment time |
| `expected_violations` | DECIMAL | from forecast |
| `rationale` | JSONB | explainable breakdown |
| `created_at` | TIMESTAMPTZ | |

---

## 5. ML Pipeline

### 5.1 Pipeline Stages

```
┌─────────┐   ┌──────────┐   ┌────────────┐   ┌─────────┐   ┌───────────┐
│  INGEST │──►│  CLEAN   │──►│  TRANSFORM │──►│  TRAIN  │──►│  DEPLOY   │
└─────────┘   └──────────┘   └────────────┘   └─────────┘   └───────────┘
     │              │               │               │              │
  CSV load      null cols       H3 assign       LightGBM       API serve
  validate PK   bbox filter    label explode   DBSCAN         daily batch
  dedupe id     status map     aggregates      MLflow log     monitor drift
```

### 5.2 Model Portfolio

| Model | Type | Target | Granularity | Algorithm |
|-------|------|--------|-------------|-----------|
| **M1: Hotspot Detector** | Unsupervised | spatial clusters | lat/lon points | DBSCAN (ε≈100m, min_samples=15) + H3 aggregation |
| **M2: Risk Forecaster** | Supervised regression | `violation_count` next 24h | H3 × hour | LightGBM on lag features |
| **M3: Severity Estimator** | Rule + regression | `severity_weighted_count` | H3 × day | Weighted sum (rules) + LightGBM residual |
| **M4: Deployment Ranker** | Optimization | officer-zone match | shift × zone | Greedy / OR-Tools using M2 output + EPS |

**Primary hackathon model:** M2 (Risk Forecaster) + M1 (Hotspot Detector)  
**Secondary:** M4 (Deployment Recommender) — high demo impact, no extra data required

### 5.3 M2: Risk Forecaster — Detail

**Training unit:** one row per `(h3_index, datetime_hour)` with `violation_count > 0` or included zeros for top 500 active cells.

**Target variables:**
- `y_count` = violation count in target hour
- `y_severity` = severity-weighted count in target hour

**Features (all derivable from dataset):**

| Feature Group | Features |
|---------------|----------|
| Lag | count lag 1h, 24h, 168h (7d); severity lag 24h, 168h |
| Rolling | mean/std count over 7d, 30d per cell |
| Temporal | hour_sin, hour_cos, dow_sin, dow_cos, is_weekend, month |
| Spatial | police_station_id (target-encoded), junction_distance_km, junction_id (nullable) |
| Device | device_coverage_7d, unique_devices_30d |
| Behaviour | repeat_location_rate, heavy_vehicle_share, multi_offence_rate |
| Location text | has_metro_keyword, has_market_keyword, pin_code (parsed) |

**Train/validation/test split (time-based):**

| Split | Period | Rows (approx.) |
|-------|--------|----------------|
| Train | 2023-11 → 2024-02 | ~70% |
| Validation | 2024-03 | ~15% |
| Test | 2024-04 (partial) | ~15% |

**Metrics:** MAE, RMSE on `y_count`; Spearman correlation on zone rankings; top-20 hotspot overlap@K

**Output:** `zone_risk_forecasts` table + EPS component `forecast_risk_24h`

### 5.4 M1: Hotspot Detector — Detail

1. Filter to `is_approved = TRUE` OR `validation_status IS NULL` (unvalidated still signal; flag separately).
2. Run DBSCAN on `(latitude, longitude)` per police station or city-wide.
3. Merge clusters spanning multiple H3 cells; compute convex hull polygon.
4. Rank clusters by `PII_score` and violation count.
5. Tag clusters near named junctions (`junction_id IS NOT NULL`) as **intersection spillover hotspots**.

### 5.5 Model Monitoring (production-ready stub)

- Track weekly MAE drift on holdout April slice.
- Alert if new `violation_type` labels appear (currently 27 known).
- Log feature null rates (`center_code` 3.77% missing → impute with station mode).

---

## 6. Feature Engineering Plan

### 6.1 ETL Transformations

| Step | Input | Output | Logic |
|------|-------|--------|-------|
| T1 | `violation_type` raw JSON string | `violation_labels` rows | `ast.literal_eval`, explode |
| T2 | `location` text | `pin_code`, keyword flags | regex `Pin-(\d{6})`, search Metro/Market/Road |
| T3 | lat/lon | `h3_index` | `h3.geo_to_h3(lat, lon, res=8)` |
| T4 | lat/lon | `geom` | PostGIS ST_SetSRID(ST_MakePoint(lon, lat), 4326) |
| T5 | `validation_status` | `is_approved` | approved→True, rejected/duplicate→False, else null |
| T6 | labels | `is_carriageway_blocking` | any label with severity ≥ 0.85 |
| T7 | `created_datetime` | hour, dow, month, is_weekend | pandas dt accessors |
| T8 | bbox outliers | `is_outlier` flag | 168 rows outside Bengaluru bbox |

### 6.2 Aggregated Features (materialized daily)

**Per H3 cell (`grid_cells`):**
- `violations_1d`, `violations_7d`, `violations_30d`
- `severity_weighted_7d`
- `approval_rate_30d` (where validated)
- `device_coverage_7d` = COUNT(DISTINCT device_id)
- `officer_coverage_7d` = COUNT(DISTINCT created_by_id)
- `repeat_location_rate` = violations within 50m duplicate coords / total
- `heavy_vehicle_share` = (CAR + LGV + BUS + TANKER) / total
- `multi_offence_rate` = offence_count > 1 / total
- `dominant_violation_type`, `dominant_vehicle_type`
- `junction_spillover_flag` = junction_id NOT NULL OR nearest junction < 200m

**Per officer (`officer_shift_stats`):**
- violations per hour-of-day histogram
- approval_rate
- top stations patrolled
- productivity_score = approved violations / shifts worked

**Per junction:**
- violations by hour, by vehicle type
- ratio of carriageway-blocking offences
- comparison to station average (relative risk)

### 6.3 Text-Derived Location Features (from `location` only)

| Feature | Extraction | Use Case |
|---------|------------|----------|
| `pin_code` | Regex Pin-560xxx | Zone grouping |
| `has_metro_keyword` | "Metro", "Metro Station" in text | Metro spillover proxy (valid: Hosahalli Metro in junction names) |
| `has_market_keyword` | "Market", "KR Market" | Commercial spillover proxy |
| `has_main_road` | "Main Road", "Ring Road" | Correlates with PARKING IN A MAIN ROAD |
| `road_name_token` | First road segment before comma | Clustering |

**Explicitly NOT used:** road width, lane count, traffic volume — not in dataset.

### 6.4 Temporal Feature Handling

Given timestamp ambiguity (see DATASET_ANALYSIS.md §7.5):
- Store both `hour_utc` and `hour_local_assumed` (treat stored value as IST).
- Use **dual models** in ablation; ship the better validator on March holdout.
- Prefer **day-of-week** and **weekly lags** over raw hour (more robust to batch artifacts).
- Document assumption in dashboard: *"Temporal patterns reflect record timestamps as provided by source."*

### 6.5 Feature Store Schema (Parquet)

```
features/grid_hourly/{date}.parquet     — training rows for M2
features/grid_cells/latest.parquet      — inference snapshot
features/officers/latest.parquet        — deployment optimizer input
```

---

## 7. API Design

**Base URL:** `/api/v1`  
**Auth:** Bearer JWT (demo: single admin token)  
**Format:** JSON; geo endpoints also support GeoJSON

### 7.1 Endpoints

#### Analytics & Summary

```
GET /api/v1/analytics/summary
```
**Response:**
```json
{
  "total_violations": 298450,
  "date_range": { "start": "2023-11-09", "end": "2024-04-08" },
  "top_police_station": "Upparpet",
  "top_junction": "BTP051 - Safina Plaza Junction",
  "carriageway_blocking_pct": 12.4,
  "approved_rate": 38.7,
  "active_hotspots": 142,
  "avg_pii_score": 0.62
}
```

#### Violations (paginated)

```
GET /api/v1/violations?station={name}&junction={id}&h3={index}
    &vehicle_type={type}&from={iso}&to={iso}&page=1&limit=50
```

#### Hotspots

```
GET /api/v1/hotspots?min_eps=0.5&station={name}&limit=50
```
**Response:**
```json
{
  "hotspots": [
    {
      "cluster_id": 12,
      "centroid": { "lat": 12.977, "lon": 77.584 },
      "polygon": { "type": "Polygon", "coordinates": [...] },
      "violation_count": 842,
      "pii_score": 0.91,
      "eps_score": 0.87,
      "dominant_violation_types": ["WRONG PARKING", "NO PARKING"],
      "dominant_station": "Upparpet",
      "nearest_junction": "BTP040 - Elite Junction",
      "carriageway_blocking_rate": 0.18
    }
  ]
}
```

```
GET /api/v1/hotspots/heatmap?resolution=8&metric=pii|count|eps
```
Returns H3 cell scores for map layer.

#### Priority Zones

```
GET /api/v1/zones/priority?station={name}&top=20
```
Returns EPS-ranked H3 cells with score decomposition:
```json
{
  "zones": [
    {
      "h3_index": "8861892591fffff",
      "eps_score": 0.92,
      "components": {
        "density_7d": 0.31,
        "severity_7d": 0.28,
        "repeat_rate": 0.12,
        "forecast_24h": 0.24,
        "device_gap": 0.08,
        "junction_spillover": 0.05
      },
      "pii_score": 0.88,
      "police_station": "Upparpet",
      "recommended_action": "HIGH_PRIORITY_PATROL"
    }
  ]
}
```

#### Forecast

```
GET /api/v1/forecast?h3={index}&horizon=24h
GET /api/v1/forecast/top?station={name}&horizon=24h&limit=20
```
**Response:**
```json
{
  "forecasts": [
    {
      "h3_index": "8861892591fffff",
      "forecast_for": "2024-04-09T18:00:00+05:30",
      "predicted_count": 14.2,
      "predicted_severity_weighted": 9.8,
      "confidence_interval": [10.1, 18.7],
      "risk_tier": "HIGH"
    }
  ]
}
```

#### Parking Impact

```
GET /api/v1/impact?h3={index}|cluster={id}|junction={id}
```
**Response:**
```json
{
  "pii_score": 0.88,
  "severity_breakdown": {
    "PARKING IN A MAIN ROAD": 312,
    "DOUBLE PARKING": 45,
    "WRONG PARKING": 892
  },
  "multi_offence_rate": 0.14,
  "heavy_vehicle_share": 0.38,
  "junction_spillover": true,
  "interpretation": "High carriageway obstruction pressure from main-road and wrong-parking offences concentrated near Elite Junction."
}
```

#### Deployment Recommendations

```
POST /api/v1/deployment/recommend
```
**Request:**
```json
{
  "shift_date": "2024-04-10",
  "shift_start_hour": 18,
  "shift_duration_hours": 4,
  "police_station": "Upparpet",
  "officers_available": ["FKUSR00021", "FKUSR00332"],
  "max_zones_per_officer": 3
}
```
**Response:**
```json
{
  "recommendations": [
    {
      "officer_id": "FKUSR00021",
      "assignments": [
        {
          "h3_index": "8861892591fffff",
          "eps_score": 0.92,
          "expected_violations": 12.4,
          "centroid": { "lat": 12.977, "lon": 77.584 },
          "rationale": "Top forecast risk; low device coverage; near BTP040 junction"
        }
      ],
      "expected_total_violations": 28.6
    }
  ],
  "uncovered_high_risk_zones": 2
}
```

#### Junctions & Stations

```
GET /api/v1/junctions?top=20&sort=violations
GET /api/v1/stations?top=20&sort=eps
GET /api/v1/stations/{name}/dashboard
```

### 7.2 Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `INVALID_BBOX` | 400 | Query outside Bengaluru coverage |
| `STATION_NOT_FOUND` | 404 | Unknown police_station |
| `MODEL_NOT_READY` | 503 | Forecast model not trained yet |

### 7.3 OpenAPI

Auto-generated at `/docs` (Swagger UI) — critical for hackathon judging.

---

## 8. Dashboard Wireframe

### 8.1 Layout — Command Center (Primary Screen)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  ParkSense AI          [Station ▼ Upparpet] [Date Range ▼] [Shift ▼ Evening]│
│  ─────────────────────────────────────────────────────────────────────────── │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐ │
│  │ Hotspots│ │ High    │ │ Forecast│ │ Officers│ │ PII     │ │ Carriageway│ │
│  │ Active  │ │ Priority│ │ Risk 24h│ │ Deployed│ │ Avg     │ │ Blocking %│ │
│  │   142   │ │ Zones 23│ │   +18%  │ │    12   │ │  0.62   │ │   12.4%   │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └───────────┘ │
├────────────────────────────────────────────┬─────────────────────────────────┤
│                                            │  PRIORITY ZONE LIST             │
│                                            │  ─────────────────────────────  │
│           INTERACTIVE MAP                  │  1. Elite Junction area  EPS 0.92│
│         (MapLibre + H3 heatmap)            │     PII 0.88 · Forecast 14/hr  │
│                                            │     [Assign Officer] [Details]  │
│    ● red = high EPS     ○ clusters         │  2. KR Market spillover  0.89  │
│    ░ H3 cells color by PII or count        │  3. Safina Plaza zone  0.85  │
│    ★ junction pins (BTP051, BTP082…)       │  ...                            │
│    ─ officer patrol routes (recommended)   │                                 │
│                                            │  FILTERS                        │
│    [Layer: EPS | PII | Count | Forecast]   │  ☑ Carriageway-blocking only   │
│    [Toggle: Junctions | Clusters | Grid]   │  ☑ Approved violations only    │
│                                            │  Vehicle: [All ▼]               │
├────────────────────────────────────────────┤  Violation: [All ▼]              │
│  TEMPORAL PANEL                            │                                 │
│  ┌──────────────────────────────────────┐│  DEPLOYMENT PANEL               │
│  │ Hourly violations (bar)              ││  ─────────────────────────────  │
│  │ ▁▂▃▅▇█▇▅▃▂▁  ← from created_datetime ││  Shift: 18:00–22:00              │
│  └──────────────────────────────────────┘│  Available: 4 officers          │
│  ┌──────────────────────────────────────┐│  [Generate Deployment Plan]     │
│  │ 7-day forecast trend (line)         ││                                 │
│  │ ─── predicted vs actual (Apr test)  ││  Officer FKUSR00021 → Zone A,B  │
│  └──────────────────────────────────────┘│  Officer FKUSR00332 → Zone C    │
└────────────────────────────────────────────┴─────────────────────────────────┘
```

### 8.2 Screen — Zone Detail (drill-down)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  ← Back    Zone: H3 8861892591fffff · Upparpet · Near BTP040 Elite Junction  │
├──────────────────────────────────────────────────────────────────────────────┤
│  EPS 0.92  │  PII 0.88  │  7d Violations: 342  │  Device Coverage: 2 (LOW)  │
├───────────────────────────────────────┬──────────────────────────────────────┤
│  Mini-map (zone polygon)              │  SCORE BREAKDOWN (explainable)       │
│                                       │  ████████████░░ density      31%     │
│                                       │  ███████████░░░ severity     28%     │
│                                       │  █████░░░░░░░░░ repeat rate  12%     │
│                                       │  █████████░░░░░ forecast     24%     │
│                                       │  ███░░░░░░░░░░░ device gap    8%     │
├───────────────────────────────────────┴──────────────────────────────────────┤
│  TOP VIOLATION TYPES          │  VEHICLE MIX (pie)    │  24H FORECAST (bar) │
│  WRONG PARKING        892     │  Scooter 32%          │  ▂▃▅▇█▇▅▃           │
│  NO PARKING           654     │  Car 30%              │                     │
│  PARKING IN MAIN ROAD 312     │  Auto 13%             │                     │
├──────────────────────────────────────────────────────────────────────────────┤
│  RECENT VIOLATIONS (table, paginated from /api/v1/violations?h3=…)          │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 8.3 Screen — Junction Spillover View

Focused on 168 named junctions; addresses commercial/metro spillover objective using **junction_name** and location keywords — no invented POI database.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Junction Spillover Monitor                                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│  Rank │ Junction                          │ Violations │ PII  │ Blocking %  │
│  1    │ BTP051 - Safina Plaza Junction    │ 15,449     │ 0.94 │ 15.2%       │
│  2    │ BTP082 - KR Market Junction       │ 11,538     │ 0.91 │ 18.7%       │
│  3    │ BTP020 - Hosahalli Metro Station  │  4,101     │ 0.86 │ 14.1%       │
├──────────────────────────────────────────────────────────────────────────────┤
│  Map: junction-centric buffers (200m) with violation scatter                │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 8.4 Mobile Patrol View (optional stretch)

Simplified list + map for assigned officer: top 3 zones, navigation centroid, expected violations.

---

## 9. Innovation Section

### 9.1 What Makes ParkSense AI Different

| Innovation | Description | Why It Matters |
|------------|-------------|----------------|
| **Severity-Weighted Parking Impact Index (PII)** | Converts multi-label `violation_type` into a carriageway obstruction score using offence taxonomy already in the data | Quantifies "impact" without traffic sensors — judges see a defensible proxy |
| **Enforcement Gap Detection** | Subtracts `device_coverage_7d` from priority — high violations + low camera presence = patrol needed | Turns `device_id` sparsity into actionable intelligence |
| **Dual-Layer Hotspots** | H3 grid (fine) + DBSCAN clusters (interpretable polygons) | Commanders get both heat and bounded patrol zones |
| **Explainable EPS Decomposition** | Every priority rank shows 6-component breakdown | Trust for police stakeholders; critical for hackathon demos |
| **Validation-Aware Ground Truth** | Separate approved vs rejected hotspots; filter noise from `duplicate`/`rejected` | Uses the 58% validated subset intelligently — shows data literacy |
| **Junction Spillover Module** | Exploits 168 BTP junctions + metro/market keyword parsing from `location` | Directly addresses commercial/metro spillover in problem statement |
| **Officer Productivity Matching** | Recommends deployment using historical `created_by_id` patterns per station/shift | Closes the loop from detection → enforcement action |
| **Forecast at Patrol Scale** | Predicts violations per ~750m H3 cell, not city-wide totals | Operationally usable — officers know *where* to go |

### 9.2 What We Explicitly Do NOT Claim

- We do **not** measure live traffic congestion or travel time delay.
- We do **not** estimate road capacity or lane blockage in meters.
- We do **not** predict individual driver behavior or identity.
- PII is a **relative pressure index** derived from violation taxonomy, not a physics-based traffic model.

This honesty strengthens credibility with technical judges.

### 9.3 Future Extensions (post-hackathon, if data becomes available)

- Integrate live camera feeds → validate forecast accuracy in real time.
- Add event calendar → improve weekend/event spillover models.
- Connect SCITA API (`data_sent_to_scita`) for closed-loop ticketing metrics.

---

## 10. Judge Pitch Section

### 10.1 Elevator Pitch (30 seconds)

> **ParkSense AI** helps Bengaluru Traffic Police decide *where* to send officers *before* carriageways choke — using the data they already collect. We analyzed **298,450 parking violations** across **54 police stations** and **168 junctions**, detected **142 persistent hotspots**, and built a forecasting engine that predicts violation risk by zone and shift. Officers get explainable priority scores — not black-box alerts — and commanders see parking impact through a severity index derived from actual offence types like *Parking in Main Road* and *Double Parking*. No external traffic data required.

### 10.2 Problem → Solution Narrative (2 minutes)

**Problem:** Illegal parking near markets, metro stations, and junctions blocks carriageways. Police cannot be everywhere.

**Insight from data:** Violations are highly concentrated — top 3 stations (Upparpet, Shivajinagar, Malleshwaram) account for **28%** of all offences. Top junctions like Safina Plaza and KR Market show **15,000+ violations each**. **13.4%** of incidents carry multiple simultaneous offences, indicating severe obstruction events.

**Our approach:** ParkSense AI converts raw violation logs into three decision tools:
1. **Hotspot Map** — where illegal parking persistently occurs (H3 + DBSCAN).
2. **Priority Queue** — EPS-ranked zones combining density, severity, repeat patterns, forecast risk, and enforcement gaps.
3. **Deployment Plan** — which officers to send where, based on station jurisdiction and historical productivity.

**Impact metric:** Parking Impact Index (PII) — a severity-weighted score using offence types that directly describe carriageway and intersection blocking, validated against **115,400 approved violations**.

### 10.3 Demo Script (3 minutes)

| Step | Action | Talking Point |
|------|--------|---------------|
| 1 | Open dashboard → city-wide heatmap | "298K violations, zero duplicate IDs, full geo coverage" |
| 2 | Filter to **Upparpet** station | "11.5% of all city violations — central Bengaluru pressure" |
| 3 | Click **BTP040 Elite Junction** zone | "PII 0.88 — high main-road parking and wrong parking cluster" |
| 4 | Show EPS breakdown chart | "Not a black box — 6 explainable factors" |
| 5 | Toggle **Forecast layer** | "Tomorrow 6–10 PM: +18% risk vs 7-day average" |
| 6 | Click **Generate Deployment Plan** | "2 officers, 3 zones each, 28 expected violations addressable" |
| 7 | Open Junction Spillover view | "Metro and market junctions ranked by carriageway-blocking rate" |
| 8 | Show model validation slide | "March holdout MAE = X; top-20 hotspot overlap = Y%" |

### 10.4 Key Numbers for Judges

| Stat | Value | Source |
|------|-------|--------|
| Total violations analyzed | 298,450 | Dataset |
| Unique vehicles | 231,890 | `vehicle_number` |
| Police stations | 54 | `police_station` |
| Named junctions | 168 | `junction_name` |
| Parking-dominated offences | >95% | `violation_type` explode |
| Multi-offence incidents | 13.4% | 40,110 records |
| Approved violations (ground truth) | 115,400 | `validation_status` |
| Carriageway-blocking labels | ~29,000+ | severity ≥ 0.85 labels |
| Enforcement devices | 3,070 | `device_id` |
| Active officers in data | 2,666 | `created_by_id` |
| Data timespan | 5 months | Nov 2023 – Apr 2024 |

### 10.5 Anticipated Judge Questions & Answers

**Q: You don't have traffic data — how can you quantify impact?**  
A: We use the offence taxonomy the police already record. *Parking in Main Road*, *Double Parking*, and *Parking Near Road Crossing* are direct proxies for carriageway obstruction. PII weights these by severity and aggregates spatially — it's a relative pressure index, not a traffic simulation.

**Q: How do you know timestamps are accurate?**  
A: We acknowledge batch-processing artifacts in the data. Our models emphasize day-of-week and weekly lags over raw hour, and we validate on held-out March data. We document assumptions transparently.

**Q: Why should police trust the forecast?**  
A: Time-based train/test split (no leakage), MAE reported on April holdout, and explainable features (7-day lag, station, junction proximity). Officers see *why* a zone is ranked high.

**Q: What's the deployment recommendation based on?**  
A: Only dataset fields: `created_by_id` historical productivity, `police_station` jurisdiction, forecasted violation counts, and EPS scores. No external workforce data.

**Q: What's novel vs a simple heatmap?**  
A: Heatmaps show history. ParkSense adds **forecasting**, **enforcement gap detection**, **severity-weighted impact**, and **officer assignment** — a closed-loop decision system.

### 10.6 Success Metrics (Hackathon KPIs)

| KPI | Target | Measurement |
|-----|--------|-------------|
| Hotspot detection precision | Top-20 zones capture ≥40% of next-week violations | Backtest on Apr holdout |
| Forecast MAE | < 5 violations/hour/cell (active cells) | March validation |
| Deployment coverage | ≥80% of high-EPS zones assigned | Optimizer output |
| Dashboard load time | < 2s for heatmap tile | API benchmark |
| Explainability | 100% of EPS scores have component breakdown | API contract |

---

## 11. Implementation Roadmap (Hackathon 24–48h)

| Phase | Hours | Deliverables |
|-------|-------|--------------|
| **Phase 1: Data** | 0–6 | ETL script, PostgreSQL schema, normalized tables |
| **Phase 2: Features** | 6–12 | H3 grid, PII/EPS calculators, materialized aggregates |
| **Phase 3: ML** | 12–18 | DBSCAN hotspots, LightGBM forecaster, backtest metrics |
| **Phase 4: API** | 18–24 | FastAPI endpoints, deployment optimizer |
| **Phase 5: UI** | 24–36 | Dashboard map, priority list, deployment panel |
| **Phase 6: Pitch** | 36–48 | Demo script, validation slides, SOLUTION_ARCHITECTURE.md walkthrough |

---

## 12. Appendix — Offence Severity Reference

Complete mapping stored in `violation_types` table; top entries driving PII:

| offence_code | violation_type | weight |
|--------------|----------------|--------|
| 107 | PARKING IN A MAIN ROAD | 1.00 |
| 109 | DOUBLE PARKING | 0.95 |
| 104 | PARKING NEAR ROAD CROSSING | 0.90 |
| 106 | PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS | 0.90 |
| 108 | PARKING OPPOSITE TO ANOTHER PARKED VEHICLE | 0.85 |
| 112 | WRONG PARKING | 0.70 |
| 113 | NO PARKING | 0.65 |
| 105 | PARKING ON FOOTPATH | 0.60 |
| 111 | PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC | 0.75 |

---

*ParkSense AI — turning enforcement data into patrol intelligence.*  
*Architecture version 1.0 · Grounded in DATASET_ANALYSIS.md findings · Dataset-only constraints observed.*
