"use client";

import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  BellRing,
  CheckCircle2,
  FlaskConical,
  GitBranch,
  Inbox,
  ShieldCheck,
} from "lucide-react";
import { useMarkNotificationRead, useNotifications } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Badge, Button } from "@/components/forge/primitives";
import { EmptyState, ErrorState, LoadingState } from "@/components/forge/states";
import type { AppNotification } from "@/lib/types";
import type { Tone } from "@/lib/state-meta";

const KIND: Record<string, { icon: React.ComponentType<{ className?: string }>; tone: Tone; label: string }> = {
  diagnosis_proposed: { icon: GitBranch, tone: "agent", label: "Diagnosis ready" },
  approval_required: { icon: ShieldCheck, tone: "approval", label: "Approval needed" },
  evidence_required: { icon: FlaskConical, tone: "evidence", label: "Evidence needed" },
  reopened: { icon: AlertTriangle, tone: "warning", label: "Reopened" },
  escalated: { icon: AlertTriangle, tone: "failure", label: "Escalated" },
  verified: { icon: CheckCircle2, tone: "verified", label: "Verified" },
};

export default function InboxPage() {
  const { data, isLoading, isError, refetch } = useNotifications(6000);
  const markRead = useMarkNotificationRead();
  const router = useRouter();

  if (isLoading) return <LoadingState label="Loading notifications" />;
  if (isError || !data)
    return <div className="p-6"><ErrorState message="Notifications unavailable." onRetry={() => refetch()} /></div>;

  const open = (n: AppNotification) => {
    if (n.status === "unread") markRead.mutate(n.id);
    if (n.action_path) router.push(n.action_path);
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-7">
      <div className="flex items-center gap-2">
        <Inbox className="h-5 w-5 text-agent" aria-hidden />
        <h1 className="text-2xl font-semibold tracking-tight text-ink-hi">Notifications</h1>
        {data.unread > 0 && <Badge tone="warning">{data.unread} unread</Badge>}
      </div>
      <p className="mt-1 text-sm text-ink-mut">
        Tasks the agent pushed to you ({data.role.replace(/_/g, " ")}) — so you never have to hunt across
        systems for what needs doing next. In production these also go out over WhatsApp / email.
      </p>

      {data.notifications.length === 0 ? (
        <div className="mt-6">
          <EmptyState title="Nothing for you right now" description="The agent will notify you when it needs evidence, an approval, or when an incident changes state." icon={BellRing} />
        </div>
      ) : (
        <ul className="mt-6 space-y-2">
          {data.notifications.map((n) => {
            const meta = KIND[n.kind] ?? { icon: BellRing, tone: "steel" as Tone, label: n.kind };
            const Icon = meta.icon;
            return (
              <li key={n.id}>
                <button
                  type="button"
                  onClick={() => open(n)}
                  className={cn(
                    "flex w-full items-start gap-3 rounded-xl border p-4 text-left transition-colors",
                    n.status === "unread"
                      ? "border-line-strong bg-surface-1 hover:bg-surface-2"
                      : "border-line bg-surface-1/50 hover:bg-surface-2",
                  )}
                >
                  <span className={cn("mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg",
                    n.status === "unread" ? "bg-surface-3" : "bg-surface-2")}>
                    <Icon className="h-4 w-4 text-ink-mut" aria-hidden />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={meta.tone}>{meta.label}</Badge>
                      {n.status === "unread" && <span className="h-1.5 w-1.5 rounded-full bg-agent" aria-label="unread" />}
                      {n.channel !== "in_app" && <span className="mono text-[11px] text-ink-mut">{n.channel}</span>}
                    </div>
                    <div className="mt-1 text-sm font-medium text-ink">{n.title}</div>
                    <p className="mt-0.5 text-xs text-ink-mut">{n.body}</p>
                  </div>
                  {n.status === "unread" && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={(e) => { e.stopPropagation(); markRead.mutate(n.id); }}
                    >
                      Mark read
                    </Button>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
