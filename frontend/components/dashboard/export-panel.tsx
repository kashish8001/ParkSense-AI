"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

export function ExportPanel() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Export Reports</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-3">
        <Button variant="secondary" asChild>
          <a href={api.exportCsvUrl()} target="_blank" rel="noreferrer">
            Download Priority CSV
          </a>
        </Button>
        <Button variant="secondary" asChild>
          <a href={api.exportGeoJsonUrl()} target="_blank" rel="noreferrer">
            Download Heatmap GeoJSON
          </a>
        </Button>
        <Button variant="secondary" asChild>
          <a href={api.exportSummaryUrl()} target="_blank" rel="noreferrer">
            Download Summary JSON
          </a>
        </Button>
      </CardContent>
    </Card>
  );
}
