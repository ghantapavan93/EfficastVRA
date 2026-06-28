"use client";

import { AlertTriangle, CheckCircle2, ShieldAlert, ShieldCheck, Users, XCircle } from "lucide-react";
import { useDisposition } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/forge/primitives";
import type { Tone } from "@/lib/state-meta";
import type { DispInvariant } from "@/lib/types";

const DISP: Record<string, { tone: Tone; label: string }> = {
  VERIFIED: { tone: "verified", label: "Verified" },
  CONDITIONAL: { tone: "steel", label: "Conditional" },
  FAILED: { tone: "failure", label: "Failed" },
  INSUFFICIENT_EVIDENCE: { tone: "warning", label: "Insufficient evidence" },
  ESCALATION_REQUIRED: { tone: "warning", label: "Escalation required" },
  IN_PROGRESS: { tone: "steel", label: "In progress" },
};

function statusTone(axis: string, v: string): Tone {
  if (axis === "technician") return v === "completed" ? "verified" : "steel";
  if (axis === "telemetry") return v === "stable" ? "verified" : v === "failed" ? "failure" : "steel";
  if (axis === "quality") return v === "released" ? "verified" : v === "hold" ? "failure" : "steel";
  return "steel";
}

export function DispositionPanel({ incidentId }: { incidentId: string }) {
  const { data } = useDisposition(incidentId, 3000);
  if (!data) return null;
  if (!data.available) {
    return (
      <section className="rounded-xl border border-line bg-surface-1 p-6 text-sm text-ink-mut">
        Disposition is available once a Recovery Contract is drafted.
      </section>
    );
  }
  const d = DISP[data.disposition ?? "IN_PROGRESS"] ?? DISP.IN_PROGRESS;
  const hs = data.human_status;

  return (
    <section className="space-y-4">
      {/* verdict header */}
      <div className="alive rounded-xl border border-line bg-surface-1 p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-ink-hi">Recovery disposition</h3>
            <span className="text-[12px] text-ink-mut">four-outcome decision · advisory</span>
          </div>
          <Badge tone={d.tone}>{d.label}</Badge>
        </div>
        <p className="mt-2 text-sm text-ink">{data.meaning}</p>

        {/* the hard truth: cleared to close or not */}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className={cn("inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm",
            data.can_close ? "border-verified/30 bg-verified-soft text-ink" : "border-line bg-surface-2 text-ink")}>
            {data.can_close
              ? <><ShieldCheck className="h-4 w-4 text-verified" aria-hidden /> Cleared to close</>
              : <><ShieldAlert className="h-4 w-4 text-ink-mut" aria-hidden /> Not cleared to close</>}
          </span>
          {data.comparability?.classification && data.comparability.classification !== "COMPARABLE" && (
            <span className="text-[12px] text-ink-mut">
              comparability {data.comparability.classification.replace(/_/g, " ").toLowerCase()}
              {data.comparability.confounding_dimensions?.length
                ? ` · confounders: ${data.comparability.confounding_dimensions.join(", ")}` : ""}
            </span>
          )}
          {typeof data.effective_confidence === "number" && (
            <span className="mono text-[12px] text-ink-mut">effective conf {data.effective_confidence.toFixed(2)}</span>
          )}
        </div>
      </div>

      {/* hard closure invariants — closure needs EVERY one; the risk score is only advisory */}
      <div className="rounded-xl border border-line bg-surface-1 p-5">
        <div className="label mb-1">Hard closure invariants</div>
        <p className="mb-3 text-[12px] text-ink-mut">
          Closure requires <b className="font-medium text-ink">every</b> invariant below — the False-Closure Risk
          score is advisory and can never substitute for a missing one.
        </p>
        <div className="space-y-1.5">
          {(data.hard_invariants ?? []).map((inv: DispInvariant) => (
            <div key={inv.key} className="flex items-center gap-2.5 text-sm">
              {inv.ok
                ? <CheckCircle2 className="h-4 w-4 shrink-0 text-verified" aria-hidden />
                : <XCircle className="h-4 w-4 shrink-0 text-failure" aria-hidden />}
              <span className={cn(inv.ok ? "text-ink" : "text-ink-hi")}>{inv.label}</span>
              <span className="mono ml-auto text-[11px] text-ink-mut">{inv.detail}</span>
            </div>
          ))}
        </div>
      </div>

      {/* human-status matrix — when signals disagree, escalate instead of forcing a winner */}
      <div className="rounded-xl border border-line bg-surface-1 p-5">
        <div className="mb-3 flex items-center gap-2">
          <Users className="h-4 w-4 text-agent" aria-hidden />
          <div className="label">Status matrix</div>
        </div>
        {data.conflict && (
          <div className="mb-3 flex items-center gap-2 rounded-lg border border-warning/40 bg-warning-soft px-3 py-2 text-sm text-ink">
            <AlertTriangle className="h-4 w-4 text-warning" aria-hidden />
            Signals disagree — the system recommends escalation rather than picking a winner.
          </div>
        )}
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {hs && (["technician", "telemetry", "quality", "supervisor"] as const).map((axis) => (
            <div key={axis} className="rounded-lg border border-line bg-surface-2 p-3">
              <div className="label capitalize">{axis}</div>
              {axis === "supervisor" ? (
                <div className="mt-1.5 text-[12px] text-ink-mut">not captured yet</div>
              ) : (
                <div className="mt-1.5">
                  <Badge tone={statusTone(axis, hs[axis])}>{hs[axis].replace(/_/g, " ")}</Badge>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* reasons */}
      {data.reasons && data.reasons.length > 0 && (
        <div className="rounded-xl border border-line bg-surface-1 p-5">
          <div className="label mb-2">Why this disposition</div>
          <ul className="space-y-1.5 text-sm text-ink">
            {data.reasons.map((r, i) => (
              <li key={i} className="flex gap-2"><span className="text-ink-mut">·</span>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {data.basis && <p className="px-1 text-[11px] text-ink-mut">{data.basis}</p>}
    </section>
  );
}
