"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalyticsSummary } from "@/lib/api";

export function KpiCards({ summary }: { summary: AnalyticsSummary }) {
  const items = [
    { label: "Total Violations", value: summary.total_violations.toLocaleString() },
    { label: "Active Hotspots", value: summary.active_hotspots.toLocaleString() },
    { label: "Avg PII Score", value: summary.avg_pii_score.toFixed(2) },
    { label: "Avg EPS Score", value: summary.avg_eps_score.toFixed(2) },
    { label: "Carriageway Blocking", value: `${summary.carriageway_blocking_pct}%` },
    { label: "Approved Rate", value: `${summary.approved_rate}%` },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      {items.map((item) => (
        <Card key={item.label}>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">{item.label}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{item.value}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
