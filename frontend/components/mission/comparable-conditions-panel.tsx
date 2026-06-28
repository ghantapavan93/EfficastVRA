"use client";

import { AlertTriangle, CheckCircle2, GitCompare, HelpCircle, XCircle } from "lucide-react";
import { useComparability } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Badge, Chip } from "@/components/forge/primitives";
import type { Tone } from "@/lib/state-meta";
import type { ComparabilityDim } from "@/lib/types";

const CLASS: Record<string, { tone: Tone; label: string }> = {
  COMPARABLE: { tone: "verified", label: "Comparable" },
  PARTIALLY_COMPARABLE: { tone: "warning", label: "Partially comparable" },
  NOT_COMPARABLE: { tone: "failure", label: "Not comparable" },
  UNKNOWN: { tone: "steel", label: "Unknown" },
};

const val = (v: string | number | null) => (v === null || v === undefined ? "—" : String(v));

function DimIcon({ status, weight }: { status: string; weight: string }) {
  if (status === "match") return <CheckCircle2 className="h-4 w-4 shrink-0 text-verified" aria-hidden />;
  if (status === "unknown") return <HelpCircle className="h-4 w-4 shrink-0 text-ink-mut" aria-hidden />;
  // shift
  if (weight === "key") return <XCircle className="h-4 w-4 shrink-0 text-failure" aria-hidden />;
  if (weight === "minor") return <AlertTriangle className="h-4 w-4 shrink-0 text-warning" aria-hidden />;
  return <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-ink-mut" aria-hidden />; // info shift
}

export function ComparableConditionsPanel({ incidentId }: { incidentId: string }) {
  const { data } = useComparability(incidentId, 4000);
  if (!data) return null;
  if (!data.available) {
    return (
      <section className="rounded-xl border border-line bg-surface-1 p-6 text-sm text-ink-mut">
        Comparable conditions are available once monitoring begins.
      </section>
    );
  }
  const c = CLASS[data.classification ?? "UNKNOWN"] ?? CLASS.UNKNOWN;

  return (
    <section className="space-y-4">
      <div className="alive rounded-xl border border-line bg-surface-1 p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <GitCompare className="h-4 w-4 text-agent" aria-hidden />
            <h3 className="text-sm font-semibold text-ink-hi">Comparable conditions</h3>
            <span className="text-[12px] text-ink-mut">causal-honesty gate · advisory</span>
          </div>
          <Badge tone={c.tone}>{c.label}</Badge>
        </div>
        <p className="mt-2 text-sm text-ink">{data.implication ?? data.reason}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-[12px] text-ink-mut">
          <Chip>confidence ×{(data.confidence_multiplier ?? 1).toFixed(2)}</Chip>
          {(data.key_shifts ?? 0) > 0 && <Chip>{data.key_shifts} key shift{data.key_shifts === 1 ? "" : "s"}</Chip>}
          {(data.minor_shifts ?? 0) > 0 && <Chip>{data.minor_shifts} minor shift{data.minor_shifts === 1 ? "" : "s"}</Chip>}
        </div>
      </div>

      <div className="rounded-xl border border-line bg-surface-1 p-5">
        <div className="label mb-1">Operating context — normal vs verification window</div>
        <p className="mb-3 text-[12px] text-ink-mut">
          A <b className="font-medium text-ink">key</b> shift (product, mode, load, speed, sensor health) breaks comparability;
          a <b className="font-medium text-ink">minor</b> shift weakens it; <b className="font-medium text-ink">info</b> changes (lot, shift) are normal.
        </p>
        <div className="space-y-1">
          {(data.dimensions ?? []).map((d: ComparabilityDim) => (
            <div key={d.key} className="flex items-center gap-2.5 border-t border-line/60 py-1.5 text-sm first:border-t-0">
              <DimIcon status={d.status} weight={d.weight} />
              <span className="w-40 shrink-0 text-ink">{d.label}</span>
              <span className="mono text-[12px] text-ink-mut">
                {val(d.baseline)} <span className="text-ink-mut">→</span>{" "}
                <span className={cn(d.status === "shift" && d.weight === "key" ? "text-failure" :
                  d.status === "shift" && d.weight === "minor" ? "text-warning" : "text-ink")}>{val(d.observed)}</span>
              </span>
              <span className="ml-auto flex items-center gap-2">
                {d.note && <span className="text-[10px] text-ink-mut">{d.note}</span>}
                <span className="rounded border border-line px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-ink-mut">{d.weight}</span>
              </span>
            </div>
          ))}
        </div>
      </div>

      {data.basis && <p className="px-1 text-[11px] text-ink-mut">{data.basis}</p>}
    </section>
  );
}
