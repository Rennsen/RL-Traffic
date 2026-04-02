"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { ChartCard } from "@/components/ChartCard";
import { StatCard } from "@/components/StatCard";
import { createPreset, getPresets, getTemplates, runSimulation } from "@/lib/api/client";
import { useDistricts } from "@/lib/district-context";
import { formatNumber, formatPercent } from "@/lib/format";
import type { RunResult } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const trafficPatterns = [
  { label: "Rush Hour (NS)", value: "rush_hour_ns" },
  { label: "Rush Hour (EW)", value: "rush_hour_ew" },
  { label: "Balanced", value: "balanced" },
  { label: "Event Spike", value: "event_spike" },
  { label: "Random", value: "random" },
];

const algorithms = [
  { label: "Q-Learning", value: "q_learning" },
  { label: "DQN", value: "dqn" },
  { label: "PPO", value: "ppo" },
];

const backends = [
  { label: "Internal Simulator", value: "internal" },
  { label: "SUMO", value: "sumo" },
];

export default function SimulationPage() {
  const { districts, activeDistrictId } = useDistricts();
  const activeDistrict = districts.find((district) => district.district_id === activeDistrictId) ?? null;
  const { data: presetsData, refetch } = useQuery({ queryKey: ["presets"], queryFn: getPresets });
  const { data: templatesData } = useQuery({ queryKey: ["templates"], queryFn: getTemplates });

  const [form, setForm] = useState({
    district_id: activeDistrictId ?? "downtown_core",
    algorithm: "q_learning",
    backend: "sumo",
    episodes: 260,
    steps_per_episode: 240,
    traffic_pattern: "rush_hour_ns",
    fixed_cycle: 18,
    service_rate: 3,
    emergency_rate: 0.02,
    learning_rate: 0.12,
    discount_factor: 0.95,
    epsilon_start: 1.0,
    epsilon_min: 0.05,
    epsilon_decay: 0.992,
    switch_penalty: 1.1,
    seed: 42,
    actual_avg_wait: "",
    actual_avg_queue: "",
    actual_throughput: "",
    actual_emergency_avg_wait: "",
    actual_clearance_ratio: "",
  });

  const [result, setResult] = useState<RunResult | null>(null);
  const [status, setStatus] = useState("Ready. Configure parameters and run a simulation.");
  const [loading, setLoading] = useState(false);
  const [presetName, setPresetName] = useState("");
  const [presetDescription, setPresetDescription] = useState("");

  useEffect(() => {
    if (!activeDistrict) {
      return;
    }
    setForm((current) => ({
      ...current,
      district_id: activeDistrict.district_id,
      traffic_pattern: activeDistrict.traffic_pattern,
      fixed_cycle: activeDistrict.default_params.fixed_cycle,
      service_rate: activeDistrict.default_params.service_rate,
      emergency_rate: activeDistrict.default_params.emergency_rate,
    }));
  }, [activeDistrict]);


  const chartLabels = useMemo(() => {
    if (!result?.time_series?.rl?.queue) {
      return [];
    }
    return result.time_series.rl.queue.map((_: number, index: number) => String(index + 1));
  }, [result]);

  const throughputSeries = useMemo(() => {
    if (!result?.time_series?.rl?.throughput) {
      return [];
    }
    let running = 0;
    return result.time_series.rl.throughput.map((value: number) => {
      running += value;
      return running;
    });
  }, [result]);

  const network = result?.district?.network ?? activeDistrict?.network;
  const benchmark = (result?.benchmark ?? {}) as {
    actual?: Record<string, number>;
    rl_vs_actual_pct?: Record<string, number>;
    fixed_vs_actual_pct?: Record<string, number>;
  };
  const trainingRewards =
    ((result?.training as { moving_avg_rewards?: number[] } | undefined)?.moving_avg_rewards ?? []) as number[];
  const activeWave = (() => {
    const series = result?.time_series?.rl;
    if (!series?.active_mode?.length) {
      return null;
    }
    return series.active_mode[series.active_mode.length - 1] ?? null;
  })();


  function updateForm<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setStatus("Training RL agent and evaluating baseline...");

    try {
      const payload = {
        ...form,
        actual_avg_wait: form.actual_avg_wait === "" ? null : Number(form.actual_avg_wait),
        actual_avg_queue: form.actual_avg_queue === "" ? null : Number(form.actual_avg_queue),
        actual_throughput: form.actual_throughput === "" ? null : Number(form.actual_throughput),
        actual_emergency_avg_wait:
          form.actual_emergency_avg_wait === "" ? null : Number(form.actual_emergency_avg_wait),
        actual_clearance_ratio:
          form.actual_clearance_ratio === "" ? null : Number(form.actual_clearance_ratio),
      };

      const data = await runSimulation(payload);
      setResult(data);
      setStatus(`Completed for ${data.district.name}. Model size: ${data.training.model_label}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Simulation failed.";
      setStatus(message);
    } finally {
      setLoading(false);
    }
  }

  async function savePreset() {
    if (!presetName.trim()) {
      setStatus("Preset name is required.");
      return;
    }

    try {
      await createPreset({
        name: presetName,
        description: presetDescription,
        config: {
          ...form,
          actual_avg_wait: form.actual_avg_wait === "" ? null : Number(form.actual_avg_wait),
          actual_avg_queue: form.actual_avg_queue === "" ? null : Number(form.actual_avg_queue),
          actual_throughput: form.actual_throughput === "" ? null : Number(form.actual_throughput),
          actual_emergency_avg_wait:
            form.actual_emergency_avg_wait === "" ? null : Number(form.actual_emergency_avg_wait),
          actual_clearance_ratio:
            form.actual_clearance_ratio === "" ? null : Number(form.actual_clearance_ratio),
        },
      });
      setPresetName("");
      setPresetDescription("");
      setStatus("Preset saved.");
      refetch();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Preset save failed.";
      setStatus(message);
    }
  }

  function applyPreset(preset: any) {
    const config = preset.config ?? {};
    setForm((current) => ({
      ...current,
      ...config,
      actual_avg_wait: config.actual_avg_wait ?? "",
      actual_avg_queue: config.actual_avg_queue ?? "",
      actual_throughput: config.actual_throughput ?? "",
      actual_emergency_avg_wait: config.actual_emergency_avg_wait ?? "",
      actual_clearance_ratio: config.actual_clearance_ratio ?? "",
    }));
  }

  function applyTemplate(template: any) {
    const config = template.config ?? {};
    setForm((current) => ({
      ...current,
      ...config,
      actual_avg_wait: config.actual_avg_wait ?? "",
      actual_avg_queue: config.actual_avg_queue ?? "",
      actual_throughput: config.actual_throughput ?? "",
      actual_emergency_avg_wait: config.actual_emergency_avg_wait ?? "",
      actual_clearance_ratio: config.actual_clearance_ratio ?? "",
    }));
    setStatus(`Template "${template.name}" loaded.`);
  }

  return (
    <div className="space-y-6">
      <section className="panel p-6 enter">
        <p className="eyebrow">Simulation Lab</p>
        <h2 className="text-2xl font-semibold">Run RL Experiments</h2>
        <p className="mt-2 text-sm text-muted">
          Tune algorithms, compare against fixed timing, and benchmark against actual district flow.
        </p>
      </section>

      <section className="panel p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="eyebrow">Presets</p>
            <h3 className="text-lg font-semibold">Scenario Library</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {(presetsData?.presets ?? []).map((preset) => (
              <Button
                key={preset.preset_id}
                variant="outline"
                size="sm"
                type="button"
                onClick={() => applyPreset(preset)}
              >
                {preset.name}
              </Button>
            ))}
          </div>
        </div>
      </section>

      <section className="panel p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="eyebrow">Templates</p>
            <h3 className="text-lg font-semibold">Citywide Playbooks</h3>
            <p className="text-sm text-muted mt-1">
              One-click parameter baselines for rush hours, events, and emergency clearance.
            </p>
          </div>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {(templatesData?.templates ?? []).map((template) => (
            <Card key={template.template_id} className="hover-lift">
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-semibold">{template.name}</h4>
                    <p className="mt-1 text-xs text-muted">{template.description}</p>
                  </div>
                  <Button variant="outline" size="sm" type="button" onClick={() => applyTemplate(template)}>
                    Apply
                  </Button>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-[0.7rem] text-muted">
                  {Object.entries(template.config ?? {}).slice(0, 4).map(([key, value]) => (
                    <Badge key={key} variant="neutral">
                      {key.replace(/_/g, " ")}: {String(value)}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="panel p-6">
        <form className="grid gap-4 md:grid-cols-3" onSubmit={handleSubmit}>
          <label className="text-xs text-muted">
            Algorithm
            <Select value={form.algorithm} onValueChange={(value) => updateForm("algorithm", value)}>
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {algorithms.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </label>
          <label className="text-xs text-muted">
            Backend
            <Select value={form.backend} onValueChange={(value) => updateForm("backend", value)}>
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {backends.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </label>
          <label className="text-xs text-muted">
            Traffic Pattern
            <Select
              value={form.traffic_pattern}
              onValueChange={(value) => updateForm("traffic_pattern", value)}
            >
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {trafficPatterns.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </label>

          <label className="text-xs text-muted">
            Episodes
            <Input
              type="number"
              className="mt-1"
              value={form.episodes}
              onChange={(event) => updateForm("episodes", Number(event.target.value))}
            />
          </label>
          <label className="text-xs text-muted">
            Steps Per Episode
            <Input
              type="number"
              className="mt-1"
              value={form.steps_per_episode}
              onChange={(event) => updateForm("steps_per_episode", Number(event.target.value))}
            />
          </label>
          <label className="text-xs text-muted">
            Fixed Cycle
            <Input
              type="number"
              className="mt-1"
              value={form.fixed_cycle}
              onChange={(event) => updateForm("fixed_cycle", Number(event.target.value))}
            />
          </label>

          <label className="text-xs text-muted">
            Service Rate
            <Input
              type="number"
              className="mt-1"
              value={form.service_rate}
              onChange={(event) => updateForm("service_rate", Number(event.target.value))}
            />
          </label>
          <label className="text-xs text-muted">
            Emergency Rate
            <Input
              type="number"
              step="0.01"
              className="mt-1"
              value={form.emergency_rate}
              onChange={(event) => updateForm("emergency_rate", Number(event.target.value))}
            />
          </label>
          <label className="text-xs text-muted">
            Learning Rate
            <Input
              type="number"
              step="0.01"
              className="mt-1"
              value={form.learning_rate}
              onChange={(event) => updateForm("learning_rate", Number(event.target.value))}
            />
          </label>

          <label className="text-xs text-muted">
            Discount Factor
            <Input
              type="number"
              step="0.001"
              className="mt-1"
              value={form.discount_factor}
              onChange={(event) => updateForm("discount_factor", Number(event.target.value))}
            />
          </label>
          <label className="text-xs text-muted">
            Epsilon Start
            <Input
              type="number"
              step="0.01"
              className="mt-1"
              value={form.epsilon_start}
              onChange={(event) => updateForm("epsilon_start", Number(event.target.value))}
            />
          </label>
          <label className="text-xs text-muted">
            Epsilon Min
            <Input
              type="number"
              step="0.01"
              className="mt-1"
              value={form.epsilon_min}
              onChange={(event) => updateForm("epsilon_min", Number(event.target.value))}
            />
          </label>
          <label className="text-xs text-muted">
            Epsilon Decay
            <Input
              type="number"
              step="0.0001"
              className="mt-1"
              value={form.epsilon_decay}
              onChange={(event) => updateForm("epsilon_decay", Number(event.target.value))}
            />
          </label>
          <label className="text-xs text-muted">
            Switch Penalty
            <Input
              type="number"
              step="0.1"
              className="mt-1"
              value={form.switch_penalty}
              onChange={(event) => updateForm("switch_penalty", Number(event.target.value))}
            />
          </label>

          <label className="text-xs text-muted">
            Random Seed
            <Input
              type="number"
              className="mt-1"
              value={form.seed}
              onChange={(event) => updateForm("seed", Number(event.target.value))}
            />
          </label>
          <label className="text-xs text-muted">
            Actual Avg Wait
            <Input
              type="number"
              step="0.1"
              className="mt-1"
              value={form.actual_avg_wait}
              onChange={(event) => updateForm("actual_avg_wait", event.target.value)}
            />
          </label>
          <label className="text-xs text-muted">
            Actual Avg Queue
            <Input
              type="number"
              step="0.1"
              className="mt-1"
              value={form.actual_avg_queue}
              onChange={(event) => updateForm("actual_avg_queue", event.target.value)}
            />
          </label>

          <label className="text-xs text-muted">
            Actual Throughput
            <Input
              type="number"
              step="1"
              className="mt-1"
              value={form.actual_throughput}
              onChange={(event) => updateForm("actual_throughput", event.target.value)}
            />
          </label>
          <label className="text-xs text-muted">
            Actual Emergency Wait
            <Input
              type="number"
              step="0.1"
              className="mt-1"
              value={form.actual_emergency_avg_wait}
              onChange={(event) => updateForm("actual_emergency_avg_wait", event.target.value)}
            />
          </label>
          <label className="text-xs text-muted">
            Actual Clearance Ratio
            <Input
              type="number"
              step="0.01"
              className="mt-1"
              value={form.actual_clearance_ratio}
              onChange={(event) => updateForm("actual_clearance_ratio", event.target.value)}
            />
          </label>

          <div className="flex items-end gap-2">
            <Button className="w-full" type="submit" disabled={loading}>
              {loading ? "Running..." : "Run Simulation"}
            </Button>
          </div>
        </form>

        <p className="mt-4 text-sm text-muted">{status}</p>
      </section>

      <section className="panel p-6">
        <div className="flex flex-wrap items-center gap-3">
          <Input
            className="flex-1"
            placeholder="Preset name"
            value={presetName}
            onChange={(event) => setPresetName(event.target.value)}
          />
          <Input
            className="flex-1"
            placeholder="Description"
            value={presetDescription}
            onChange={(event) => setPresetDescription(event.target.value)}
          />
          <Button variant="outline" type="button" onClick={savePreset}>
            Save Preset
          </Button>
        </div>
      </section>

      <section className="panel p-6">
        <div className="section-head">
          <p className="eyebrow">Network Coordination</p>
          <h3 className="text-lg font-semibold">Signal Wave Overview</h3>
          <p className="text-sm text-muted mt-1">
            Inspect how many intersections are coordinated and which signal wave is dominant.
          </p>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <div className="rounded-xl border border-border bg-surface p-4 shadow-soft hover-lift">
            <p className="text-xs font-medium text-muted">Intersections</p>
            <p className="mt-2 text-lg font-semibold">{formatNumber((network as any)?.intersection_count)}</p>
          </div>
          <div className="rounded-xl border border-border bg-surface p-4 shadow-soft hover-lift">
            <p className="text-xs font-medium text-muted">Corridors</p>
            <p className="mt-2 text-lg font-semibold">{formatNumber((network as any)?.corridor_count)}</p>
          </div>
          <div className="rounded-xl border border-border bg-surface p-4 shadow-soft hover-lift">
            <p className="text-xs font-medium text-muted">Boundary Nodes</p>
            <p className="mt-2 text-lg font-semibold">{formatNumber((network as any)?.boundary_nodes?.length)}</p>
          </div>
          <div className="rounded-xl border border-border bg-surface p-4 shadow-soft hover-lift">
            <p className="text-xs font-medium text-muted">Active Wave</p>
            <p className="mt-2 text-lg font-semibold">
              {activeWave === null || activeWave === undefined
                ? "Awaiting run"
                : activeWave === 0
                  ? "NS Priority"
                  : "EW Priority"}
            </p>
          </div>
        </div>
      </section>

      {result ? (
        <>
          <section className="grid gap-4 md:grid-cols-5">
            <StatCard
              label="Wait Improvement"
              value={formatPercent(result.comparison.improvements.avg_wait_pct)}
              helper="vs fixed timing"
            />
            <StatCard
              label="Queue Reduction"
              value={formatPercent(result.comparison.improvements.avg_queue_pct)}
              helper="vs fixed timing"
            />
            <StatCard
              label="Throughput Gain"
              value={formatPercent(result.comparison.improvements.throughput_pct)}
              helper="vs fixed timing"
            />
            <StatCard
              label="RL vs Actual Wait"
              value={formatPercent(benchmark.rl_vs_actual_pct?.avg_wait_pct)}
              helper="benchmark delta"
            />
            <StatCard
              label="Busiest Queue"
              value={formatNumber(result.comparison.rl.busiest_intersection_queue)}
              helper="peak intersection"
            />
          </section>

          <section className="grid gap-6 lg:grid-cols-3">
            <ChartCard
              title="Queue Pressure"
              labels={chartLabels}
              datasets={[
                {
                  label: "RL Queue",
                  data: result.time_series.rl.queue ?? [],
                  borderColor: "#2563eb",
                  backgroundColor: "rgba(37, 99, 235, 0.14)",
                },
                {
                  label: "Fixed Queue",
                  data: result.time_series.fixed.queue ?? [],
                  borderColor: "#f38020",
                  backgroundColor: "rgba(243, 128, 32, 0.18)",
                },
              ]}
            />
            <ChartCard
              title="Cumulative Throughput"
              labels={chartLabels}
              datasets={[
                {
                  label: "RL Throughput",
                  data: throughputSeries,
                  borderColor: "#0ea5e9",
                  backgroundColor: "rgba(14, 165, 233, 0.18)",
                },
              ]}
            />
            <ChartCard
              title="Training Rewards"
              labels={trainingRewards.map((_: number, idx: number) => String(idx + 1))}
              datasets={[
                {
                  label: "Reward (moving avg)",
                  data: trainingRewards,
                  borderColor: "#2563eb",
                  backgroundColor: "rgba(37, 99, 235, 0.14)",
                },
              ]}
            />
          </section>

          <section className="grid gap-6 lg:grid-cols-2">
            <div className="panel p-6">
              <h3 className="text-lg font-semibold">RL Controller vs Fixed Timer</h3>
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="text-xs font-semibold text-muted">
                    <tr>
                      <th className="py-2 text-left">Metric</th>
                      <th className="py-2 text-left">RL</th>
                      <th className="py-2 text-left">Fixed</th>
                      <th className="py-2 text-left">Delta</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(result.comparison.rl).map(([key, value]) => (
                      <tr key={key} className="border-t border-border/60">
                        <td className="py-2 capitalize">{key.replace(/_/g, " ")}</td>
                        <td className="py-2">{formatNumber(value)}</td>
                        <td className="py-2">{formatNumber(result.comparison.fixed[key])}</td>
                        <td className="py-2">{formatPercent(result.comparison.improvements[`${key}_pct`])}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="panel p-6">
              <h3 className="text-lg font-semibold">Benchmark vs Actual</h3>
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="text-xs font-semibold text-muted">
                    <tr>
                      <th className="py-2 text-left">Metric</th>
                      <th className="py-2 text-left">Actual</th>
                      <th className="py-2 text-left">RL vs Actual</th>
                      <th className="py-2 text-left">Fixed vs Actual</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(benchmark.actual ?? {}).map(([key, value]) => (
                      <tr key={key} className="border-t border-border/60">
                        <td className="py-2 capitalize">{key.replace(/_/g, " ")}</td>
                        <td className="py-2">{formatNumber(value as number)}</td>
                        <td className="py-2">{formatPercent(benchmark.rl_vs_actual_pct?.[`${key}_pct`])}</td>
                        <td className="py-2">{formatPercent(benchmark.fixed_vs_actual_pct?.[`${key}_pct`])}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
