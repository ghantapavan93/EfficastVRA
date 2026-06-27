"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Gauge, ShieldAlert } from "lucide-react";
import { useClosureRisk } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Badge, Chip, ProgressBar } from "@/components/forge/primitives";
import type { Tone } from "@/lib/state-meta";
import type { FcrsFactor } from "@/lib/types";

const BAND: Record<string, { tone: Tone; label: string; cssVar: string }> = {
  low: { tone: "verified", label: "Low risk", cssVar: "var(--verified)" },
  elevated: { tone: "warning", label: "Elevated risk", cssVar: "var(--warning)" },
  high: { tone: "failure", label: "High risk", cssVar: "var(--failure)" },
};

const R = 100;
const ARC = Math.PI * R; // length of the top semicircle

function factorTone(v: number): Tone {
  return v >= 0.6 ? "failure" : v >= 0.3 ? "warning" : "verified";
}

export function ClosureRiskPanel({ incidentId }: { incidentId: string }) {
  const { data } = useClosureRisk(incidentId, 3000);
  const [shown, setShown] = useState(false);
  useEffect(() => setShown(true), []);

  if (!data) return null;
  if (!data.available) {
    return (
      <section className="rounded-xl border border-line bg-surface-1 p-6 text-sm text-ink-mut">
        Closure risk is available once a Recovery Contract is drafted.
      </section>
    );
  }
  const band = BAND[data.band ?? "low"] ?? BAND.low;
  const risk = data.risk ?? 0;
  const offset = shown ? ARC * (1 - risk) : ARC; // animate fill on mount

  return (
    <section className="rounded-xl border border-line bg-surface-1 p-4" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Gauge className="h-4 w-4 text-agent" aria-hidden />
          <h3 className="text-sm font-semibold text-ink-hi">Closure risk</h3>
          <span className="text-[12px] text-ink-mut">false‑closure · advisory</span>
        </div>
        <Badge tone={band.tone}>
          {band.tone === "verified" ? <CheckCircle2 className="h-3 w-3" aria-hidden /> :
           band.tone === "warning" ? <AlertTriangle className="h-3 w-3" aria-hidden /> :
           <ShieldAlert className="h-3 w-3" aria-hidden />}
          {band.label}
        </Badge>
      </div>

      <div className="mt-3 grid gap-4 sm:grid-cols-[240px_1fr]">
        {/* radial gauge */}
        <figure className="grid place-items-center">
          <svg viewBox="0 0 240 138" className="w-full max-w-[260px]" role="img"
               aria-label={`False-closure risk ${data.risk_pct}%, ${band.label}`}>
            <path d="M 20 120 A 100 100 0 0 1 220 120" fill="none" stroke="var(--surface-3)" strokeWidth="14" strokeLinecap="round" />
            <path
              d="M 20 120 A 100 100 0 0 1 220 120" fill="none" stroke={band.cssVar} strokeWidth="14" strokeLinecap="round"
              strokeDasharray={ARC} strokeDashoffset={offset}
              style={{ transition: "stroke-dashoffset 1.1s cubic-bezier(.22,1,.36,1)" }}
            />
            {/* band-threshold ticks at 25% and 60% */}
            {[0.25, 0.6].map((f) => {
              const a = Math.PI - f * Math.PI;
              return (
                <line
                  key={f}
                  x1={120 + (R - 9) * Math.cos(a)} y1={120 - (R - 9) * Math.sin(a)}
                  x2={120 + (R + 9) * Math.cos(a)} y2={120 - (R + 9) * Math.sin(a)}
                  stroke="var(--ink-mut)" strokeWidth="1.5" opacity="0.5"
                />
              );
            })}
            <text x="120" y="104" textAnchor="middle" className="mono" fill="var(--ink-hi)" fontSize="34" fontWeight="600">
              {data.risk_pct}%
            </text>
            <text x="120" y="122" textAnchor="middle" fill="var(--ink-mut)" fontSize="11">false‑closure risk</text>
          </svg>
        </figure>

        {/* recommendation + factors */}
        <div className="space-y-3">
          <div className={cn("rounded-lg border p-3 text-sm",
            band.tone === "failure" ? "border-failure/40 bg-failure-soft text-failure" :
            band.tone === "warning" ? "border-line bg-surface-2 text-ink" : "border-verified/30 bg-verified-soft text-ink")}>
            {data.recommendation}
            {data.dominant_driver && (
              <span className="mt-1 block text-[11px] text-ink-mut">Dominant driver: {data.dominant_driver}</span>
            )}
          </div>

          <div className="space-y-2">
            <div className="label">Contributing factors</div>
            {(data.factors ?? []).map((f: FcrsFactor) => (
              <div key={f.key} className="text-xs">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-ink">{f.label}</span>
                  <span className="mono text-ink-mut">+{Math.round(f.contribution * 100)}%</span>
                </div>
                <div className="mt-1"><ProgressBar value={f.value * 100} tone={factorTone(f.value)} /></div>
                {f.detail && <p className="mt-0.5 text-[10px] text-ink-mut">{f.detail}</p>}
              </div>
            ))}
          </div>
        </div>
      </div>

      {data.basis && <p className="mt-3 text-[11px] text-ink-mut">{data.basis}</p>}
    </section>
  );
}
