"use client";

import { Activity, AlertTriangle, CheckCircle2, Radar } from "lucide-react";
import { useForecast } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Badge, Chip, ProgressBar } from "@/components/forge/primitives";
import type { ForecastHypothesis } from "@/lib/types";

export function ForecastPanel({ incidentId }: { incidentId: string }) {
  const { data } = useForecast(incidentId, 3000);
  if (!data || !data.available) return null;

  const pRelapse = data.p_relapse ?? 0;
  const pHolds = data.p_recovery_holds ?? 1 - pRelapse;
  const warning = data.predicted_relapse_cycle != null;
  const tone = warning ? "failure" : pHolds >= 0.75 ? "verified" : "agent";

  return (
    <section
      className={cn(
        "rounded-xl border p-4",
        warning ? "border-failure/40 bg-failure-soft" : "border-line bg-surface-1",
      )}
      aria-live="polite"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Radar className={cn("h-4 w-4", warning ? "text-failure" : "text-agent")} aria-hidden />
          <h3 className="text-sm font-semibold text-ink-hi">Recovery forecast</h3>
          <span className="inline-flex items-center gap-1.5 text-[12px] text-ink-mut">
            <Activity className="h-3 w-3" aria-hidden /> predictive · advisory
          </span>
        </div>
        <Badge tone={tone}>
          {warning ? (
            <><AlertTriangle className="h-3 w-3" aria-hidden /> relapse predicted</>
          ) : (
            <><CheckCircle2 className="h-3 w-3" aria-hidden /> on track</>
          )}
        </Badge>
      </div>

      <p className={cn("mt-2 text-sm", warning ? "text-failure" : "text-ink")}>{data.headline}</p>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <Meter label="Will hold" value={pHolds} tone={warning ? "warning" : "verified"} />
        <Meter label="Will relapse" value={pRelapse} tone={warning ? "failure" : "steel"} />
      </div>

      {warning && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Chip>predicted at cycle {data.predicted_relapse_cycle}</Chip>
          {data.fault_cycle != null && <Chip>fault confirmed at cycle {data.fault_cycle}</Chip>}
          {data.lead_cycles != null && <Badge tone="agent">{data.lead_cycles} cycles of lead time</Badge>}
          {data.leading_indicator && <span className="text-[11px] text-ink-mut">via {data.leading_indicator}</span>}
        </div>
      )}

      {data.hypotheses && data.hypotheses.length > 0 && (
        <div className="mt-3 space-y-2 border-t border-line pt-3">
          <div className="label">Competing hypotheses (live support)</div>
          {data.hypotheses.map((h: ForecastHypothesis) => (
            <div key={h.id} className="text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className="text-ink">{h.label}</span>
                <span className="mono text-ink-mut">{Math.round(h.support * 100)}%</span>
              </div>
              <div className="mt-1">
                <ProgressBar value={h.support * 100} tone={h.id === "H2" ? "failure" : "verified"} />
              </div>
              {h.evidence && <p className="mt-1 text-[11px] text-ink-mut">{h.evidence}</p>}
            </div>
          ))}
        </div>
      )}

      {data.basis && <p className="mt-3 text-[11px] text-ink-mut">{data.basis}</p>}
      <p className="mt-2 text-[11px] text-ink-mut">
        Advisory only — the deterministic evaluator still decides closure. A forecast never reopens or
        closes an incident; it gives the team earlier insight.
      </p>
    </section>
  );
}

function Meter({ label, value, tone }: { label: string; value: number; tone: "verified" | "failure" | "warning" | "steel" }) {
  return (
    <div className="rounded-lg border border-line bg-surface-2 p-3">
      <div className="flex items-baseline justify-between">
        <span className="label">{label}</span>
        <span className="mono text-lg text-ink-hi">{Math.round(value * 100)}%</span>
      </div>
      <div className="mt-2">
        <ProgressBar value={value * 100} tone={tone} />
      </div>
    </div>
  );
}
