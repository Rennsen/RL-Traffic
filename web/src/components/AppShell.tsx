"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { PanelLeftClose } from "lucide-react";

import { Nav } from "@/components/Nav";
import { TopBar } from "@/components/TopBar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { getCurrentUser } from "@/lib/api/client";
import { cn } from "@/lib/utils";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isAuthRoute = pathname?.startsWith("/auth");
  const [collapsed, setCollapsed] = useState(false);
  const [authState, setAuthState] = useState<"checking" | "authed" | "guest">("checking");

  useEffect(() => {
    const stored = window.localStorage.getItem("sidebar-collapsed");
    if (stored === "true") {
      setCollapsed(true);
    }
  }, []);

  useEffect(() => {
    if (isAuthRoute) {
      setAuthState("guest");
      return;
    }
    let active = true;
    setAuthState("checking");
    getCurrentUser()
      .then((user) => {
        if (!active) return;
        if (user) {
          setAuthState("authed");
        } else {
          setAuthState("guest");
          router.replace("/auth");
        }
      })
      .catch(() => {
        if (!active) return;
        setAuthState("guest");
        router.replace("/auth");
      });
    return () => {
      active = false;
    };
  }, [isAuthRoute, router]);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      window.localStorage.setItem("sidebar-collapsed", String(next));
      return next;
    });
  };

  if (isAuthRoute) {
    return <main className="min-h-screen bg-bg px-6 py-10">{children}</main>;
  }

  if (authState !== "authed") {
    return (
      <main className="min-h-screen bg-bg px-6 py-10">
        <div className="panel mx-auto max-w-xl p-6 text-sm text-muted">
          Checking session… redirecting to sign-in if needed.
        </div>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-bg">
      <aside
        className={cn(
          "hidden lg:flex fixed inset-y-0 left-0 flex-col border-r border-border bg-surface-2 overflow-hidden transition-[width] duration-300 ease-in-out",
          collapsed ? "w-24" : "w-[18rem]",
        )}
      >
        <div className="flex h-full flex-col">
          <div
            className={cn(
              "flex h-[72px] items-center border-b border-border",
              collapsed ? "justify-center px-3" : "justify-between px-4",
            )}
          >
            <div className={cn("flex items-center", collapsed ? "gap-0" : "gap-3")}>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={collapsed ? toggleCollapsed : undefined}
                aria-label={collapsed ? "Expand sidebar" : "Sidebar logo"}
                className="h-9 w-9 rounded-xl border border-border bg-surface p-0 text-sm font-semibold text-accent"
              >
                FM
              </Button>
              {!collapsed && (
                <div>
                  <h1 className="text-base font-semibold text-ink">FlowMind</h1>
                  <p className="text-xs text-muted">Traffic Ops Console</p>
                </div>
              )}
            </div>
            {!collapsed && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={toggleCollapsed}
                aria-label="Collapse sidebar"
              >
                <PanelLeftClose size={16} />
              </Button>
            )}
          </div>

          <div className={cn("flex-1 space-y-4 py-4", collapsed ? "px-3" : "px-4")}>
            <Card className="border-border/70 bg-surface p-3">
              {!collapsed ? (
                <div className="space-y-2">
                  <Badge variant="info">Traffic Ops</Badge>
                  <p className="text-xs text-muted">
                    Adaptive control for city-scale intersections.
                  </p>
                </div>
              ) : (
                <div className="flex items-center justify-center">
                  <Badge variant="info">Ops</Badge>
                </div>
              )}
            </Card>

            <Card className="flex-1 border-border/70 bg-surface p-2">
              {!collapsed && (
                <div className="px-2 pb-2">
                  <p className="text-xs font-semibold text-muted">Navigation</p>
                </div>
              )}
              <Separator className={collapsed ? "mb-2" : "mb-3"} />
              <div className={cn("flex-1 overflow-y-auto", collapsed ? "px-1" : "px-2")}>
                <Nav collapsed={collapsed} />
              </div>
            </Card>

          </div>
          <div className={cn("mt-auto", collapsed ? "px-3 pb-4" : "px-4 pb-4")}>
            <Card className="border-border/70 bg-surface p-3">
              {!collapsed ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs text-muted">
                    <span>System Status</span>
                    <Badge variant="info">Operational</Badge>
                  </div>
                  <Separator />
                  <p className="text-xs text-muted">vNext Showcase</p>
                </div>
              ) : (
                <div className="flex items-center justify-center">
                  <Badge variant="info">On</Badge>
                </div>
              )}
            </Card>
          </div>
        </div>
      </aside>

      <div className={cn("min-h-screen", collapsed ? "lg:pl-24" : "lg:pl-[18rem]")}>
        <TopBar />
        <main className="px-5 md:px-8 pb-16 pt-6">{children}</main>
      </div>
    </div>
  );
}
