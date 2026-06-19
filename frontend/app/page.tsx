"use client";

import { useEffect, useState } from "react";
import { ChartsSection } from "@/components/dashboard/dashboard-client";
import { DeploymentPanel } from "@/components/dashboard/deployment-panel";
import { ExportPanel } from "@/components/dashboard/export-panel";
import { HotspotMap } from "@/components/dashboard/hotspot-map";
import { KpiCards } from "@/components/dashboard/kpi-cards";
import { PriorityZones } from "@/components/dashboard/priority-zones";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, type AnalyticsSummary, type HeatmapGeoJSON, type HotspotCluster, type PriorityZone } from "@/lib/api";

export default function DashboardPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapGeoJSON | null>(null);
  const [clusters, setClusters] = useState<HotspotCluster[]>([]);
  const [zones, setZones] = useState<PriorityZone[]>([]);
  const [stations, setStations] = useState<string[]>([]);
  const [station, setStation] = useState<string>("all");
  const [metric, setMetric] = useState<string>("eps");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadDashboard(selectedStation?: string) {
    setLoading(true);
    setError(null);
    try {
      const stationFilter = selectedStation && selectedStation !== "all" ? selectedStation : undefined;
      const [summaryRes, heatmapRes, hotspotRes, zonesRes, stationsRes] = await Promise.all([
        api.summary(),
        api.heatmap(metric, stationFilter),
        api.hotspots(stationFilter),
        api.priorityZones(stationFilter, 15),
        api.stations(),
      ]);
      setSummary(summaryRes);
      setHeatmap(heatmapRes);
      setClusters(hotspotRes.hotspots);
      setZones(zonesRes.zones);
      setStations(stationsRes.stations.map((item) => item.police_station));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard(station);
  }, [station, metric]);

  if (loading && !summary) {
    return <div className="py-20 text-center text-muted-foreground">Loading ParkSense AI dashboard…</div>;
  }

  if (error || !summary || !heatmap) {
    return (
      <div className="space-y-4 py-20 text-center">
        <p className="text-red-400">{error ?? "Dashboard unavailable"}</p>
        <Button onClick={() => loadDashboard(station)}>Retry</Button>
      </div>
    );
  }

  const activeStation = station === "all" ? summary.top_police_station : station;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Select value={station} onValueChange={setStation}>
          <SelectTrigger className="w-[220px]">
            <SelectValue placeholder="Police station" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Stations</SelectItem>
            {stations.map((name) => (
              <SelectItem key={name} value={name}>
                {name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={metric} onValueChange={setMetric}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Heatmap metric" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="eps">EPS Score</SelectItem>
            <SelectItem value="pii">PII Score</SelectItem>
            <SelectItem value="count">7d Violations</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" onClick={() => loadDashboard(station)}>
          Refresh
        </Button>
      </div>

      <KpiCards summary={summary} />

      <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        <div className="overflow-hidden rounded-lg border border-border">
          <HotspotMap heatmap={heatmap} clusters={clusters} metric={metric} />
        </div>
        <PriorityZones zones={zones} />
      </div>

      <ChartsSection summary={summary} />

      <Tabs defaultValue="deployment">
        <TabsList>
          <TabsTrigger value="deployment">Deployment</TabsTrigger>
          <TabsTrigger value="export">Export</TabsTrigger>
        </TabsList>
        <TabsContent value="deployment">
          <DeploymentPanel station={activeStation} />
        </TabsContent>
        <TabsContent value="export">
          <ExportPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}
