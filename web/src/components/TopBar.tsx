"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bell, FlaskConical, LogIn, LogOut, Moon, PlayCircle, Sun } from "lucide-react";

import { getCurrentUser } from "@/lib/api/client";
import { useDistricts } from "@/lib/district-context";
import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export function TopBar() {
  const { districts, activeDistrictId, setActiveDistrictId, isLoading } = useDistricts();
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: getCurrentUser });
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    const stored = window.localStorage.getItem("theme") as "light" | "dark" | null;
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const nextTheme = stored ?? (prefersDark ? "dark" : "light");
    setTheme(nextTheme);
    document.documentElement.classList.toggle("dark", nextTheme === "dark");
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    document.documentElement.classList.toggle("dark", nextTheme === "dark");
    window.localStorage.setItem("theme", nextTheme);
  };

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-surface shadow-soft">
      <div className="flex min-h-[71px] flex-wrap items-center gap-4 px-6 md:px-10 py-4 lg:h-[71px] lg:flex-nowrap lg:py-4">
        <div className="flex items-center gap-4">
          <div className="space-y-1 pt-0.5">
            <p className="eyebrow">City Control</p>
            <h2 className="text-xl font-semibold">FlowMind Operations</h2>
          </div>
          <div className="hidden h-9 w-px bg-border/80 lg:block" />
          <div className="flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-3 py-2">
            <label className="text-xs font-medium text-muted">
              Active
            </label>
            <Select
              value={activeDistrictId ?? undefined}
              onValueChange={setActiveDistrictId}
              disabled={isLoading || districts.length === 0}
            >
              <SelectTrigger className="h-8 min-w-[200px] bg-surface">
                <SelectValue placeholder={isLoading ? "Loading..." : "Select district"} />
              </SelectTrigger>
              <SelectContent>
                {districts.map((district) => (
                  <SelectItem key={district.district_id} value={district.district_id}>
                    {district.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-2">
          <Link href="/simulation" className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
            <FlaskConical size={16} />
            Run Simulation
          </Link>
          <Link href="/notifications" className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
            <Bell size={16} />
            Notifications
          </Link>
          <Link href="/playback" className={cn(buttonVariants({ size: "sm" }))}>
            <PlayCircle size={16} />
            Open Playback
          </Link>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={toggleTheme}
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            {theme === "dark" ? "Light" : "Dark"}
          </Button>
          {me ? (
            <>
              <Badge variant="info">{(me.roles ?? ["Operator"])[0]}</Badge>
              <div className="text-xs text-muted">{me.name}</div>
              <a
                className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                href={`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/auth/logout`}
              >
                <LogOut size={16} />
                Sign out
              </a>
            </>
          ) : (
            <a className={cn(buttonVariants({ size: "sm" }))} href="/auth">
              <LogIn size={16} />
              Sign in
            </a>
          )}
        </div>
      </div>
    </header>
  );
}
