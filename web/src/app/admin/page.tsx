"use client";

import { useQuery } from "@tanstack/react-query";

import {
  approveRun,
  getActivity,
  getAudit,
  getPresets,
  getRuns,
  rejectRun,
} from "@/lib/api/client";
import { formatDate } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const roles = [
  { role: "Operator", access: "Run simulations, view dashboards" },
  { role: "Analyst", access: "Deep reports, benchmarking" },
  { role: "Manager", access: "Approve changes, export reports" },
  { role: "Admin", access: "Roles, presets, audit logs" },
];

export default function AdminPage() {
  const { data: presetsData } = useQuery({ queryKey: ["presets"], queryFn: getPresets });
  const { data: runsData, refetch: refetchRuns } = useQuery({
    queryKey: ["runs", "pending"],
    queryFn: () => getRuns({ limit: 10, status: "pending" }),
  });
  const { data: auditData } = useQuery({ queryKey: ["audit"], queryFn: getAudit });
  const { data: activityData } = useQuery({ queryKey: ["activity"], queryFn: getActivity });

  async function handleApprove(runId: string) {
    await approveRun(runId);
    refetchRuns();
  }

  async function handleReject(runId: string) {
    await rejectRun(runId);
    refetchRuns();
  }

  return (
    <div className="space-y-6">
      <section className="panel p-6 enter">
        <p className="eyebrow">Admin</p>
        <h2 className="text-2xl font-semibold">Operations Governance</h2>
        <p className="mt-2 text-sm text-muted">Controls for roles, auditing, approvals, and scenario policy.</p>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="panel p-6">
          <h3 className="text-lg font-semibold">Roles & Permissions</h3>
          <div className="mt-4 space-y-3">
            {roles.map((role) => (
              <div key={role.role} className="rounded-xl border border-border bg-surface-2 p-3 shadow-soft">
                <div className="flex items-center justify-between">
                  <p className="font-semibold">{role.role}</p>
                  <Badge variant="info">RBAC</Badge>
                </div>
                <p className="text-sm text-muted mt-1">{role.access}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="panel p-6">
          <h3 className="text-lg font-semibold">Run Approval Queue</h3>
          <div className="mt-4 space-y-3">
            {(runsData?.runs ?? []).map((run) => (
              <div key={run.run_id} className="rounded-xl border border-border bg-surface-2 p-3 shadow-soft">
                <p className="font-semibold">{run.district_name}</p>
                <p className="text-sm text-muted">Created {formatDate(run.created_at)}</p>
                <div className="mt-2 flex gap-2">
                  <Button size="sm" onClick={() => handleApprove(run.run_id)} type="button">
                    Approve
                  </Button>
                  <Button variant="destructive" size="sm" onClick={() => handleReject(run.run_id)} type="button">
                    Reject
                  </Button>
                </div>
              </div>
            ))}
            {(runsData?.runs ?? []).length === 0 && (
              <p className="text-sm text-muted">No runs awaiting approval.</p>
            )}
          </div>
        </div>
      </section>

      <section className="panel p-6">
        <h3 className="text-lg font-semibold">Scenario Library</h3>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {(presetsData?.presets ?? []).map((preset) => (
            <div key={preset.preset_id} className="rounded-xl border border-border bg-surface-2 p-4 shadow-soft">
              <p className="font-semibold">{preset.name}</p>
              <p className="mt-2 text-sm text-muted">{preset.description || "No description"}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="panel p-6">
          <h3 className="text-lg font-semibold">Audit Log</h3>
          <div className="mt-4 space-y-3">
            {(auditData?.entries ?? []).map((entry: any) => (
              <div key={entry.id} className="rounded-xl border border-border bg-surface-2 p-3 shadow-soft">
                <p className="font-semibold">{entry.action}</p>
                <p className="text-sm text-muted">{formatDate(entry.created_at)}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="panel p-6">
          <h3 className="text-lg font-semibold">Activity Feed</h3>
          <div className="mt-4 space-y-3">
            {(activityData?.events ?? []).map((entry: any) => (
              <div key={entry.id} className="rounded-xl border border-border bg-surface-2 p-3 shadow-soft">
                <p className="font-semibold">{entry.message}</p>
                <p className="text-sm text-muted">{formatDate(entry.created_at)}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
