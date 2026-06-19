import { SimulationDashboard } from "@/components/simulation/simulation-dashboard";

export default function SimulationPage() {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold">Simulation Dashboard</h2>
        <p className="text-sm text-muted-foreground">
          Model patrol scenarios using enforcement priority scores and projected violation reductions.
        </p>
      </div>
      <SimulationDashboard />
    </div>
  );
}
