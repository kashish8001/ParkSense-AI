"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { PriorityZone } from "@/lib/api";

export function PriorityZones({ zones }: { zones: PriorityZone[] }) {
  return (
    <Card className="h-[260px] flex flex-col">
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-sm font-semibold">Priority Enforcement Zones</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto px-4 pb-3 pt-0 space-y-2 max-h-[200px]">
        {zones.map((zone, index) => (
          <div key={zone.h3_index} className="rounded-md border border-border bg-secondary/40 p-3">
            <div className="mb-2 flex items-center justify-between gap-2">
              <div className="font-medium">
                {index + 1}. {zone.police_station}
              </div>
              <Badge className="bg-primary/20 text-primary">EPS {zone.eps_score.toFixed(2)}</Badge>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
              <span>PII: {zone.pii_score.toFixed(2)}</span>
              <span>7d: {zone.violations_7d}</span>
              <span>Forecast: {zone.predicted_count.toFixed(1)}</span>
              <span>{zone.recommended_action.replaceAll("_", " ")}</span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
