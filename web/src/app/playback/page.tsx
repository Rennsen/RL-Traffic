"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { SumoPlaybackControls } from "@/components/SumoPlaybackControls";
import { getRun, getRuns, getSumoStatus, withApiBase } from "@/lib/api/client";
import { useDistricts } from "@/lib/district-context";
import { formatNumber } from "@/lib/format";
import { buttonVariants } from "@/components/ui/button";

export default function PlaybackPage() {
  const { activeDistrictId } = useDistricts();
  const { data: runList } = useQuery({
    queryKey: ["runs", activeDistrictId, "latest"],
    queryFn: () => getRuns({ district_id: activeDistrictId ?? undefined, limit: 1 }),
    enabled: !!activeDistrictId,
    refetchInterval: 10000,
  });

  const latestRunId = runList?.runs?.[0]?.run_id;
  const { data: runDetail } = useQuery({
    queryKey: ["run", latestRunId],
    queryFn: () => getRun(latestRunId as string),
    enabled: !!latestRunId,
    refetchInterval: 10000,
  });
  const { data: sumoStatus } = useQuery({ queryKey: ["sumo-status"], queryFn: getSumoStatus });

  const [sumoStep, setSumoStep] = useState(0);
  const [sumoPlaying, setSumoPlaying] = useState(false);
  const [sumoSpeedMs, setSumoSpeedMs] = useState(900);

  useEffect(() => {
    setSumoStep(0);
    setSumoPlaying(false);
  }, [latestRunId]);

  const backend = runDetail?.backend;
  const sumoActiveBackend = backend?.active_backend ?? (sumoStatus as any)?.active_mode ?? "internal";
  const sumoRequestedBackend = backend?.requested_backend ?? "internal";
  const sumoMessage = backend?.message ?? (sumoStatus as any)?.message ?? "SUMO status unavailable.";
  const gui = backend?.gui as any;
  const guiStreamUrl = runDetail?.run_id
    ? withApiBase(`/api/runs/${runDetail.run_id}/sumo/gui.mjpg`)
    : null;
  const guiFrameCount = Number(gui?.frame_count ?? 0);
  const guiFrameIndex = Math.max(0, Math.min(sumoStep, Math.max(guiFrameCount - 1, 0)));
  const guiFrameUrl = runDetail?.run_id
    ? withApiBase(`/api/runs/${runDetail.run_id}/sumo/gui/frame/${guiFrameIndex}`)
    : null;
  const publicFiles = (backend?.artifacts?.public_files ?? {}) as Record<string, string>;
  const layout = runDetail?.district?.layout;
  const fallbackNodeCount = layout?.intersections?.length ?? 0;
  const fallbackEdgeCount = layout?.roads?.length ?? 0;
  const nodeCount = (backend?.artifacts?.node_count ?? 0) || fallbackNodeCount;
  const edgeCount = (backend?.artifacts?.edge_count ?? 0) || fallbackEdgeCount;
  const routeCount = backend?.artifacts?.route_count ?? 0;
  const signalCount = (backend?.artifacts?.traffic_light_count ?? 0) || fallbackNodeCount;

  useEffect(() => {
    if (!sumoPlaying) {
      return;
    }
    const frameLimit = guiFrameCount || (backend?.runtime?.trace?.frames ?? []).length;
    if (!frameLimit) {
      return;
    }
    const timer = window.setInterval(() => {
      setSumoStep((current) => (current >= frameLimit - 1 ? 0 : current + 1));
    }, sumoSpeedMs);
    return () => window.clearInterval(timer);
  }, [sumoPlaying, backend, sumoSpeedMs, guiFrameCount]);

  function formatBackendLabel(value?: string) {
    if (!value) return "internal";
    return value.replace(/_/g, " ");
  }

  return (
    <div className="space-y-6">
      <section className="panel p-6 enter">
        <p className="eyebrow">Playback</p>
        <h2 className="text-2xl font-semibold">SUMO Network Playback</h2>
        <p className="mt-2 text-sm text-muted">
          The SUMO visualizer is the primary playback view. It shows network geometry and vehicle movement.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link href="/simulation" className={buttonVariants({ variant: "outline", size: "sm" })}>
            Run Simulation
          </Link>
          <Link href="/simulation" className={buttonVariants({ size: "sm" })}>
            Open Simulation Lab
          </Link>
        </div>
      </section>

      <section className="panel p-6">
        <div className="section-head">
          <p className="eyebrow">SUMO Integration</p>
          <h3 className="text-lg font-semibold">Insane Network Viewer + Runtime Playback</h3>
          <p className="mt-2 text-sm text-muted">
            Explore the SUMO-ready network geometry, then replay live runtime frames with enhanced visual depth.
          </p>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <div className="rounded-xl border border-border bg-surface p-4 shadow-soft hover-lift">
            <p className="text-xs font-medium text-muted">Requested Backend</p>
            <p className="mt-2 text-lg font-semibold">{formatBackendLabel(sumoRequestedBackend)}</p>
          </div>
          <div className="rounded-xl border border-border bg-surface p-4 shadow-soft hover-lift">
            <p className="text-xs font-medium text-muted">Active Backend</p>
            <p className="mt-2 text-lg font-semibold">{formatBackendLabel(sumoActiveBackend)}</p>
          </div>
          <div className="rounded-xl border border-border bg-surface p-4 shadow-soft hover-lift">
            <p className="text-xs font-medium text-muted">Node / Edge Count</p>
            <p className="mt-2 text-lg font-semibold">
              {formatNumber(nodeCount)} / {formatNumber(edgeCount)}
            </p>
          </div>
          <div className="rounded-xl border border-border bg-surface p-4 shadow-soft hover-lift">
            <p className="text-xs font-medium text-muted">Routes / Signals</p>
            <p className="mt-2 text-lg font-semibold">
              {formatNumber(routeCount)} / {formatNumber(signalCount)}
            </p>
          </div>
        </div>

        <p className="mt-4 text-sm text-muted">{sumoMessage}</p>
        {sumoRequestedBackend !== "sumo" ? (
          <p className="mt-1 text-xs text-muted">
            Tip: Run a new simulation with backend set to SUMO to generate runtime frames and downloadable artifacts.
          </p>
        ) : null}
        {backend?.runtime && !backend.runtime.executed && backend.runtime.reason ? (
          <p className="mt-1 text-xs text-muted">Runtime not executed: {backend.runtime.reason}</p>
        ) : null}
        {backend?.runtime?.missing_requirements?.length ? (
          <p className="mt-1 text-xs text-muted">
            Missing: {backend.runtime.missing_requirements.join(", ")}.
          </p>
        ) : null}

        <div className="mt-4 overflow-hidden rounded-2xl border border-border bg-surface-2 shadow-soft">
          {gui?.executed || gui?.snapshot_dir ? (
            <img
              src={guiFrameCount ? guiFrameUrl ?? "" : guiStreamUrl ?? ""}
              alt="SUMO GUI Stream"
              className="h-auto w-full"
            />
          ) : (
            <div className="p-6 text-sm text-muted">
              SUMO GUI frames are not available. {gui?.reason || "Ensure sumo-gui is installed and DISPLAY is set."}
            </div>
          )}
        </div>

        <div className="mt-4">
          {gui?.executed || gui?.snapshot_dir ? (
            <p className="text-xs text-muted">SUMO GUI stream auto-plays. Playback controls are available for runtime frames.</p>
          ) : null}
          <SumoPlaybackControls
            result={runDetail ?? null}
            step={sumoStep}
            playing={sumoPlaying}
            speedMs={sumoSpeedMs}
            frameCount={guiFrameCount || undefined}
            onStepChange={setSumoStep}
            onTogglePlay={() => setSumoPlaying((current) => !current)}
            onSpeedChange={setSumoSpeedMs}
          />
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-xl border border-border bg-surface p-4 shadow-soft">
            <h4 className="text-sm font-semibold">Generated Files</h4>
            <ul className="mt-3 space-y-2 text-sm text-muted">
              {Object.entries(publicFiles).length === 0 ? (
                <li>Run a simulation with SUMO backend to generate downloadable files.</li>
              ) : (
                Object.entries(publicFiles)
                  .sort(([a], [b]) => a.localeCompare(b))
                  .map(([filename, url]) => (
                    <li key={filename}>
                      <a className="text-accent underline" href={withApiBase(url)} target="_blank" rel="noopener noreferrer">
                        {filename}
                      </a>
                    </li>
                  ))
              )}
            </ul>
          </div>

          <div className="rounded-xl border border-border bg-surface p-4 shadow-soft">
            <h4 className="text-sm font-semibold">SUMO Export Preview</h4>
            <div className="mt-3 space-y-3 text-xs text-muted">
              <div>
                <p className="font-semibold text-ink">nodes.xml</p>
                <pre className="mt-1 max-h-40 overflow-auto rounded-lg border border-border bg-surface-2 p-3 text-[0.7rem]">
{backend?.preview?.nodes_xml || "No SUMO nodes export generated yet."}
                </pre>
              </div>
              <div>
                <p className="font-semibold text-ink">edges.xml</p>
                <pre className="mt-1 max-h-40 overflow-auto rounded-lg border border-border bg-surface-2 p-3 text-[0.7rem]">
{backend?.preview?.edges_xml || "No SUMO edges export generated yet."}
                </pre>
              </div>
              <div>
                <p className="font-semibold text-ink">routes.xml</p>
                <pre className="mt-1 max-h-40 overflow-auto rounded-lg border border-border bg-surface-2 p-3 text-[0.7rem]">
{backend?.preview?.routes_xml || "No SUMO routes export generated yet."}
                </pre>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
