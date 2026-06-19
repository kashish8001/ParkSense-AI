const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${path}`);
  }
  return response.json() as Promise<T>;
}

export type AnalyticsSummary = {
  total_violations: number;
  date_range: { start: string; end: string };
  top_police_station: string;
  top_junction: string;
  carriageway_blocking_pct: number;
  approved_rate: number;
  active_hotspots: number;
  avg_pii_score: number;
  avg_eps_score: number;
  top_violation_types: { label: string; count: number }[];
  top_vehicle_types: { label: string; count: number }[];
  hourly_distribution: Record<string, number>;
  weekday_distribution: Record<string, number>;
  station_counts: { station: string; count: number }[];
};

export type PriorityZone = {
  h3_index: string;
  centroid: { lat: number; lon: number };
  eps_score: number;
  pii_score: number;
  components: Record<string, number>;
  police_station: string;
  violations_7d: number;
  predicted_count: number;
  recommended_action: string;
};

export type HotspotCluster = {
  cluster_id: number;
  centroid: { lat: number; lon: number };
  violation_count: number;
  pii_score: number;
  eps_score: number;
  dominant_station: string;
  dominant_junction: string;
  carriageway_blocking_rate: number;
  top_violation_types: string[];
};

export type HeatmapGeoJSON = {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    properties: {
      h3_index: string;
      value: number;
      violations_7d: number;
      pii_score: number;
      eps_score: number;
      police_station: string;
    };
    geometry: { type: "Polygon"; coordinates: number[][][] };
  }>;
};

export const api = {
  health: () => fetchJson<{ status: string; ready: boolean; records: number }>("/health"),
  summary: () => fetchJson<AnalyticsSummary>("/analytics/summary"),
  heatmap: (metric = "eps", station?: string) =>
    fetchJson<HeatmapGeoJSON>(
      `/hotspots/heatmap?metric=${metric}${station ? `&station=${encodeURIComponent(station)}` : ""}`,
    ),
  hotspots: (station?: string) =>
    fetchJson<{ hotspots: HotspotCluster[] }>(
      `/hotspots${station ? `?station=${encodeURIComponent(station)}` : ""}`,
    ),
  priorityZones: (station?: string, top = 20) =>
    fetchJson<{ zones: PriorityZone[] }>(
      `/zones/priority?top=${top}${station ? `&station=${encodeURIComponent(station)}` : ""}`,
    ),
  forecastTop: (station?: string) =>
    fetchJson<{ forecasts: Array<Record<string, unknown>>; metrics: Record<string, number> }>(
      `/forecast/top${station ? `?station=${encodeURIComponent(station)}` : ""}`,
    ),
  deploymentRecommend: (payload: {
    police_station: string;
    officers_available: string[];
    shift_start_hour: number;
    max_zones_per_officer: number;
  }) =>
    fetchJson<Record<string, unknown>>("/deployment/recommend", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  simulation: (payload: {
    police_station?: string | null;
    officer_count: number;
    patrol_hours: number;
    target_eps_threshold: number;
  }) =>
    fetchJson<Record<string, unknown>>("/simulation/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  stations: () => fetchJson<{ stations: Array<{ police_station: string; total_violations: number }> }>("/stations"),
  runPipeline: () => fetchJson<Record<string, unknown>>("/ingest/run-pipeline", { method: "POST" }),
  exportSummaryUrl: () => `${API_BASE}/export/summary`,
  exportCsvUrl: () => `${API_BASE}/export/priority.csv`,
  exportGeoJsonUrl: () => `${API_BASE}/export/heatmap.geojson`,
};
