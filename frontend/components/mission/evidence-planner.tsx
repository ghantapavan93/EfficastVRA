"use client";

import { Lightbulb, TrendingUp } from "lucide-react";
import { useEvidencePlan } from "@/lib/hooks";
import { Badge, Chip } from "@/components/forge/primitives";
import type { Tone } from "@/lib/state-meta";
import type { EvidenceRec } from "@/lib/types";

const IMPACT_TONE: Record<string, Tone> = { Critical: "failure", High: "warning", Supporting: "steel" };

export function EvidencePlanner({ incidentId }: { incidentId: string }) {
  const { data } = useEvidencePlan(incidentId, 4000);
  if (!data) return null;
  if (!data.available) {
    return <section className="rounded-xl border border-line bg-surface-1 p-6 text-sm text-ink-mut">{data.reason ?? "The Evidence Planner opens once a Recovery Contract exists."}</section>;
  }
  const cur = Math.round((data.current_confidence ?? 0) * 100);
  const pot = Math.round((data.potential_confidence ?? 0) * 100);
  const recs = data.recommendations ?? [];

  return (
    <section className="space-y-4">
      <div className="alive rounded-2xl border border-line-strong bg-surface-1 p-5">
        <div className="flex items-center gap-2">
          <Lightbulb className="h-4 w-4 text-agent" aria-hidden />
          <h3 className="text-sm font-semibold text-ink-hi">Evidence Value Planner</h3>
          <span className="text-[12px] text-ink-mut">what would most reduce uncertainty · advisory</span>
        </div>
        <p className="mt-2 text-sm text-ink">
          {recs.length === 0 ? "No outstanding evidence would change the decision — the gates that remain are not evidence-resolvable."
            : `Collecting the right evidence next could raise decision readiness from ${cur}% toward ${pot}%.`}
        </p>

        {/* readiness bar: current → potential */}
        <div className="mt-3">
          <div className="mb-1 flex items-center justify-between text-[11px] text-ink-mut">
            <span>decision readiness</span>
            <span className="mono">{cur}% <span className="text-ink-faint">→</span> <span className="text-verified">{pot}%</span></span>
          </div>
          <div className="relative h-2 overflow-hidden rounded-full bg-surface-3">
            <div className="absolute inset-y-0 left-0 rounded-full bg-verified/30" style={{ width: `${pot}%` }} />
            <div className="absolute inset-y-0 left-0 rounded-full bg-agent" style={{ width: `${cur}%` }} />
          </div>
          {data.unmet_invariants != null && data.unmet_invariants > 0 && (
            <div className="mt-1.5 text-[11px] text-ink-mut">{data.unmet_invariants} hard gate{data.unmet_invariants === 1 ? "" : "s"} unmet</div>
          )}
        </div>
      </div>

      {recs.length > 0 && (
        <ol className="space-y-2">
          {recs.map((r: EvidenceRec, i) => (
            <li key={r.title} className="alive rounded-xl border border-line bg-surface-1 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="mono grid h-6 w-6 place-items-center rounded-full border border-line-strong text-[11px] text-ink-mut">{i + 1}</span>
                <span className="text-sm font-medium text-ink">{r.title}</span>
                <Badge tone={IMPACT_TONE[r.decision_impact] ?? "steel"}>{r.decision_impact}</Badge>
                <Chip>{r.effort} effort</Chip>
                <span className="ml-auto inline-flex items-center gap-1 text-[12px] font-semibold text-verified">
                  <TrendingUp className="h-3.5 w-3.5" aria-hidden /> +{Math.round(r.confidence_gain * 100)}%
                </span>
              </div>
              <p className="mt-1.5 text-[12px] leading-relaxed text-ink-mut">{r.why}</p>
            </li>
          ))}
        </ol>
      )}
      {data.basis && <p className="px-1 text-[11px] text-ink-mut">{data.basis}</p>}
    </section>
  );
}
