"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  addDistrictNote,
  getDistrictNotes,
  getDistrictTargets,
  getRuns,
  updateDistrictSettings,
  updateDistrictTargets,
} from "@/lib/api/client";
import { useDistricts } from "@/lib/district-context";
import { formatDate, formatNumber } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export default function DistrictsPage() {
  const { districts, activeDistrictId } = useDistricts();
  const activeDistrict = districts.find((district) => district.district_id === activeDistrictId) ?? null;

  const { data: runsData, refetch: refetchRuns } = useQuery({
    queryKey: ["runs", activeDistrictId],
    queryFn: () => getRuns({ district_id: activeDistrictId ?? undefined, limit: 8 }),
    enabled: !!activeDistrictId,
  });
  const { data: allRunsData } = useQuery({
    queryKey: ["runs", "all"],
    queryFn: () => getRuns({ limit: 50 }),
  });

  const { data: notesData, refetch: refetchNotes } = useQuery({
    queryKey: ["notes", activeDistrictId],
    queryFn: () => getDistrictNotes(activeDistrictId ?? ""),
    enabled: !!activeDistrictId,
  });

  const { data: targetsData, refetch: refetchTargets } = useQuery({
    queryKey: ["targets", activeDistrictId],
    queryFn: () => getDistrictTargets(activeDistrictId ?? ""),
    enabled: !!activeDistrictId,
  });

  const [settings, setSettings] = useState({
    fixed_cycle: activeDistrict?.default_params.fixed_cycle ?? 16,
    service_rate: activeDistrict?.default_params.service_rate ?? 3,
    emergency_rate: activeDistrict?.default_params.emergency_rate ?? 0.02,
    actual_avg_wait: activeDistrict?.actual_metrics.avg_wait ?? 0,
    actual_avg_queue: activeDistrict?.actual_metrics.avg_queue ?? 0,
    actual_throughput: activeDistrict?.actual_metrics.throughput ?? 0,
    actual_emergency_avg_wait: activeDistrict?.actual_metrics.emergency_avg_wait ?? 0,
    actual_clearance_ratio: activeDistrict?.actual_metrics.clearance_ratio ?? 0.7,
  });

  const [noteText, setNoteText] = useState("");
  const [targetForm, setTargetForm] = useState({
    avg_wait: targetsData?.targets?.avg_wait ?? 50,
    avg_queue: targetsData?.targets?.avg_queue ?? 200,
    throughput: targetsData?.targets?.throughput ?? 1000,
  });

  useEffect(() => {
    if (!activeDistrict) {
      return;
    }
    setSettings({
      fixed_cycle: activeDistrict.default_params.fixed_cycle,
      service_rate: activeDistrict.default_params.service_rate,
      emergency_rate: activeDistrict.default_params.emergency_rate,
      actual_avg_wait: activeDistrict.actual_metrics.avg_wait ?? 0,
      actual_avg_queue: activeDistrict.actual_metrics.avg_queue ?? 0,
      actual_throughput: activeDistrict.actual_metrics.throughput ?? 0,
      actual_emergency_avg_wait: activeDistrict.actual_metrics.emergency_avg_wait ?? 0,
      actual_clearance_ratio: activeDistrict.actual_metrics.clearance_ratio ?? 0.7,
    });
  }, [activeDistrict]);

  useEffect(() => {
    if (!targetsData?.targets) {
      return;
    }
    setTargetForm({
      avg_wait: targetsData.targets.avg_wait ?? 50,
      avg_queue: targetsData.targets.avg_queue ?? 200,
      throughput: targetsData.targets.throughput ?? 1000,
    });
  }, [targetsData]);

  const districtComparison = useMemo(() => {
    const latestRuns = allRunsData?.runs ?? [];
    const map = new Map<string, any>();
    for (const run of latestRuns) {
      if (!map.has(run.district_id)) {
        map.set(run.district_id, run);
      }
    }
    return Array.from(map.values());
  }, [allRunsData]);

  async function saveSettings() {
    if (!activeDistrictId) {
      return;
    }
    await updateDistrictSettings(activeDistrictId, {
      default_params: {
        fixed_cycle: settings.fixed_cycle,
        service_rate: settings.service_rate,
        emergency_rate: settings.emergency_rate,
      },
      benchmark_overrides: {
        avg_wait: settings.actual_avg_wait,
        avg_queue: settings.actual_avg_queue,
        throughput: settings.actual_throughput,
        emergency_avg_wait: settings.actual_emergency_avg_wait,
        clearance_ratio: settings.actual_clearance_ratio,
      },
    });
    refetchRuns();
  }

  async function saveNote() {
    if (!activeDistrictId || !noteText.trim()) {
      return;
    }
    await addDistrictNote(activeDistrictId, { note: noteText });
    setNoteText("");
    refetchNotes();
  }

  async function saveTargets() {
    if (!activeDistrictId) {
      return;
    }
    await updateDistrictTargets(activeDistrictId, { targets: targetForm });
    refetchTargets();
  }

  return (
    <div className="space-y-6">
      <section className="panel p-6 enter">
        <p className="eyebrow">Districts</p>
        <h2 className="text-2xl font-semibold">Management & Ownership</h2>
        <p className="mt-2 text-sm text-muted">
          Track district health, owners, and the latest optimization performance across the city.
        </p>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        {districts.map((district) => (
          <div key={district.district_id} className="panel p-5 hover-lift">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">{district.name}</h3>
              <Badge variant="info">{district.traffic_pattern}</Badge>
            </div>
            <p className="mt-2 text-sm text-muted">{district.description}</p>
            <div className="mt-4 space-y-1 text-sm text-ink">
              <p><span className="text-muted">Owner:</span> {district.manager.owner}</p>
              <p><span className="text-muted">Team:</span> {district.manager.team}</p>
              <p><span className="text-muted">Contact:</span> {district.manager.contact}</p>
            </div>
            <div className="mt-4 rounded-xl border border-border bg-surface-2 p-3 text-xs text-muted">
              Default cycle {district.default_params.fixed_cycle} · Service rate {district.default_params.service_rate} ·
              Emergency {district.default_params.emergency_rate}
            </div>
          </div>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="panel p-6">
          <h3 className="text-lg font-semibold">District Settings</h3>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {[
              { label: "Fixed Cycle", key: "fixed_cycle" },
              { label: "Service Rate", key: "service_rate" },
              { label: "Emergency Rate", key: "emergency_rate" },
              { label: "Actual Avg Wait", key: "actual_avg_wait" },
              { label: "Actual Avg Queue", key: "actual_avg_queue" },
              { label: "Actual Throughput", key: "actual_throughput" },
              { label: "Actual Emergency Wait", key: "actual_emergency_avg_wait" },
              { label: "Actual Clearance Ratio", key: "actual_clearance_ratio" },
            ].map((field) => (
              <label key={field.key} className="text-xs text-muted">
                {field.label}
                <Input
                  className="mt-1"
                  value={(settings as any)[field.key] ?? ""}
                  onChange={(event) =>
                    setSettings((current) => ({ ...current, [field.key]: Number(event.target.value) }))
                  }
                />
              </label>
            ))}
          </div>
          <Button className="mt-4" type="button" onClick={saveSettings} disabled={!activeDistrictId}>
            Save Settings
          </Button>
        </div>

        <div className="panel p-6">
          <h3 className="text-lg font-semibold">Performance Targets</h3>
          <div className="mt-4 grid gap-3">
            {[
              { label: "Avg Wait Target", key: "avg_wait" },
              { label: "Avg Queue Target", key: "avg_queue" },
              { label: "Throughput Target", key: "throughput" },
            ].map((field) => (
              <label key={field.key} className="text-xs text-muted">
                {field.label}
                <Input
                  className="mt-1"
                  value={(targetForm as any)[field.key] ?? ""}
                  onChange={(event) =>
                    setTargetForm((current) => ({ ...current, [field.key]: Number(event.target.value) }))
                  }
                />
              </label>
            ))}
          </div>
          <Button variant="outline" className="mt-4" type="button" onClick={saveTargets} disabled={!activeDistrictId}>
            Update Targets
          </Button>
        </div>
      </section>

      <section className="panel p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="eyebrow">Run History</p>
            <h3 className="text-lg font-semibold">Latest simulations</h3>
          </div>
          <span className="mono">{runsData?.runs.length ?? 0} runs</span>
        </div>

        <div className="mt-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Run ID</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Avg Wait</TableHead>
                <TableHead>Avg Queue</TableHead>
                <TableHead>Throughput</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(runsData?.runs ?? []).map((run) => (
                <TableRow key={run.run_id}>
                  <TableCell className="font-mono text-xs">{run.run_id.slice(0, 8)}</TableCell>
                  <TableCell>{formatDate(run.created_at)}</TableCell>
                  <TableCell>{formatNumber(run.avg_wait)}</TableCell>
                  <TableCell>{formatNumber(run.avg_queue)}</TableCell>
                  <TableCell>{formatNumber(run.throughput, 0)}</TableCell>
                </TableRow>
              ))}
              {(runsData?.runs ?? []).length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="py-6 text-center text-sm text-muted">
                    No runs yet. Kick off a new simulation in the Simulation Lab.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </section>

      <section className="panel p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="eyebrow">Notes</p>
            <h3 className="text-lg font-semibold">District Notes & Annotations</h3>
          </div>
          <span className="mono">{notesData?.notes?.length ?? 0} notes</span>
        </div>
        <div className="mt-4 space-y-3">
          {(notesData?.notes ?? []).map((note) => (
            <div key={note.id} className="rounded-xl border border-border bg-surface-2 p-3 text-sm shadow-soft">
              <p>{note.note}</p>
              <p className="mono mt-2">{formatDate(note.created_at)}</p>
            </div>
          ))}
          {(notesData?.notes ?? []).length === 0 && (
            <p className="text-sm text-muted">No notes yet.</p>
          )}
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Input
            className="flex-1"
            placeholder="Add a note..."
            value={noteText}
            onChange={(event) => setNoteText(event.target.value)}
          />
          <Button type="button" onClick={saveNote} disabled={!activeDistrictId}>
            Add Note
          </Button>
        </div>
      </section>

      <section className="panel p-6">
        <h3 className="text-lg font-semibold">District Comparison</h3>
        <div className="mt-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>District</TableHead>
                <TableHead>Wait Gain</TableHead>
                <TableHead>Throughput Gain</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {districtComparison.map((run) => (
                <TableRow key={run.run_id}>
                  <TableCell>{run.district_name}</TableCell>
                  <TableCell>{formatNumber(run.improvements?.avg_wait_pct)}</TableCell>
                  <TableCell>{formatNumber(run.improvements?.throughput_pct)}</TableCell>
                </TableRow>
              ))}
              {districtComparison.length === 0 && (
                <TableRow>
                  <TableCell colSpan={3} className="py-6 text-center text-sm text-muted">
                    Run simulations to populate comparisons.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </section>
    </div>
  );
}
