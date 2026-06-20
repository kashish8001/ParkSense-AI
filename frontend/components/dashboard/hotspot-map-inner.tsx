"use client";

import { useMemo } from "react";
import { CircleMarker, GeoJSON, MapContainer, Popup, TileLayer } from "react-leaflet";
import type { HeatmapGeoJSON, HotspotCluster } from "@/lib/api";

function colorForValue(value: number, max: number) {
  const ratio = max > 0 ? value / max : 0;
  if (ratio > 0.75) return "#ef4444";
  if (ratio > 0.5) return "#f97316";
  if (ratio > 0.25) return "#eab308";
  return "#22c55e";
}

export default function HotspotMapInner({
  heatmap,
  clusters,
  metric,
}: {
  heatmap: HeatmapGeoJSON;
  clusters: HotspotCluster[];
  metric: string;
}) {
  const styled = useMemo(() => {
    const max = Math.max(...heatmap.features.map((feature) => feature.properties.value), 1);
    return {
      type: "FeatureCollection" as const,
      features: heatmap.features.map((feature) => ({
        ...feature,
        properties: {
          ...feature.properties,
          fillColor: colorForValue(feature.properties.value, max),
        },
      })),
    };
  }, [heatmap]);

  return (
    <MapContainer center={[12.981, 77.601]} zoom={12} className="h-full min-h-[420px] rounded-lg">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <GeoJSON
        data={styled}
        style={(feature) => ({
          color: feature?.properties?.fillColor ?? "#0ea5e9",
          weight: 1,
          fillColor: feature?.properties?.fillColor ?? "#0ea5e9",
          fillOpacity: 0.45,
        })}
        onEachFeature={(feature, layer) => {
          const props = feature.properties as HeatmapGeoJSON["features"][0]["properties"] & { fillColor?: string };
          layer.bindPopup(
            `<strong>${metric.toUpperCase()}:</strong> ${props.value.toFixed(3)}<br/>
             <strong>Station:</strong> ${props.police_station}<br/>
             <strong>7d violations:</strong> ${props.violations_7d}`,
          );
        }}
      />
      {clusters.map((cluster) => (
        <CircleMarker
          key={cluster.cluster_id}
          center={[cluster.centroid.lat, cluster.centroid.lon]}
          radius={10}
          pathOptions={{ color: "#38bdf8", fillColor: "#0284c7", fillOpacity: 0.9 }}
        >
          <Popup>
            <div className="text-xs space-y-1 font-sans text-foreground">
              <strong className="text-sm font-semibold">Cluster #{cluster.cluster_id}</strong>
              <br />
              <strong>Location:</strong> {cluster.location_desc}
              <br />
              <strong>EPS:</strong> {cluster.eps_score.toFixed(2)}
              <br />
              <strong>Violations (7d):</strong> {cluster.violation_count}
              <br />
              <strong>Junction:</strong> {cluster.dominant_junction}
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
