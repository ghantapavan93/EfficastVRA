"use client";

import { AlertTriangle, Check, Lock } from "lucide-react";
import { useMissionSpine } from "@/lib/hooks";
import { Badge } from "@/components/forge/primitives";
import type { MissionStage } from "@/lib/types";

const NODE_COLOR: Record<string, string> = {
  done: "var(--verified)", active: "var(--agent)", blocked: "var(--failure)", pending: "var(--line-strong)",
};

function Node({ s }: { s: MissionStage }) {
  const c = NODE_COLOR[s.status] ?? "var(--line-strong)";
  return (
    <span className="relative grid h-7 w-7 place-items-center rounded-full border bg-surface-1"
      style={{ borderColor: c }} aria-label={`${s.name}: ${s.status}`}>
      {s.status === "active" && <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-50" style={{ background: c }} />}
      {s.status === "done" ? <Check className="h-3.5 w-3.5" style={{ color: c }} aria-hidden />
        : s.status === "blocked" ? <AlertTriangle className="h-3.5 w-3.5" style={{ color: c }} aria-hidden />
          : <span className="relative h-2 w-2 rounded-full" style={{ background: c }} />}
    </span>
  );
}

export function MissionSpine({ incidentId }: { incidentId: string }) {
  const { data } = useMissionSpine(incidentId, 4000);
  if (!data || !data.available) return null;
  const stages = data.stages ?? [];
  const n = stages.length;
  const progress = Math.min(100, ((data.current_index ?? 0) / Math.max(1, n - 1)) * 100);
  const outcomeTone = data.complete ? "verified" : data.outcome === "FAILED" ? "failure"
    : data.outcome === "ESCALATION_REQUIRED" ? "warning" : "agent";

  return (
    <section className="alive rounded-2xl border border-line-strong bg-surface-1 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="label mb-0">Recovery Mission</span>
          {data.reopened_count != null && data.reopened_count > 0 && <Badge tone="failure">reopened ×{data.reopened_count}</Badge>}
        </div>
        <Badge tone={outcomeTone}>{data.complete ? "Qualification Record issued" : (data.outcome ?? "").replace(/_/g, " ")}</Badge>
      </div>

      {/* seven-stage tracker */}
      <div className="relative mt-5 flex items-start justify-between">
        <div className="absolute inset-x-3 top-3.5 h-px bg-line-strong" aria-hidden />
        <div className="absolute left-3 top-3.5 h-px bg-verified transition-all duration-700" style={{ width: `calc(${progress}% - ${progress / 100 * 24}px)` }} aria-hidden />
        {stages.map((s) => (
          <div key={s.index} className="relative z-10 flex flex-1 flex-col items-center gap-1.5 px-1 text-center">
            <Node s={s} />
            <span className="text-[11px] font-medium leading-tight" style={{ color: s.status === "pending" ? "var(--text-faint)" : "var(--text)" }}>{s.name}</span>
            <span className="hidden text-[10px] leading-tight text-ink-mut md:block">{s.summary}</span>
          </div>
        ))}
      </div>

      {/* where it stands · what's blocking · who's next */}
      <div className="mt-5 grid gap-3 border-t border-line pt-4 sm:grid-cols-3">
        <Cell label="Where it stands" value={`Stage ${Math.min((data.current_index ?? 0) + 1, n)} / ${n} · ${data.current_stage}`} />
        <Cell label="What's blocking" value={data.what_blocks ?? "—"} accent={data.complete ? "var(--verified)" : "var(--warning)"} />
        <Cell label="Who's next" value={data.who_next ?? "—"} icon={!data.complete} />
      </div>

      {data.why_not_verified && data.why_not_verified.length > 0 && (
        <div className="mt-3 rounded-lg border border-line bg-surface-2 p-3">
          <div className="label mb-1.5">Why it isn&apos;t verified yet</div>
          <ul className="space-y-1 text-[12px] text-ink-mut">
            {data.why_not_verified.map((r, i) => <li key={i}>· {r}</li>)}
          </ul>
        </div>
      )}
    </section>
  );
}

function Cell({ label, value, accent, icon }: { label: string; value: string; accent?: string; icon?: boolean }) {
  return (
    <div>
      <div className="label">{label}</div>
      <div className="mt-0.5 flex items-start gap-1.5 text-sm" style={{ color: accent ?? "var(--text)" }}>
        {icon && <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-mut" aria-hidden />}
        <span>{value}</span>
      </div>
    </div>
  );
}
