import * as React from "react";

import { cn } from "@/lib/utils";

interface TabsProps {
  tabs: Array<{ value: string; label: string }>;
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

export function Tabs({ tabs, value, onChange, className }: TabsProps) {
  return (
    <div className={cn("inline-flex rounded-full border border-border bg-surface-2 p-1", className)}>
      {tabs.map((tab) => {
        const active = tab.value === value;
        return (
          <button
            key={tab.value}
            className={cn(
              "rounded-full px-3 py-1.5 text-xs font-semibold transition",
              active
                ? "bg-surface text-ink shadow-soft border border-border"
                : "text-muted hover:text-ink",
            )}
            type="button"
            onClick={() => onChange(tab.value)}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
