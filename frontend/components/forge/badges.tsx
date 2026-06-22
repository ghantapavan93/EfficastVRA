"use client";

import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Circle,
  Clock,
  Flame,
  FlaskConical,
  ShieldCheck,
  XOctagon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  APPROVAL_META,
  CONDITION_META,
  EVIDENCE_META,
  SEVERITY_META,
  STATE_META,
  TONE_CLASS,
  type Tone,
} from "@/lib/state-meta";
import { Badge } from "./primitives";

const TONE_ICON: Record<Tone, React.ComponentType<{ className?: string }>> = {
  agent: Activity,
  verified: CheckCircle2,
  pending: Clock,
  warning: AlertTriangle,
  failure: XOctagon,
  approval: ShieldCheck,
  evidence: FlaskConical,
  steel: Circle,
  brand: Flame,
};

export function StateBadge({ state, className }: { state: string; className?: string }) {
  const meta = STATE_META[state] ?? { label: state, tone: "steel" as Tone };
  const Icon = TONE_ICON[meta.tone];
  return (
    <Badge tone={meta.tone} className={className}>
      <Icon className="h-3 w-3" aria-hidden />
      {meta.label}
    </Badge>
  );
}

export function SeverityIndicator({ severity }: { severity: string }) {
  const meta = SEVERITY_META[severity] ?? { label: severity, tone: "steel" as Tone };
  return (
    <Badge tone={meta.tone} dot>
      {meta.label}
    </Badge>
  );
}

export function ConditionPill({ status }: { status: string }) {
  const meta = CONDITION_META[status] ?? { label: status, tone: "steel" as Tone };
  const Icon = TONE_ICON[meta.tone];
  return (
    <span className={cn("inline-flex items-center gap-1 text-[12px] font-medium", TONE_CLASS[meta.tone].text)}>
      <Icon className="h-3.5 w-3.5" aria-hidden />
      {meta.label}
    </span>
  );
}

export function EvidenceStatusBadge({ status }: { status: string }) {
  const meta = EVIDENCE_META[status] ?? { label: status, tone: "steel" as Tone };
  return <Badge tone={meta.tone}>{meta.label}</Badge>;
}

export function ApprovalStatusBadge({ status }: { status: string }) {
  const meta = APPROVAL_META[status] ?? { label: status, tone: "steel" as Tone };
  return <Badge tone={meta.tone} dot>{meta.label}</Badge>;
}

export function EvidenceFreshnessBadge({
  seconds,
  max,
}: {
  seconds: number | null;
  max: number | null;
}) {
  if (seconds === null) return null;
  const stale = max !== null && seconds > max;
  const label = seconds < 60 ? `${seconds}s` : seconds < 3600 ? `${Math.round(seconds / 60)}m` : `${Math.round(seconds / 3600)}h`;
  return (
    <span
      className={cn(
        "mono inline-flex items-center gap-1 text-[11px]",
        stale ? "text-warning" : "text-evidence",
      )}
      title={stale ? `Stale: older than ${max}s freshness limit` : "Within freshness limit"}
    >
      <Clock className="h-3 w-3" aria-hidden />
      {label}
      {stale && " · stale"}
    </span>
  );
}

export function AgentActivityIndicator({
  label,
  active = true,
}: {
  label: string;
  active?: boolean;
}) {
  return (
    <span className="inline-flex items-center gap-2 text-[12px] text-agent" aria-live="polite">
      <span className="relative flex h-2 w-2" aria-hidden>
        {active && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-agent opacity-60" />}
        <span className="relative inline-flex h-2 w-2 rounded-full bg-agent" />
      </span>
      {label}
    </span>
  );
}
