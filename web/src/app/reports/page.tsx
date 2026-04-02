"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { AssistantPanel } from "@/components/AssistantPanel";
import { ChartCard } from "@/components/ChartCard";
import {
  getLeaderboard,
  getMonthlyReport,
  getRuns,
  getTeamPerformance,
  getWeeklyReport,
} from "@/lib/api/client";
import { formatDate, formatNumber, formatPercent } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

function TrendSparkline({ values }: { values: number[] }) {
  if (values.length === 0) {
    return <div className="h-12 rounded-lg border border-dashed border-border bg-surface-2" />;
  }
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = Math.max(1, max - min);
  const points = values
    .map((value, index) => {
      const x = (index / Math.max(1, values.length - 1)) * 100;
      const y = 100 - ((value - min) / range) * 100;
      return `${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(", ");

  return (
    <svg viewBox="0 0 100 100" className="h-12 w-full">
      <polyline
        points={points}
        fill="none"
        stroke="#2563eb"
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function ReportsPage() {
  const { data: runsData } = useQuery({
    queryKey: ["runs", "reports"],
    queryFn: () => getRuns({ limit: 30 }),
  });
  const { data: leaderboardData } = useQuery({ queryKey: ["leaderboard"], queryFn: getLeaderboard });
  const { data: teamsData } = useQuery({ queryKey: ["teams"], queryFn: getTeamPerformance });
  const { data: weeklyData } = useQuery({ queryKey: ["weekly"], queryFn: getWeeklyReport });
  const { data: monthlyData } = useQuery({ queryKey: ["monthly"], queryFn: getMonthlyReport });

  const [summary, setSummary] = useState<string>("Generate an AI summary for the latest operations.");
  const [loadingSummary, setLoadingSummary] = useState(false);

  const runs = runsData?.runs ?? [];
  const sortedRuns = [...runs].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  const runSeriesLabels = sortedRuns
    .slice(0, 20)
    .reverse()
    .map((run) => formatDate(run.created_at));
  const waitSeries = sortedRuns.slice(0, 20).reverse().map((run) => run.avg_wait);
  const queueSeries = sortedRuns.slice(0, 20).reverse().map((run) => run.avg_queue);

  const runsByDistrict = useMemo(() => {
    const map = new Map<string, typeof runs>();
    for (const run of sortedRuns) {
      if (!map.has(run.district_id)) {
        map.set(run.district_id, []);
      }
      map.get(run.district_id)?.push(run);
    }
    return map;
  }, [sortedRuns]);

  const districtTrendCards = Array.from(runsByDistrict.entries()).map(([districtId, districtRuns]) => {
    const latest = districtRuns[0];
    const series = districtRuns.slice(0, 8).reverse().map((run) => run.avg_wait);
    return {
      districtId,
      name: latest?.district_name ?? districtId,
      owner: latest?.district_name ?? districtId,
      latestWait: latest?.avg_wait ?? 0,
      waitGain: latest?.improvements?.avg_wait_pct,
      series,
    };
  });

  const bestDistrict = districtTrendCards.reduce((best, current) => {
    if (!best) return current;
    return (current.waitGain ?? 0) > (best.waitGain ?? 0) ? current : best;
  }, null as (typeof districtTrendCards)[number] | null);

  const worstDistrict = districtTrendCards.reduce((worst, current) => {
    if (!worst) return current;
    return (current.waitGain ?? 0) < (worst.waitGain ?? 0) ? current : worst;
  }, null as (typeof districtTrendCards)[number] | null);

  const totals = useMemo(() => {
    if (runs.length === 0) {
      return { avgWait: 0, avgQueue: 0, throughput: 0 };
    }
    const avgWait = runs.reduce((acc, run) => acc + run.avg_wait, 0) / runs.length;
    const avgQueue = runs.reduce((acc, run) => acc + run.avg_queue, 0) / runs.length;
    const throughput = runs.reduce((acc, run) => acc + run.throughput, 0);
    return { avgWait, avgQueue, throughput };
  }, [runs]);

  const csvRows = useMemo(() => {
    const header = [
      "run_id",
      "district",
      "created_at",
      "avg_wait",
      "avg_queue",
      "throughput",
      "clearance_ratio",
      "wait_gain_pct",
      "throughput_gain_pct",
    ];
    const summaryRow = [
      "summary",
      "-",
      new Date().toISOString(),
      totals.avgWait,
      totals.avgQueue,
      totals.throughput,
      "-",
      "-",
      "-",
    ];
    const rows = runs.map((run) => [
      run.run_id,
      run.district_name,
      run.created_at,
      run.avg_wait,
      run.avg_queue,
      run.throughput,
      run.clearance_ratio,
      run.improvements?.avg_wait_pct,
      run.improvements?.throughput_pct,
    ]);
    return [header, summaryRow, ...rows];
  }, [runs, totals]);

  function exportCsv() {
    const csv = csvRows.map((row) => row.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "flowmind-report.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function generateSummary() {
    setLoadingSummary(true);
    try {
      const response = await fetch("/api/ai/summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: "report", payload: { runs } }),
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
        <p className="eyebrow">Reports</p>
        <h2 className="text-2xl font-semibold">Operational Performance Reports</h2>
        <p className="mt-2 text-sm text-muted">
          Export results, compare district trends, and generate manager-ready summaries.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <div className="panel p-4 hover-lift">
          <p className="text-xs font-medium text-muted">Runs in Scope</p>
          <p className="mt-2 text-2xl font-semibold">{runs.length}</p>
          <p className="mono mt-2">Report window</p>
        </div>
        <div className="panel p-4 hover-lift">
          <p className="text-xs font-medium text-muted">Avg Wait</p>
          <p className="mt-2 text-2xl font-semibold">{formatNumber(totals.avgWait)}</p>
          <p className="mono mt-2">Across all runs</p>
        </div>
        <div className="panel p-4 hover-lift">
          <p className="text-xs font-medium text-muted">Avg Queue</p>
          <p className="mt-2 text-2xl font-semibold">{formatNumber(totals.avgQueue)}</p>
          <p className="mono mt-2">Across all runs</p>
        </div>
        <div className="panel p-4 hover-lift">
          <p className="text-xs font-medium text-muted">Total Throughput</p>
          <p className="mt-2 text-2xl font-semibold">{formatNumber(totals.throughput, 0)}</p>
          <p className="mono mt-2">Vehicles served</p>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
        <ChartCard
          title="Network Wait + Queue Trend"
          labels={runSeriesLabels}
          datasets={[
            {
              label: "Avg Wait",
              data: waitSeries,
              borderColor: "#2563eb",
              backgroundColor: "rgba(37, 99, 235, 0.14)",
            },
            {
              label: "Avg Queue",
              data: queueSeries,
              borderColor: "#f38020",
              backgroundColor: "rgba(243, 128, 32, 0.18)",
            },
          ]}
        />
        <div className="panel p-6">
          <h3 className="text-lg font-semibold">Top Movers</h3>
          <div className="mt-4 space-y-3">
            <div className="rounded-xl border border-border bg-surface-2 p-4 shadow-soft">
              <p className="text-xs font-medium text-muted">Best Improvement</p>
              <p className="mt-2 text-lg font-semibold">{bestDistrict?.name ?? "-"}</p>
              <p className="text-sm text-muted">Wait gain {formatPercent(bestDistrict?.waitGain)}</p>
            </div>
            <div className="rounded-xl border border-border bg-surface-2 p-4 shadow-soft">
              <p className="text-xs font-medium text-muted">Needs Attention</p>
              <p className="mt-2 text-lg font-semibold">{worstDistrict?.name ?? "-"}</p>
              <p className="text-sm text-muted">Wait gain {formatPercent(worstDistrict?.waitGain)}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="panel p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="eyebrow">District Trends</p>
            <h3 className="text-lg font-semibold">Performance over recent runs</h3>
          </div>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {districtTrendCards.map((card) => (
            <div key={card.districtId} className="rounded-xl border border-border bg-surface-2 p-4 shadow-soft hover-lift">
              <div className="flex items-center justify-between">
                <p className="font-semibold">{card.name}</p>
                <span className="text-xs text-muted">Wait gain {formatPercent(card.waitGain)}</span>
              </div>
              <p className="text-sm text-muted mt-1">Latest avg wait {formatNumber(card.latestWait)}</p>
              <div className="mt-3">
                <TrendSparkline values={card.series} />
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        <div className="panel p-6">
          <h3 className="text-lg font-semibold">Leaderboard</h3>
          <div className="mt-4 space-y-2">
            {(leaderboardData?.leaderboard ?? []).map((row: any) => (
              <div key={row.district_id} className="rounded-xl border border-border bg-surface-2 p-3 shadow-soft">
                <p className="font-semibold">{row.district_name}</p>
                <p className="text-sm text-muted">Wait gain {formatPercent(row.avg_wait_pct)}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="panel p-6">
          <h3 className="text-lg font-semibold">Team Performance</h3>
          <div className="mt-4 space-y-2">
            {(teamsData?.teams ?? []).map((row: any, index: number) => (
              <div key={`${row.team}-${index}`} className="rounded-xl border border-border bg-surface-2 p-3 shadow-soft">
                <p className="font-semibold">{row.team}</p>
                <p className="text-sm text-muted">{row.district} · {row.owner}</p>
                <p className="text-xs text-muted">Wait gain {formatPercent(row.wait_gain)}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="panel p-6">
          <h3 className="text-lg font-semibold">Snapshots</h3>
          <div className="mt-4 space-y-3">
            <div className="rounded-xl border border-border bg-surface-2 p-3 shadow-soft">
              <p className="font-semibold">Weekly</p>
              <p className="text-sm text-muted">Runs: {weeklyData?.count ?? weeklyData?.runs?.length ?? 0}</p>
              <p className="text-xs text-muted">Avg wait: {formatNumber(weeklyData?.avg_wait)}</p>
              <p className="text-xs text-muted">Avg queue: {formatNumber(weeklyData?.avg_queue)}</p>
              <p className="text-xs text-muted">Throughput: {formatNumber(weeklyData?.throughput, 0)}</p>
            </div>
            <div className="rounded-xl border border-border bg-surface-2 p-3 shadow-soft">
              <p className="font-semibold">Monthly</p>
              <p className="text-sm text-muted">Runs: {monthlyData?.count ?? monthlyData?.runs?.length ?? 0}</p>
              <p className="text-xs text-muted">Avg wait: {formatNumber(monthlyData?.avg_wait)}</p>
              <p className="text-xs text-muted">Avg queue: {formatNumber(monthlyData?.avg_queue)}</p>
              <p className="text-xs text-muted">Throughput: {formatNumber(monthlyData?.throughput, 0)}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="panel p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="eyebrow">History</p>
            <h3 className="text-lg font-semibold">Recent Runs</h3>
          </div>
          <Button variant="outline" type="button" onClick={exportCsv}>
            Export CSV
          </Button>
        </div>
        <div className="mt-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>District</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Avg Wait</TableHead>
                <TableHead>Avg Queue</TableHead>
                <TableHead>Throughput</TableHead>
                <TableHead>Clearance</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.map((run) => (
                <TableRow key={run.run_id}>
                  <TableCell>{run.district_name}</TableCell>
                  <TableCell>{formatDate(run.created_at)}</TableCell>
                  <TableCell>{formatNumber(run.avg_wait)}</TableCell>
                  <TableCell>{formatNumber(run.avg_queue)}</TableCell>
                  <TableCell>{formatNumber(run.throughput, 0)}</TableCell>
                  <TableCell>{formatNumber(run.clearance_ratio)}</TableCell>
                </TableRow>
              ))}
              {runs.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="py-6 text-center text-sm text-muted">
                    No runs yet. Run a simulation to populate reporting data.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[0.7fr_1.3fr]">
        <div className="panel p-6">
          <p className="eyebrow">AI Summary</p>
          <h3 className="text-lg font-semibold">Manager Brief</h3>
          <p className="mt-3 text-sm text-muted">{summary}</p>
          <Button className="mt-4" onClick={generateSummary} type="button">
            {loadingSummary ? "Generating..." : "Generate Summary"}
          </Button>
        </div>
        <AssistantPanel compact context={JSON.stringify({ runs })} />
      </section>
    </div>
  );
}
