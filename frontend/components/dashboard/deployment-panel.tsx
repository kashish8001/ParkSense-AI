"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

export function DeploymentPanel({ station }: { station: string }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);

  async function generatePlan() {
    setLoading(true);
    try {
      const response = await api.deploymentRecommend({
        police_station: station,
        officers_available: ["FKUSR00021", "FKUSR00332"],
        shift_start_hour: 18,
        max_zones_per_officer: 3,
      });
      setResult(response);
    } finally {
      setLoading(false);
    }
  }

  const recommendations = (result?.recommendations as Array<Record<string, unknown>>) ?? [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Officer Deployment Recommendations</CardTitle>
        <Button onClick={generatePlan} disabled={loading}>
          {loading ? "Generating…" : "Generate Plan"}
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {!result && <p className="text-sm text-muted-foreground">Generate a shift plan for {station}.</p>}
        {recommendations.map((rec) => (
          <div key={String(rec.officer_id)} className="rounded-md border border-border p-3">
            <div className="mb-2 font-medium">Officer {String(rec.officer_id)}</div>
            <div className="text-sm text-muted-foreground">
              Expected violations addressable: {String(rec.expected_total_violations)}
            </div>
            <ul className="mt-2 space-y-1 text-xs">
              {((rec.assignments as Array<Record<string, unknown>>) ?? []).map((assignment) => (
                <li key={String(assignment.h3_index)}>
                  Zone {String(assignment.h3_index).slice(-6)} · EPS {String(assignment.eps_score)} ·{" "}
                  {String(assignment.rationale)}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
