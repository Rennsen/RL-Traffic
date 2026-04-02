"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { getAlerts, getLeaderboard, getNotifications, getRuns, getWeeklyReport } from "@/lib/api/client";
import { useDistricts } from "@/lib/district-context";
import { formatNumber, formatPercent } from "@/lib/format";
import { Badge } from "@/components/ui/badge";

export default function ExecutivePage() {
  const { districts } = useDistricts();
  const { data: runsData } = useQuery({ queryKey: ["runs", "executive"], queryFn: () => getRuns({ limit: 60 }) });
  const { data: alertsData } = useQuery({ queryKey: ["alerts"], queryFn: getAlerts });
  const { data: notificationsData } = useQuery({ queryKey: ["notifications"], queryFn: getNotifications });
  const { data: leaderboardData } = useQuery({ queryKey: ["leaderboard"], queryFn: getLeaderboard });
  const { data: weeklyData } = useQuery({ queryKey: ["weekly"], queryFn: getWeeklyReport });

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

  const criticalNotifications = (notificationsData?.notifications ?? []).filter(
    (item: any) => item.severity === "high",
  );

  return (
    <div className="space-y-6">
      <section className="panel p-6 enter">
        <p className="eyebrow">Executive</p>
        <h2 className="text-2xl font-semibold">Citywide Pulse Dashboard</h2>
        <p className="mt-2 text-sm text-muted">
          A mobile-first briefing view for leadership decisions, highlighting top risks and performance gains.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2">
        <div className="panel p-5 hover-lift">
          <p className="text-xs font-medium text-muted">Avg Wait</p>
          <p className="mt-2 text-3xl font-semibold">{formatNumber(avgWait)}</p>
          <p className="text-xs text-muted mt-1">sec across latest runs</p>
        </div>
        <div className="panel p-5 hover-lift">
          <p className="text-xs font-medium text-muted">Avg Queue</p>
          <p className="mt-2 text-3xl font-semibold">{formatNumber(avgQueue)}</p>
          <p className="text-xs text-muted mt-1">vehicles per intersection</p>
        </div>
        <div className="panel p-5 hover-lift">
          <p className="text-xs font-medium text-muted">Throughput</p>
          <p className="mt-2 text-3xl font-semibold">{formatNumber(throughput)}</p>
          <p className="text-xs text-muted mt-1">total vehicles served</p>
        </div>
        <div className="panel p-5 hover-lift">
          <p className="text-xs font-medium text-muted">Active Districts</p>
          <p className="mt-2 text-3xl font-semibold">{districts.length}</p>
          <p className="text-xs text-muted mt-1">managed corridors</p>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="panel p-6">
          <p className="eyebrow">Critical Focus</p>
          <h3 className="text-lg font-semibold">High Priority Notifications</h3>
          <div className="mt-4 space-y-3">
            {criticalNotifications.slice(0, 4).map((item: any) => (
              <div key={item.notification_id} className="rounded-xl border border-border bg-surface-2 p-4 shadow-soft">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold">{item.title}</p>
                  <Badge variant="danger">{item.category.replace(/_/g, " ")}</Badge>
                </div>
                <p className="mt-2 text-xs text-muted">{item.message}</p>
              </div>
            ))}
            {criticalNotifications.length === 0 && (
              <div className="rounded-xl border border-dashed border-border p-6 text-sm text-muted">
                No critical notifications right now.
              </div>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div className="panel p-5">
            <p className="eyebrow">Leaderboard</p>
            <h3 className="text-sm font-semibold">Top Performing Districts</h3>
            <div className="mt-3 space-y-2 text-sm">
              {(leaderboardData?.leaderboard ?? []).slice(0, 3).map((row: any, index: number) => (
                <div key={row.district_id} className="flex items-center justify-between rounded-xl bg-surface-2 px-3 py-2 shadow-soft">
                  <div>
                    <p className="text-xs text-muted">#{index + 1}</p>
                    <p className="font-semibold">{row.district_name}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold">{formatPercent(row.avg_wait_pct ?? 0)}</p>
                    <p className="text-[0.65rem] text-muted">wait reduction</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="panel p-5">
            <p className="eyebrow">Weekly Snapshot</p>
            <h3 className="text-sm font-semibold">Aggregate Trend</h3>
            <div className="mt-3 space-y-2 text-xs text-muted">
              <div className="flex items-center justify-between">
                <span>Runs completed</span>
                <span className="font-semibold text-ink">{weeklyData?.count ?? 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Avg wait</span>
                <span className="font-semibold text-ink">{formatNumber(weeklyData?.avg_wait ?? 0)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Avg queue</span>
                <span className="font-semibold text-ink">{formatNumber(weeklyData?.avg_queue ?? 0)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Total throughput</span>
                <span className="font-semibold text-ink">{formatNumber(weeklyData?.throughput ?? 0)}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="panel p-6">
        <p className="eyebrow">Active Alerts</p>
        <h3 className="text-lg font-semibold">Operational Risks</h3>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {(alertsData?.alerts ?? []).slice(0, 4).map((alert) => (
            <div key={alert.alert_id} className="rounded-xl border border-border bg-surface-2 p-4 shadow-soft">
              <p className="text-sm font-semibold">{alert.title}</p>
              <p className="mt-2 text-xs text-muted">{alert.message}</p>
            </div>
          ))}
          {(alertsData?.alerts ?? []).length === 0 && (
            <div className="rounded-xl border border-dashed border-border p-6 text-sm text-muted">
              No alerts currently active.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
