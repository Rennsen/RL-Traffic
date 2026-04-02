"use client";

import { useEffect, useMemo } from "react";

import type { RunResult } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";

interface SumoPlaybackControlsProps {
  result: RunResult | null;
  step: number;
  playing: boolean;
  speedMs: number;
  frameCount?: number;
  onStepChange: (next: number) => void;
  onTogglePlay: () => void;
  onSpeedChange: (next: number) => void;
}

function avgSpeedForFrame(frame?: { vehicles?: Array<{ speed?: number }> }) {
  const vehicles = frame?.vehicles ?? [];
  if (vehicles.length === 0) {
    return 0;
  }
  let total = 0;
  vehicles.forEach((vehicle) => {
    total += Number(vehicle.speed) || 0;
  });
  return total / vehicles.length;
}

export function SumoPlaybackControls({
  result,
  step,
  playing,
  speedMs,
  onStepChange,
  onTogglePlay,
  onSpeedChange,
  frameCount,
}: SumoPlaybackControlsProps) {
  const frames = result?.backend?.runtime?.trace?.frames ?? [];
  const fallbackMaxStep = Math.max(0, frames.length - 1);
  const maxStep = Math.max(0, (frameCount ?? 0) - 1, fallbackMaxStep);
  const runtimeIndex =
    frames.length > 0 && maxStep > 0
      ? Math.round((Math.min(step, maxStep) / maxStep) * (frames.length - 1))
      : 0;
  const frame = frames[Math.max(0, Math.min(runtimeIndex, fallbackMaxStep))];

  const runtimeSeries = result?.backend?.runtime?.time_series ?? {};
  const queueNow = runtimeSeries?.queue?.[runtimeIndex] ?? 0;
  const throughputNow = runtimeSeries?.throughput?.[runtimeIndex] ?? 0;

  const avgSpeed = useMemo(() => avgSpeedForFrame(frame), [frame]);

  useEffect(() => {
    if (step > maxStep) {
      onStepChange(maxStep);
    }
  }, [step, maxStep, onStepChange]);

  if (!frames.length && !frameCount) {
    return (
      <div className="rounded-xl border border-dashed border-border bg-surface-2 p-4 text-sm text-muted">
        Run with SUMO backend to generate runtime frames for playback.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        <label className="text-xs text-muted flex-1">
          SUMO Step
          <Slider
            className="mt-2"
            min={0}
            max={maxStep}
            step={1}
            value={[step]}
            onValueChange={(value) => onStepChange(value[0] ?? 0)}
          />
        </label>
        <label className="text-xs text-muted">
          Speed
          <select
            className="mt-1 h-9 rounded-md border border-border bg-surface px-2 text-xs text-ink"
            value={String(speedMs)}
            onChange={(event) => onSpeedChange(Number(event.target.value))}
          >
            <option value="900">Slow</option>
            <option value="650">Medium</option>
            <option value="420">Fast</option>
          </select>
        </label>
        <Button type="button" onClick={onTogglePlay}>
          {playing ? "Pause" : "Play"}
        </Button>
        <div className="mono">SUMO step {step} / {maxStep}</div>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <div className="rounded-xl border border-border bg-surface p-4 shadow-soft hover-lift">
          <p className="text-xs font-medium text-muted">Vehicles In Network</p>
          <p className="mt-2 text-lg font-semibold">{frame?.vehicle_count ?? 0}</p>
        </div>
        <div className="rounded-xl border border-border bg-surface p-4 shadow-soft hover-lift">
          <p className="text-xs font-medium text-muted">Average Speed</p>
          <p className="mt-2 text-lg font-semibold">{avgSpeed.toFixed(2)}</p>
        </div>
        <div className="rounded-xl border border-border bg-surface p-4 shadow-soft hover-lift">
          <p className="text-xs font-medium text-muted">Throughput At Step</p>
          <p className="mt-2 text-lg font-semibold">{throughputNow.toFixed(2)}</p>
        </div>
        <div className="rounded-xl border border-border bg-surface p-4 shadow-soft hover-lift">
          <p className="text-xs font-medium text-muted">Queue At Step</p>
          <p className="mt-2 text-lg font-semibold">{queueNow.toFixed(2)}</p>
        </div>
      </div>
    </div>
  );
}
