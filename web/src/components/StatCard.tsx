interface StatCardProps {
  label: string;
  value: string | number;
  helper?: string;
}

export function StatCard({ label, value, helper }: StatCardProps) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4 shadow-soft hover-lift">
      <p className="text-xs font-medium text-muted">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-ink">
        <span className="bg-gradient-to-r from-accent to-accent-2 bg-clip-text text-transparent">
          {value}
        </span>
      </p>
      {helper ? <p className="mono mt-2 text-muted">{helper}</p> : null}
    </div>
  );
}
