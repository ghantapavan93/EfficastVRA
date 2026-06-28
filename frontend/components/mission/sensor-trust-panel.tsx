"use client";

import { AlertTriangle, Check, HelpCircle, ShieldAlert, ShieldCheck, X } from "lucide-react";
import { useSensorTrust } from "@/lib/hooks";
import { Badge, Chip } from "@/components/forge/primitives";
import type { Tone } from "@/lib/state-meta";

const TRUST: Record<string, { tone: Tone; label: string }> = {
  TRUSTED: { tone: "verified", label: "Trusted" },
  DEGRADED: { tone: "warning", label: "Degraded" },
  UNTRUSTED: { tone: "failure", label: "Untrusted" },
  UNKNOWN: { tone: "steel", label: "Unknown" },
};

export function SensorTrustPanel({ incidentId }: { incidentId: string }) {
  const { data } = useSensorTrust(incidentId, 4000);
  if (!data) return null;
  if (!data.available) {
    return <section className="rounded-xl border border-line bg-surface-1 p-6 text-sm text-ink-mut">
      Sensor trust is available once monitoring begins.
    </section>;
  }
  const t = TRUST[data.status ?? "UNKNOWN"] ?? TRUST.UNKNOWN;
  return (
    <section className="space-y-4">
      <div className="rounded-xl border border-line bg-surface-1 p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-agent" aria-hidden />
            <h3 className="text-sm font-semibold text-ink-hi">Sensor trust</h3>
            <span className="text-[12px] text-ink-mut">data-trust gate · advisory</span>
          </div>
          <Badge tone={t.tone}>
            {t.tone === "verified" ? <ShieldCheck className="h-3 w-3" aria-hidden /> :
             t.tone === "failure" ? <ShieldAlert className="h-3 w-3" aria-hidden /> :
             t.tone === "warning" ? <AlertTriangle className="h-3 w-3" aria-hidden /> :
             <HelpCircle className="h-3 w-3" aria-hidden />}
            {t.label}
          </Badge>
        </div>
        <p className="mt-2 text-sm text-ink">
          {data.satisfies_hard_conditions
            ? "Sensors are trusted — they may satisfy hard recovery conditions."
            : "A measurement we can't trust can't satisfy a hard recovery condition — this caps recovery at INSUFFICIENT_EVIDENCE."}
        </p>
        {data.reasons && data.reasons.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">{data.reasons.map((r, i) => <Chip key={i}>{r}</Chip>)}</div>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {(data.per_metric ?? []).map((m) => {
          const mt = TRUST[m.status] ?? TRUST.UNKNOWN;
          return (
            <div key={m.metric} className="rounded-lg border border-line bg-surface-1 p-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-ink">{m.metric.replace(/_/g, " ")}</span>
                <Badge tone={mt.tone}>{mt.label}</Badge>
              </div>
              <div className="mt-2 space-y-1">
                {m.checks.map((c) => (
                  <div key={c.name} className="flex items-center gap-1.5 text-[11px] text-ink-mut">
                    {c.ok ? <Check className="h-3 w-3 text-verified" aria-hidden /> : <X className="h-3 w-3 text-failure" aria-hidden />}
                    <span>{c.name.replace(/_/g, " ")}</span>
                    {c.detail && <span className="mono ml-auto">{c.detail}</span>}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {data.basis && <p className="px-1 text-[11px] text-ink-mut">{data.basis}</p>}
    </section>
  );
}
