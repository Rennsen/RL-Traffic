import type { Alert } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

const severityStyles: Record<string, string> = {
  low: "border-success/30 bg-success/10",
  medium: "border-warning/30 bg-warning/10",
  high: "border-danger/30 bg-danger/10",
};

export function AlertCard({ alert }: { alert: Alert }) {
  return (
    <div
      className={`rounded-xl border p-4 shadow-soft hover-lift ${severityStyles[alert.severity] ?? "border-border bg-surface"}`}
    >
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-ink">{alert.title}</p>
        <Badge variant={alert.severity === "high" ? "danger" : alert.severity === "medium" ? "warning" : "success"}>
          {alert.severity}
        </Badge>
      </div>
      <p className="mt-2 text-sm text-muted">{alert.message}</p>
      <p className="mono mt-3 text-muted">
        {alert.metric}: {alert.value.toFixed(2)} (threshold {alert.threshold})
      </p>
    </div>
  );
}
