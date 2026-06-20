"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { HotspotCluster } from "@/lib/api";

export function HotspotsList({ hotspots }: { hotspots: HotspotCluster[] }) {
  const top10 = hotspots.slice(0, 10);

  return (
    <Card className="h-[260px] flex flex-col">
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <span className="text-red-500">🚨</span> Top 10 Critical Hotspots
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto px-4 pb-3 pt-0 space-y-2 max-h-[200px]">
        {top10.length === 0 ? (
          <div className="py-8 text-center text-sm text-muted-foreground">
            No hotspots detected. Run the pipeline or adjust filters.
          </div>
        ) : (
          top10.map((hotspot, index) => (
            <div
              key={hotspot.cluster_id}
              className="rounded-md border border-border bg-secondary/20 hover:bg-secondary/40 transition-colors p-2.5 flex items-start justify-between gap-3 border-l-4 border-l-red-500"
            >
              <div className="space-y-0.5 min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-bold text-red-500">
                    #{index + 1}
                  </span>
                  <span className="text-xs font-semibold text-foreground truncate">
                    {hotspot.dominant_station} Area
                  </span>
                </div>
                <p className="text-[11px] text-muted-foreground leading-normal break-words">
                  <strong className="text-foreground/75 font-medium">Location:</strong> {hotspot.location_desc}
                </p>
                <div className="text-[9px] text-muted-foreground/60 truncate">
                  Junction: {hotspot.dominant_junction}
                </div>
              </div>
              <div className="text-right flex flex-col items-end gap-1 flex-shrink-0">
                <Badge className="bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20 text-[9px] font-semibold py-0 px-1.5">
                  {hotspot.violation_count} Violations
                </Badge>
                <span className="text-[9px] text-muted-foreground font-medium">
                  EPS: {hotspot.eps_score.toFixed(2)}
                </span>
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
