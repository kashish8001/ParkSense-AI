"use client";

import { HourlyChart, ViolationTypesChart, WeekdayChart } from "@/components/dashboard/charts";
import type { AnalyticsSummary } from "@/lib/api";

export function ChartsSection({ summary }: { summary: AnalyticsSummary }) {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <HourlyChart data={summary.hourly_distribution} />
      <WeekdayChart data={summary.weekday_distribution} />
      <ViolationTypesChart data={summary.top_violation_types} />
    </div>
  );
}
