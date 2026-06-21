# ParkSense AI

Parking enforcement intelligence platform for Bengaluru, built from 298K+ anonymized police violation records.

## Project Structure

```
parksense ai/
├── backend/          FastAPI + ML pipeline (Pandas, scikit-learn, LightGBM)
├── frontend/         Next.js dashboard (React Leaflet, Recharts, shadcn/ui)
├── data/             Source CSV dataset
├── DATASET_ANALYSIS.md
└── SOLUTION_ARCHITECTURE.md
```

## Features

1. CSV dataset ingestion and processing pipeline
2. Violation analytics dashboard
3. Interactive hotspot heatmap (H3 hex grid + DBSCAN clusters)
4. Parking Impact Index (PII) engine
5. Enforcement Priority Score (EPS) and zone ranking
6. LightGBM violation forecasting
7. Officer deployment recommendations
8. Patrol impact simulation dashboard
9. CSV / GeoJSON / JSON report exports

## Quick Start

### 1. Backend

```bash
# Create and activate virtual environment
cd backend
python -m venv venv

# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate

# Install dependencies and run
pip install -r requirements.txt
python run_pipeline.py
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: http://localhost:3000

Set `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1` if the API runs elsewhere.

## Pipeline Output

After running `run_pipeline.py`, artifacts are stored in `backend/storage/`:

- `violations.parquet`
- `grid_cells.parquet`
- `hourly_features.parquet`
- `forecast_model.joblib`
- `clusters.json`

## API Highlights

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/ingest/run-pipeline` | Reprocess dataset |
| `GET /api/v1/analytics/summary` | Dashboard KPIs |
| `GET /api/v1/hotspots/heatmap` | GeoJSON heatmap |
| `GET /api/v1/zones/priority` | EPS-ranked zones |
| `GET /api/v1/forecast/top` | Forecasted risk zones |
| `POST /api/v1/deployment/recommend` | Officer deployment plan |
| `POST /api/v1/simulation/run` | Patrol what-if simulation |
| `GET /api/v1/export/priority.csv` | Export priority zones |

## Notes

- All metrics are derived only from fields in the violation dataset.
- Parking impact is measured via severity-weighted offence types, not external traffic sensors.
- First API startup auto-runs the pipeline if storage artifacts are missing (~2 min for 298K rows).
