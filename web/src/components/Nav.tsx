"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Bell,
  Building2,
  FileText,
  FlaskConical,
  LayoutDashboard,
  Map,
  PlayCircle,
  Shield,
  Smartphone,
} from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/districts", label: "Districts", icon: Building2 },
  { href: "/dashboard", label: "Live Dashboard", icon: Activity },
  { href: "/simulation", label: "Simulation Lab", icon: FlaskConical },
  { href: "/playback", label: "Playback", icon: PlayCircle },
  { href: "/city-map", label: "City Map", icon: Map },
  { href: "/notifications", label: "Notifications", icon: Bell },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/executive", label: "Executive", icon: Smartphone },
  { href: "/admin", label: "Admin", icon: Shield },
];

export function Nav({ collapsed = false }: { collapsed?: boolean }) {
  const pathname = usePathname();
  return (
    <TooltipProvider delayDuration={120}>
      <nav className="space-y-1.5">
        {navItems.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;

          const link = (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                buttonVariants({ variant: "ghost", size: "sm" }),
                "h-10 w-full gap-3 text-sm transition-colors",
                collapsed ? "justify-center px-2" : "justify-start px-3",
                active
                  ? "bg-surface-2 text-ink shadow-soft"
                  : "text-ink/80 hover:bg-surface",
              )}
            >
              <span
                className={cn(
                  "flex items-center justify-center rounded-md",
                  collapsed ? "h-9 w-9" : "h-8 w-8",
                  active ? "text-ink" : "text-muted",
                )}
              >
                <Icon size={16} />
              </span>
              {!collapsed && (
                <span className={cn(active ? "text-ink" : "text-ink/80")}>{item.label}</span>
              )}
            </Link>
          );

          if (!collapsed) {
            return link;
          }

          return (
            <Tooltip key={item.href}>
              <TooltipTrigger asChild>{link}</TooltipTrigger>
              <TooltipContent side="right" className="text-xs">
                {item.label}
              </TooltipContent>
            </Tooltip>
          );
        })}
      </nav>
    </TooltipProvider>
  );
}
