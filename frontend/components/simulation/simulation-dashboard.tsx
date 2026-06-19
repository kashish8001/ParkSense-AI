"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";

export function SimulationDashboard() {
  const [station, setStation] = useState<string>("Upparpet");
  const [officerCount, setOfficerCount] = useState(4);
  const [patrolHours, setPatrolHours] = useState(4);
  const [threshold, setThreshold] = useState(0.6);
  const [stations, setStations] = useState<string[]>([]);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.stations().then((response) => {
      const names = response.stations.map((item) => item.police_station);
      setStations(names);
      if (names.length > 0) setStation(names[0]);
    });
  }, []);

  async function runSimulation() {
    setLoading(true);
    try {
      const response = await api.simulation({
        police_station: station,
        officer_count: officerCount,
        patrol_hours: patrolHours,
        target_eps_threshold: threshold,
      });
      setResult(response);
    } finally {
      setLoading(false);
    }
  }

  const baseline = (result?.baseline as Record<string, number>) ?? {};
  const projected = (result?.projected_outcomes as Record<string, number>) ?? {};
  const chartData = [
    { name: "Baseline", violations: baseline.weekly_violations ?? 0 },
    { name: "Prevented", violations: projected.violations_prevented_weekly ?? 0 },
    { name: "Residual", violations: projected.residual_violations_weekly ?? 0 },
  ];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Patrol Impact Simulation</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-4">
          <div>
            <label className="mb-2 block text-sm text-muted-foreground">Police Station</label>
            <Select value={station} onValueChange={setStation}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {stations.map((name) => (
                  <SelectItem key={name} value={name}>
                    {name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="mb-2 block text-sm text-muted-foreground">Officers</label>
            <Select value={String(officerCount)} onValueChange={(value) => setOfficerCount(Number(value))}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[2, 4, 6, 8, 10].map((value) => (
                  <SelectItem key={value} value={String(value)}>
                    {value}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="mb-2 block text-sm text-muted-foreground">Patrol Hours</label>
            <Select value={String(patrolHours)} onValueChange={(value) => setPatrolHours(Number(value))}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[2, 4, 6, 8].map((value) => (
                  <SelectItem key={value} value={String(value)}>
                    {value}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="mb-2 block text-sm text-muted-foreground">EPS Threshold</label>
            <Select value={String(threshold)} onValueChange={(value) => setThreshold(Number(value))}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[0.4, 0.5, 0.6, 0.7, 0.8].map((value) => (
                  <SelectItem key={value} value={String(value)}>
                    {value}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="md:col-span-4">
            <Button onClick={runSimulation} disabled={loading}>
              {loading ? "Running simulation…" : "Run Simulation"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {result && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Projected Weekly Outcomes</CardTitle>
            </CardHeader>
            <CardContent className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" tick={{ fill: "#94a3b8" }} />
                  <YAxis tick={{ fill: "#94a3b8" }} />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
                  <Bar dataKey="violations" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Simulation Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>High-risk zones: {baseline.high_risk_zones}</p>
              <p>Zones selected: {baseline.zones_selected}</p>
              <p>Effectiveness rate: {(projected.effectiveness_rate ?? 0) * 100}%</p>
              <p>Violations prevented (weekly): {projected.violations_prevented_weekly}</p>
              <p>Severity reduction (weekly): {projected.severity_reduction_weekly}</p>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
