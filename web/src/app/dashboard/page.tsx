"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { ChartCard } from "@/components/ChartCard";
import { StatCard } from "@/components/StatCard";
import { getAlerts, getRun, getRuns } from "@/lib/api/client";
import { useDistricts } from "@/lib/district-context";
import { formatNumber } from "@/lib/format";

export default function DashboardPage() {
  const { activeDistrictId } = useDistricts();
  const { data: runList } = useQuery({
    queryKey: ["runs", activeDistrictId, "latest"],
    queryFn: () => getRuns({ district_id: activeDistrictId ?? undefined, limit: 1 }),
    enabled: !!activeDistrictId,
    refetchInterval: 15000,
  });
  const { data: alertsData } = useQuery({
    queryKey: ["alerts"],
    queryFn: getAlerts,
    refetchInterval: 20000,
  });

  const latestRunId = runList?.runs?.[0]?.run_id;
  const { data: runDetail } = useQuery({
    queryKey: ["run", latestRunId],
    queryFn: () => getRun(latestRunId as string),
    enabled: !!latestRunId,
    refetchInterval: 15000,
  });

  const series = runDetail?.time_series?.rl;
  const labels = useMemo(
    () => (series?.queue ? series.queue.map((_: number, index: number) => String(index + 1)) : []),
    [series],
  );

  const throughputSeries = useMemo(() => {
    if (!series?.throughput) {
      return [];
    }
    let running = 0;
    return series.throughput.map((value: number) => {
      running += value;
      return running;
    });
  }, [series]);

  const latestPhase = series?.phase?.[series?.phase?.length - 1] ?? 0;
  const latestEmergencyQueue = series?.emergency_queue?.[series?.emergency_queue?.length - 1] ?? 0;

  const liveSummary = useMemo(() => {
    if (!runDetail) {
      return "No live run yet. Start a simulation to generate live metrics.";
    }
    const avgWait = runDetail.comparison.rl.avg_wait;
    const avgQueue = runDetail.comparison.rl.avg_queue;
    const emergency = runDetail.comparison.rl.emergency_avg_wait;
    if (avgQueue > 250 || avgWait > 60) {
      return "Congestion elevated. Consider lowering fixed cycle and increasing service rate.";
    }
    if (emergency > 12) {
      return "Emergency wait time is trending high. Consider boosting emergency priority.";
    }
    return "Traffic flow is within target bounds. Continue monitoring.";
  }, [runDetail]);

  return (
    <div className="space-y-6">
      <section className="panel p-6 enter">
        <p className="eyebrow">Live Dashboard</p>
        <h2 className="text-2xl font-semibold">District Operations Pulse</h2>
        <p className="mt-2 text-sm text-muted">
          Auto-refreshes from the latest simulation run to provide a live operational readout.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-6">
        <StatCard label="Avg Wait" value={formatNumber(runDetail?.comparison.rl.avg_wait)} helper="RL controller" />
        <StatCard label="Avg Queue" value={formatNumber(runDetail?.comparison.rl.avg_queue)} helper="RL controller" />
        <StatCard label="Throughput" value={formatNumber(runDetail?.comparison.rl.throughput, 0)} helper="RL controller" />
        <StatCard
          label="Emergency Wait"
          value={formatNumber(runDetail?.comparison.rl.emergency_avg_wait)}
          helper="RL controller"
        />
        <StatCard label="Emergency Queue" value={formatNumber(latestEmergencyQueue)} helper="Live step" />
        <StatCard label="Signal Phase" value={latestPhase === 0 ? "NS Green" : "EW Green"} helper="Current phase" />
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="panel p-6">
          <p className="eyebrow">Live Summary</p>
          <h3 className="text-lg font-semibold">Traffic Condition Brief</h3>
          <p className="mt-3 text-sm text-muted">{liveSummary}</p>
        </div>
        <div className="panel p-6">
          <p className="eyebrow">Alerts</p>
          <h3 className="text-lg font-semibold">Active Banners</h3>
          <div className="mt-3 space-y-2">
            {(alertsData?.alerts ?? []).length === 0 ? (
              <div className="rounded-xl border border-dashed border-border p-4 text-sm text-muted">
                No active alerts right now.
              </div>
            ) : (
              alertsData?.alerts.map((alert) => (
                <div key={alert.alert_id} className="rounded-xl border border-border bg-surface-2 p-3 shadow-soft">
                  <p className="font-semibold text-ink">{alert.title}</p>
                  <p className="text-sm text-muted">{alert.message}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <ChartCard
          title="Queue Pressure"
          labels={labels}
          datasets={[
            {
              label: "Queue",
              data: series?.queue ?? [],
              borderColor: "#2563eb",
              backgroundColor: "rgba(37, 99, 235, 0.14)",
            },
          ]}
        />
        <ChartCard
          title="Cumulative Throughput"
          labels={labels}
          datasets={[
            {
              label: "Throughput",
              data: throughputSeries,
              borderColor: "#0ea5e9",
              backgroundColor: "rgba(14, 165, 233, 0.18)",
            },
          ]}
        />
      </section>
    </div>
  );
}
