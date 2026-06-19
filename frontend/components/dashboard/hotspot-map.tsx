"use client";

import dynamic from "next/dynamic";
import type { HeatmapGeoJSON, HotspotCluster } from "@/lib/api";

const MapInner = dynamic(() => import("./hotspot-map-inner"), {
  ssr: false,
  loading: () => <div className="flex h-full items-center justify-center text-sm text-muted-foreground">Loading map…</div>,
});

export function HotspotMap({
  heatmap,
  clusters,
  metric,
}: {
  heatmap: HeatmapGeoJSON;
  clusters: HotspotCluster[];
  metric: string;
}) {
  return <MapInner heatmap={heatmap} clusters={clusters} metric={metric} />;
}
