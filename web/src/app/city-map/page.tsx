"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { getAlerts, getRuns } from "@/lib/api/client";
import { useDistricts } from "@/lib/district-context";
import { formatNumber, formatPercent } from "@/lib/format";

function scoreFromRun(run: any) {
  if (!run) return 0;
  const waitScore = Math.max(0, 100 - (run.avg_wait ?? 0) * 0.8);
  const queueScore = Math.max(0, 100 - (run.avg_queue ?? 0) * 0.2);
  const throughputScore = Math.min(100, (run.throughput ?? 0) / 15);
  return Math.round((waitScore + queueScore + throughputScore) / 3);
}

export default function CityMapPage() {
  const { districts, activeDistrictId, setActiveDistrictId } = useDistricts();
  const { data: runsData } = useQuery({ queryKey: ["runs", "city-map"], queryFn: () => getRuns({ limit: 60 }) });
  const { data: alertsData } = useQuery({ queryKey: ["alerts"], queryFn: getAlerts });

  const latestRuns = useMemo(() => {
    const map = new Map<string, any>();
    for (const run of runsData?.runs ?? []) {
      if (!map.has(run.district_id)) {
        map.set(run.district_id, run);
      }
    }
    return map;
  }, [runsData]);

  const cols = 2;
  const cellW = 420;
  const cellH = 220;
  const margin = 40;
  const rows = Math.max(1, Math.ceil(districts.length / cols));
  const width = margin * 2 + cols * cellW + (cols - 1) * margin;
  const height = margin * 2 + rows * cellH + (rows - 1) * margin;

  return (
    <div className="space-y-6">
      <section className="panel p-6 enter">
        <p className="eyebrow">City Map</p>
        <h2 className="text-2xl font-semibold">Multi-Intersection Command View</h2>
        <p className="mt-2 text-sm text-muted max-w-2xl">
          Scan every district at once, drill into hot corridors, and launch scenario templates for rapid response.
        </p>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="panel p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="eyebrow">City Grid</p>
              <h3 className="text-lg font-semibold">Intersection Health</h3>
            </div>
            <span className="mono">{districts.length} districts mapped</span>
          </div>
          <div className="mt-4 rounded-xl border border-border bg-surface-2 p-3">
            <svg
              viewBox={`0 0 ${width} ${height}`}
              className="w-full"
              style={{ height: Math.max(420, Math.min(620, height)) }}
            >
              {districts.map((district, index) => {
                const col = index % cols;
                const row = Math.floor(index / cols);
                const x = margin + col * (cellW + margin);
                const y = margin + row * (cellH + margin);
                const layout = district.layout ?? { width: 1, height: 1, roads: [], intersections: [] };
                const scale = Math.min(cellW / layout.width, cellH / layout.height);
                const innerX = (cellW - layout.width * scale) / 2;
                const innerY = (cellH - layout.height * scale) / 2;
                const run = latestRuns.get(district.district_id);
                const score = scoreFromRun(run);
                const isActive = district.district_id === activeDistrictId;

                return (
                  <g key={district.district_id} transform={`translate(${x}, ${y})`}>
                    <rect
                      x={0}
                      y={0}
                      width={cellW}
                      height={cellH}
                      rx={18}
                      fill={isActive ? "rgba(37, 99, 235, 0.12)" : "rgba(255,255,255,0.7)"}
                      stroke={isActive ? "#2563eb" : "rgba(15,23,42,0.15)"}
                      strokeWidth={isActive ? 2 : 1}
                      onClick={() => setActiveDistrictId(district.district_id)}
                      style={{ cursor: "pointer" }}
                    />
                    <text x={18} y={26} fontSize={12} fill="#0f1b2d" fontWeight={600}>
                      {district.name}
                    </text>
                    <text x={18} y={44} fontSize={10} fill="#5a6b85">
                      Health Score {score}
                    </text>
                    <g transform={`translate(${innerX}, ${innerY}) scale(${scale})`}>
                      {(layout.roads ?? []).map((road: any) => (
                        <line
                          key={road.id}
                          x1={road.from[0]}
                          y1={road.from[1]}
                          x2={road.to[0]}
                          y2={road.to[1]}
                          stroke="rgba(91,107,128,0.6)"
                          strokeWidth={Math.max(1, road.lanes ?? 1) * 1.2}
                        />
                      ))}
                      {(layout.intersections ?? []).map((node: any) => (
                        <circle
                          key={node.id}
                          cx={node.x}
                          cy={node.y}
                          r={6}
                          fill={isActive ? "#2563eb" : "#0ea5e9"}
                          opacity={0.9}
                        />
                      ))}
                    </g>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>

        <div className="space-y-4">
          <div className="panel p-4">
            <p className="eyebrow">Hotspots</p>
            <h3 className="text-sm font-semibold">Live Risk Zones</h3>
            <div className="mt-3 space-y-2">
              {(alertsData?.alerts ?? []).slice(0, 4).map((alert) => (
                <div key={alert.alert_id} className="rounded-xl border border-border bg-surface-2 p-3 shadow-soft">
                  <div className="text-xs font-semibold">{alert.title}</div>
                  <div className="text-[0.7rem] text-muted">{alert.message}</div>
                </div>
              ))}
              {(alertsData?.alerts ?? []).length === 0 && (
                <p className="text-xs text-muted">No active congestion spikes.</p>
              )}
            </div>
          </div>

          <div className="panel p-4">
            <p className="eyebrow">Pulse</p>
            <h3 className="text-sm font-semibold">District Status</h3>
            <div className="mt-3 space-y-2">
              {districts.map((district) => {
                const run = latestRuns.get(district.district_id);
                return (
                  <div key={district.district_id} className="rounded-xl border border-border bg-surface-2 p-3 shadow-soft">
                    <div className="flex items-center justify-between">
                      <div className="text-xs font-semibold">{district.name}</div>
                      <div className="mono">
                        {formatPercent(run?.improvements?.avg_wait_pct ?? 0)}
                      </div>
                    </div>
                    <div className="mt-2 grid grid-cols-2 gap-2 text-[0.7rem] text-muted">
                      <span>Avg Wait: {formatNumber(run?.avg_wait ?? 0)}</span>
                      <span>Queue: {formatNumber(run?.avg_queue ?? 0)}</span>
                      <span>Throughput: {formatNumber(run?.throughput ?? 0)}</span>
                      <span>Clearance: {formatNumber(run?.clearance_ratio ?? 0)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
