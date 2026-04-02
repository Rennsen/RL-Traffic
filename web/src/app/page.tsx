"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { AlertCard } from "@/components/AlertCard";
import { AssistantPanel } from "@/components/AssistantPanel";
import { StatCard } from "@/components/StatCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getAIRecommendations, getAlerts, getAnomalies, getRuns } from "@/lib/api/client";
import { formatNumber } from "@/lib/format";
import { useDistricts } from "@/lib/district-context";

export default function OverviewPage() {
  const { districts, activeDistrictId } = useDistricts();
  const { data: alertsData } = useQuery({ queryKey: ["alerts"], queryFn: getAlerts });
  const { data: anomaliesData } = useQuery({ queryKey: ["anomalies"], queryFn: getAnomalies });
  const { data: recommendationsData } = useQuery({
    queryKey: ["recommendations", activeDistrictId],
    queryFn: () => getAIRecommendations(activeDistrictId ?? "downtown_core"),
    enabled: !!activeDistrictId,
  });
  const { data: runsData } = useQuery({
    queryKey: ["runs", "overview"],
    queryFn: () => getRuns({ limit: 50 }),
  });

  const [summary, setSummary] = useState<string>("Click generate to summarize the latest operations.");
  const [loadingSummary, setLoadingSummary] = useState(false);

  const latestRuns = useMemo(() => {
    const map = new Map<string, any>();
    for (const run of runsData?.runs ?? []) {
      if (!map.has(run.district_id)) {
        map.set(run.district_id, run);
      }
    }
    return Array.from(map.values());
  }, [runsData]);

  const avgWait = latestRuns.length
    ? latestRuns.reduce((acc, run) => acc + run.avg_wait, 0) / latestRuns.length
    : 0;
  const avgQueue = latestRuns.length
    ? latestRuns.reduce((acc, run) => acc + run.avg_queue, 0) / latestRuns.length
    : 0;
  const throughput = latestRuns.reduce((acc, run) => acc + run.throughput, 0);

  async function generateSummary() {
    setLoadingSummary(true);
    try {
      const response = await fetch("/api/ai/summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind: "daily_ops",
          payload: {
            districts: districts.map((district) => ({
              id: district.district_id,
              name: district.name,
              owner: district.manager.owner,
            })),
            latest_runs: latestRuns,
          },
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || "Summary failed.");
      }
      setSummary(data.output);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Summary unavailable.";
      setSummary(message);
    } finally {
      setLoadingSummary(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="panel p-6 enter">
        <p className="eyebrow">Overview</p>
        <h2 className="text-2xl font-semibold">City Traffic Intelligence</h2>
        <p className="mt-2 text-sm text-muted max-w-2xl">
          Monitor citywide health, active alerts, and AI summaries across all districts. Every simulation run feeds the
          live ops story below.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <StatCard label="Active Districts" value={districts.length} helper="Currently configured" />
        <StatCard label="Avg Wait (sec)" value={formatNumber(avgWait)} helper="Across latest runs" />
        <StatCard label="Avg Queue" value={formatNumber(avgQueue)} helper="Across latest runs" />
        <StatCard label="Total Throughput" value={formatNumber(throughput)} helper="Vehicles served" />
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
        <div className="panel p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="eyebrow">Alerts</p>
              <h3 className="text-lg font-semibold">Operational Flags</h3>
            </div>
            <span className="mono">{alertsData?.alerts.length ?? 0} active</span>
          </div>
          <div className="mt-4 grid gap-3">
            {(alertsData?.alerts ?? []).length === 0 ? (
              <div className="rounded-xl border border-dashed border-border p-6 text-sm text-muted">
                No alerts yet. Run simulations to surface congestion spikes and risk zones.
              </div>
            ) : (
              alertsData?.alerts.map((alert) => <AlertCard key={alert.alert_id} alert={alert} />)
            )}
          </div>
        </div>

        <div className="panel p-6">
          <p className="eyebrow">AI Summary</p>
          <h3 className="text-lg font-semibold">Daily Ops Brief</h3>
          <p className="mt-3 text-sm text-muted">{summary}</p>
          <Button className="mt-4" onClick={generateSummary} type="button">
            {loadingSummary ? "Generating..." : "Generate Summary"}
          </Button>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="panel p-6">
          <p className="eyebrow">Anomaly Detection</p>
          <h3 className="text-lg font-semibold">AI Detected Issues</h3>
          <div className="mt-4 space-y-3">
            {(anomaliesData?.anomalies ?? []).length === 0 ? (
              <div className="rounded-xl border border-dashed border-border p-6 text-sm text-muted">
                No anomalies detected. Traffic behavior looks stable.
              </div>
            ) : (
              anomaliesData?.anomalies.map((anomaly: any) => (
                <div key={anomaly.anomaly_id} className="rounded-xl border border-border bg-surface-2 p-4 shadow-soft">
                  <p className="font-semibold">{anomaly.title}</p>
                  <p className="text-sm text-muted mt-1">{anomaly.message}</p>
                  <p className="mono mt-2">{anomaly.metric}: {anomaly.value}</p>
                </div>
              ))
            )}
          </div>
        </div>
        <div className="panel p-6">
          <p className="eyebrow">AI Recommendations</p>
          <h3 className="text-lg font-semibold">Suggested Adjustments</h3>
          <div className="mt-4 space-y-3">
            {(recommendationsData?.recommendations ?? []).map((rec: string, index: number) => (
              <div key={`${rec}-${index}`} className="rounded-xl border border-border bg-surface-2 p-4 text-sm shadow-soft">
                {rec}
              </div>
            ))}
            {(recommendationsData?.recommendations ?? []).length === 0 && (
              <p className="text-sm text-muted">Run a simulation to generate recommendations.</p>
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="panel p-6">
          <p className="eyebrow">Next Actions</p>
          <h3 className="text-lg font-semibold">Launch the right workflow</h3>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <Card className="hover-lift">
              <CardContent className="p-4">
                <a className="block" href="/simulation">
                  <p className="font-semibold text-ink">Run a new simulation</p>
                  <p className="mt-2 text-sm text-muted">Tune RL parameters and compare against fixed timing.</p>
                </a>
              </CardContent>
            </Card>
            <Card className="hover-lift">
              <CardContent className="p-4">
                <a className="block" href="/playback">
                  <p className="font-semibold text-ink">Open playback map</p>
                  <p className="mt-2 text-sm text-muted">Inspect intersection phases and vehicle density step-by-step.</p>
                </a>
              </CardContent>
            </Card>
          </div>
        </div>

        <AssistantPanel compact context={JSON.stringify({ latestRuns })} districtId={activeDistrictId ?? undefined} />
      </section>
    </div>
  );
}
