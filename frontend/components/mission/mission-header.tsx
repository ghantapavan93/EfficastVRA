"use client";

import { Bot, HardHat, RotateCcw } from "lucide-react";
import type { MissionDetail, RailStage } from "@/lib/types";
import { cn } from "@/lib/utils";
import { SeverityIndicator, StateBadge } from "@/components/forge/badges";
import { Chip } from "@/components/forge/primitives";
import { SyntheticBadge } from "@/components/shell/synthetic-badge";

const STAGE_LABEL: Record<string, string> = {
  diagnosis: "Diagnosis",
  intervention: "Intervention",
  contract: "Contract",
  evidence: "Evidence",
  approval: "Approval",
  monitoring: "Monitoring",
  verification: "Verification",
  outcome: "Outcome",
};

const STATUS_DOT: Record<string, string> = {
  complete: "bg-verified border-verified",
  active: "bg-agent border-agent",
  upcoming: "bg-surface-3 border-line",
  blocked: "bg-warning border-warning",
  failed: "bg-failure border-failure",
  reopened: "bg-failure border-failure",
};

export function MissionHeader({ m }: { m: MissionDetail }) {
  const reopened = m.reopened_count > 0;
  return (
    <div className="border-b border-line bg-raised/60">
      <div className="mx-auto max-w-6xl px-6 pt-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="mono text-xs text-ink-mut">{m.id}</span>
              <StateBadge state={m.state} />
              <SeverityIndicator severity={m.severity} />
              {reopened && (
                <Chip className="text-failure">
                  <RotateCcw className="h-3 w-3" /> reopened ×{m.reopened_count}
                </Chip>
              )}
              <SyntheticBadge compact />
            </div>
            <h1 className="mt-2 text-[26px] font-semibold leading-tight tracking-tight text-ink-hi">{m.title}</h1>
            <p className="mt-1 max-w-3xl text-sm text-ink-mut">{m.objective}</p>
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-mut">
              {m.machine && <span><span className="label mr-1.5">Machine</span><span className="mono text-ink">{m.machine.code}</span> · {m.machine.name}</span>}
              {m.order && <span><span className="label mr-1.5">Order</span><span className="mono text-ink">{m.order.id}</span> · {m.order.qty_remaining.toLocaleString()} units left</span>}
            </div>
          </div>

          {/* responsibility split */}
          <div className="grid w-full max-w-md grid-cols-2 gap-2 sm:w-auto">
            <Responsibility icon={Bot} tone="agent" who="Agent" text={m.agent_responsibility} />
            <Responsibility icon={HardHat} tone="brand" who="Human" text={m.human_responsibility} />
          </div>
        </div>

        {/* progress rail */}
        <ProgressRail rail={m.progress_rail} />
      </div>
    </div>
  );
}

function Responsibility({
  icon: Icon,
  tone,
  who,
  text,
}: {
  icon: React.ComponentType<{ className?: string }>;
  tone: "agent" | "brand";
  who: string;
  text: string;
}) {
  return (
    <div className="rounded-lg border border-line bg-surface-1 p-2.5">
      <div className={cn("flex items-center gap-1.5 text-[11px] font-semibold", tone === "agent" ? "text-agent" : "text-brand")}>
        <Icon className="h-3.5 w-3.5" /> {who} responsibility
      </div>
      <p className="mt-1 text-[11px] leading-snug text-ink-mut">{text}</p>
    </div>
  );
}

function ProgressRail({ rail }: { rail: RailStage[] }) {
  return (
    <ol className="mt-5 flex items-center gap-1 overflow-x-auto pb-4" aria-label="Mission progress">
      {rail.map((s, i) => (
        <li key={s.stage} className="flex min-w-0 flex-1 items-center gap-1">
          <div className="flex min-w-0 flex-col items-center gap-1.5">
            <span
              className={cn("h-3 w-3 rounded-full border-2 transition-colors", STATUS_DOT[s.status] ?? STATUS_DOT.upcoming, s.status === "active" && "ring-4 ring-agent-soft")}
              aria-label={`${STAGE_LABEL[s.stage]}: ${s.status}`}
            />
            <span className={cn("whitespace-nowrap text-[10px]", s.status === "active" ? "text-ink" : s.status === "reopened" || s.status === "failed" ? "text-failure" : "text-ink-faint")}>
              {STAGE_LABEL[s.stage]}
            </span>
          </div>
          {i < rail.length - 1 && (
            <span className={cn("h-px flex-1", rail[i + 1].status === "upcoming" ? "bg-line" : s.status === "reopened" || s.status === "failed" ? "bg-failure/50" : "bg-agent/40")} />
          )}
        </li>
      ))}
    </ol>
  );
}
