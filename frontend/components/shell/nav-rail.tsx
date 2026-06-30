"use client";

import { Activity, BellRing, BookMarked, ClipboardCheck, FileCheck2, FileUp, Gauge, Inbox, Lightbulb, ListChecks, ShieldCheck, Telescope, Wrench } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAlerts, useKnowledge, useMissions, useNotifications } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Tooltip } from "@/components/forge/primitives";
import { BrandMark } from "@/components/forge/brand-mark";

export function NavRail() {
  const pathname = usePathname();
  const { data } = useMissions();
  const { data: alertData } = useAlerts(8000);
  const { data: notifData } = useNotifications(8000);
  const { data: knowledgeData } = useKnowledge(10000);
  const openAlerts = alertData?.alerts.length ?? 0;
  const unread = notifData?.unread ?? 0;
  const pendingKnowledge = knowledgeData?.pending ?? 0;
  const active = data?.missions.find((m) => m.is_active);
  const primary = active?.id ?? data?.missions[0]?.id;
  const m = (tab: string) => (primary ? `/missions/${primary}?tab=${tab}` : "/missions");

  const items = [
    { href: "/missions", icon: Gauge, label: "Missions", match: (p: string) => p === "/missions", badge: 0 },
    { href: "/intake", icon: FileUp, label: "Create Mission · Upload data", match: (p: string) => p === "/intake", badge: 0 },
    { href: "/alerts", icon: BellRing, label: "MAIA Alerts", match: (p: string) => p === "/alerts", badge: openAlerts },
    { href: primary ? `/missions/${primary}` : "/missions", icon: Activity, label: "Active Recovery", match: (p: string) => p.startsWith("/missions/"), badge: 0 },
    { href: "/inbox", icon: Inbox, label: "Notifications", match: (p: string) => p === "/inbox", badge: unread },
    { href: "/troubleshoot", icon: Wrench, label: "Troubleshoot", match: (p: string) => p === "/troubleshoot", badge: 0 },
    { href: m("evidence"), icon: ListChecks, label: "Evidence", match: () => false, badge: 0 },
    { href: m("contract"), icon: FileCheck2, label: "Approvals", match: () => false, badge: 0 },
    { href: "/passport", icon: BookMarked, label: "Recovery Passport · asset history", match: (p: string) => p === "/passport", badge: 0 },
    { href: "/handoff", icon: ClipboardCheck, label: "Shift Handoff", match: (p: string) => p === "/handoff", badge: 0 },
    { href: "/knowledge", icon: Lightbulb, label: "Knowledge", match: (p: string) => p === "/knowledge", badge: pendingKnowledge },
    { href: "/system", icon: ShieldCheck, label: "System Health", match: (p: string) => p === "/system", badge: 0 },
    { href: "/vision", icon: Telescope, label: "Future Vision", match: (p: string) => p === "/vision", badge: 0 },
  ];

  return (
    <nav aria-label="Primary" className="glass relative z-10 flex w-14 shrink-0 flex-col items-center gap-1 border-r border-line py-3">
      <Link href="/" aria-label="Verified Recovery Agent home" className="sheen mb-3 grid h-9 w-9 place-items-center rounded-[10px] shadow-[0_0_22px_-10px_var(--agent)] transition-transform hover:scale-105">
        <BrandMark size={30} animated />
      </Link>
      {items.map((it, i) => {
        const isActive = it.match(pathname);
        return (
          <Tooltip key={it.label} content={it.label}>
            <Link
              href={it.href}
              aria-label={it.label}
              aria-current={isActive ? "page" : undefined}
              style={{ animation: "nav-pop .4s ease both", animationDelay: `${i * 38}ms` }}
              className={cn(
                "relative grid h-10 w-10 place-items-center rounded-[10px] transition-all duration-150 hover:-translate-y-px active:scale-95",
                isActive
                  ? "bg-agent-soft text-agent ring-1 ring-agent/40 shadow-[0_0_26px_-6px_var(--agent)]"
                  : "text-ink-mut hover:text-ink hover:bg-surface-2",
              )}
            >
              {isActive && <span className="absolute -left-3 h-5 w-[3px] rounded-pill bg-agent shadow-[0_0_10px_var(--agent)]" aria-hidden />}
              <it.icon className="h-[18px] w-[18px]" />
              {it.badge > 0 && (
                <span
                  className="absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-warning px-1 text-[10px] font-semibold text-black"
                  aria-label={`${it.badge} open`}
                >
                  {it.badge}
                </span>
              )}
            </Link>
          </Tooltip>
        );
      })}
    </nav>
  );
}
