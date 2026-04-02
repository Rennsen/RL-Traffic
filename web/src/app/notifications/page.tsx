"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getAlerts, getNotifications } from "@/lib/api/client";
import { useDistricts } from "@/lib/district-context";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const severityTone: Record<string, string> = {
  high: "border-danger/30 bg-danger/10 text-danger",
  medium: "border-warning/30 bg-warning/10 text-warning",
  low: "border-success/30 bg-success/10 text-success",
};

function formatTimestamp(value?: string) {
  if (!value) return "";
  const date = new Date(value);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export default function NotificationsPage() {
  const { districts } = useDistricts();
  const { data } = useQuery({ queryKey: ["notifications"], queryFn: getNotifications });
  const { data: alertsData } = useQuery({ queryKey: ["alerts"], queryFn: getAlerts });

  const [severityFilter, setSeverityFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [acknowledged, setAcknowledged] = useState<Record<string, boolean>>({});

  const districtLookup = useMemo(() => {
    return new Map(districts.map((district) => [district.district_id, district.name]));
  }, [districts]);

  const notifications = useMemo(() => {
    const list = data?.notifications ?? [];
    return list.filter((item) => {
      if (severityFilter !== "all" && item.severity !== severityFilter) return false;
      if (categoryFilter !== "all" && item.category !== categoryFilter) return false;
      return true;
    });
  }, [data, severityFilter, categoryFilter]);

  const stats = useMemo(() => {
    const list = data?.notifications ?? [];
    return {
      total: list.length,
      high: list.filter((item) => item.severity === "high").length,
      medium: list.filter((item) => item.severity === "medium").length,
      low: list.filter((item) => item.severity === "low").length,
    };
  }, [data]);

  const categories = useMemo(() => {
    const list = data?.notifications ?? [];
    return Array.from(new Set(list.map((item) => item.category)));
  }, [data]);

  return (
    <div className="space-y-6">
      <section className="panel p-6 enter">
        <p className="eyebrow">Ops Center</p>
        <h2 className="text-2xl font-semibold">Notification Center</h2>
        <p className="mt-2 text-sm text-muted">
          Track congestion spikes, approvals, and field events in one unified feed.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        {[
          { label: "Total", value: stats.total },
          { label: "High", value: stats.high },
          { label: "Medium", value: stats.medium },
          { label: "Low", value: stats.low },
        ].map((item) => (
          <div key={item.label} className="panel p-4 hover-lift">
            <p className="text-xs font-medium text-muted">{item.label}</p>
            <p className="mt-2 text-2xl font-semibold">{item.value}</p>
          </div>
        ))}
      </section>

      <section className="panel p-6">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-xs text-muted">
            Severity
            <Select value={severityFilter} onValueChange={setSeverityFilter}>
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="low">Low</SelectItem>
              </SelectContent>
            </Select>
          </label>
          <label className="text-xs text-muted">
            Category
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                {categories.map((category) => (
                  <SelectItem key={category} value={category}>
                    {category.replace(/_/g, " ")}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </label>
          <div className="ml-auto text-xs text-muted">
            {notifications.length} active messages
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[2fr,1fr]">
        <div className="space-y-3">
          {notifications.map((item) => (
            <div key={item.notification_id} className="panel p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge className={`border ${severityTone[item.severity] ?? ""}`} variant="neutral">
                      {item.severity}
                    </Badge>
                    <Badge variant="info">{item.category.replace(/_/g, " ")}</Badge>
                    {item.district_id ? (
                      <span className="text-xs text-muted">
                        {districtLookup.get(item.district_id) ?? item.district_id}
                      </span>
                    ) : null}
                  </div>
                  <h3 className="mt-2 text-sm font-semibold">{item.title}</h3>
                  <p className="mt-1 text-xs text-muted">{item.message}</p>
                </div>
                <div className="text-right">
                  <div className="mono">{formatTimestamp(item.created_at)}</div>
                  <Button
                    variant="outline"
                    size="sm"
                    type="button"
                    onClick={() =>
                      setAcknowledged((current) => ({
                        ...current,
                        [item.notification_id]: !current[item.notification_id],
                      }))
                    }
                  >
                    {acknowledged[item.notification_id] ? "Unmark" : "Acknowledge"}
                  </Button>
                </div>
              </div>
              {acknowledged[item.notification_id] ? (
                <div className="mt-3 text-[0.7rem] text-success">
                  Acknowledged by on-call operator.
                </div>
              ) : null}
            </div>
          ))}
        </div>

        <div className="space-y-4">
          <div className="panel p-4">
            <p className="eyebrow">Live Alerts</p>
            <h3 className="text-sm font-semibold">Active Escalations</h3>
            <div className="mt-3 space-y-2">
              {(alertsData?.alerts ?? []).slice(0, 5).map((alert) => (
                <div key={alert.alert_id} className="rounded-xl border border-border bg-surface-2 p-3 shadow-soft">
                  <div className="text-xs font-semibold text-ink/80">{alert.title}</div>
                  <div className="text-[0.7rem] text-muted">{alert.message}</div>
                </div>
              ))}
              {alertsData?.alerts?.length ? null : (
                <p className="text-xs text-muted">No live alerts right now.</p>
              )}
            </div>
          </div>

          <div className="panel p-4">
            <p className="eyebrow">Runbooks</p>
            <h3 className="text-sm font-semibold">Rapid Response</h3>
            <ul className="mt-3 space-y-2 text-xs text-muted">
              <li>Trigger emergency corridor template for high queue spikes.</li>
              <li>Escalate to city coordinator after 2x clearance drop.</li>
              <li>Notify transit priority when queue exceeds 300 vehicles.</li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
