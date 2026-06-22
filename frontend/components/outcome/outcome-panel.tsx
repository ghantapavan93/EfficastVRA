"use client";

import { ArrowRight, BadgeCheck, BookOpen, Boxes, ShieldCheck } from "lucide-react";
import { useOutcome } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Badge, Chip, SectionLabel } from "@/components/forge/primitives";
import { ErrorState, LoadingState } from "@/components/forge/states";

const ROWS: { key: string; label: string; unit: string }[] = [
  { key: "vibration", label: "Vibration", unit: "mm/s" },
  { key: "temperature", label: "Temperature", unit: "°C" },
  { key: "cycle_time", label: "Cycle time", unit: "s" },
  { key: "scrap_pct", label: "Scrap", unit: "%" },
];

export function OutcomePanel({ incidentId }: { incidentId: string }) {
  const { data, isLoading, isError, refetch } = useOutcome(incidentId);
  if (isLoading) return <LoadingState label="Loading outcome" />;
  if (isError || !data) return <ErrorState message="Could not load the outcome." onRetry={() => refetch()} />;

  const verified = data.state === "VERIFIED_RECOVERY";

  return (
    <div className="space-y-5">
      <section className={cn("rounded-xl border p-5", verified ? "border-verified/30 bg-verified-soft" : "border-line bg-surface-1")}>
        <div className="flex items-center gap-2">
          {verified ? <BadgeCheck className="h-5 w-5 text-verified" /> : <ShieldCheck className="h-5 w-5 text-ink-mut" />}
          <h2 className="text-xl font-semibold text-ink-hi">
            {verified ? "Production recovery verified." : "Recovery in progress."}
          </h2>
        </div>
        <p className="mt-1 text-sm text-ink-mut">{data.summary || "Awaiting verification."}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Chip>{data.stable_cycles}/{data.required_stable_cycles} stable cycles</Chip>
          <Chip>reopened ×{data.reopened_count}</Chip>
          {data.quality_released && <Badge tone="verified">quality released</Badge>}
          {data.policy_version && <Chip>policy {data.policy_version}</Chip>}
        </div>
      </section>

      {/* before / after */}
      <section className="rounded-xl border border-line bg-surface-1 p-4">
        <SectionLabel className="mb-3">Before / after</SectionLabel>
        <div className="overflow-hidden rounded-lg border border-line">
          <div className="grid grid-cols-3 bg-raised px-3 py-2 text-[11px] text-ink-mut">
            <span>Metric</span><span className="text-right">Before</span><span className="text-right">After</span>
          </div>
          {ROWS.map((r) => (
            <div key={r.key} className="grid grid-cols-3 items-center border-t border-line px-3 py-2 text-sm">
              <span className="text-ink-mut">{r.label}</span>
              <span className="mono text-right text-failure">{String(data.before[r.key])} {r.unit}</span>
              <span className="mono text-right text-verified">{String(data.after[r.key])} {r.unit}</span>
            </div>
          ))}
          <div className="grid grid-cols-3 items-center border-t border-line px-3 py-2 text-sm">
            <span className="text-ink-mut">Fault F27</span>
            <span className="text-right text-failure">{String(data.before.fault)}</span>
            <span className="text-right text-verified">{String(data.after.fault)}</span>
          </div>
        </div>
      </section>

      {/* interventions */}
      <section className="rounded-xl border border-line bg-surface-1 p-4">
        <SectionLabel className="mb-3">Interventions</SectionLabel>
        <div className="space-y-2">
          {data.interventions.map((i) => (
            <div key={i.sequence} className="flex items-center gap-3 rounded-lg border border-line bg-raised px-3 py-2">
              <span className={cn("grid h-6 w-6 place-items-center rounded-md text-[11px] mono", i.failed ? "bg-failure-soft text-failure" : "bg-verified-soft text-verified")}>{i.sequence}</span>
              <span className="flex-1 text-sm text-ink">{i.title}</span>
              <Badge tone={i.failed ? "failure" : "verified"}>{i.failed ? "did not hold" : i.status.toLowerCase()}</Badge>
            </div>
          ))}
        </div>
        {data.lots.length > 0 && (
          <div className="mt-3 flex items-center gap-2 text-xs text-ink-mut">
            <Boxes className="h-3.5 w-3.5" /> Affected lots:
            {data.lots.map((l) => (
              <Chip key={l.id}>{l.id} · {l.disposition.toLowerCase()}</Chip>
            ))}
          </div>
        )}
      </section>

      {/* knowledge candidate */}
      {data.knowledge_candidate && (
        <section className="rounded-xl border border-approval/30 bg-surface-1 p-4">
          <div className="flex items-center justify-between">
            <SectionLabel className="flex items-center gap-1.5"><BookOpen className="h-3.5 w-3.5" /> Knowledge candidate</SectionLabel>
            <Badge tone="approval">Pending expert review</Badge>
          </div>
          <h3 className="mt-2 text-sm font-medium text-ink-hi">{data.knowledge_candidate.title}</h3>
          <p className="mt-1 text-xs leading-relaxed text-ink-mut">{data.knowledge_candidate.lesson}</p>
          <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
            {data.knowledge_candidate.applicable_models.map((mdl) => <Chip key={mdl}>{mdl}</Chip>)}
            <Chip>component: {data.knowledge_candidate.component}</Chip>
            <Chip>reviewer: {data.knowledge_candidate.reviewer_role.replace("_", " ")}</Chip>
          </div>
          <p className="mt-2 inline-flex items-center gap-1 text-[11px] text-approval">
            <ArrowRight className="h-3 w-3" /> Candidate knowledge — not approved guidance until an expert reviews it.
          </p>
        </section>
      )}
    </div>
  );
}
