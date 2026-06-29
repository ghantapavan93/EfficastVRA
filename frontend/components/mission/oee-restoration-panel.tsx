"use client";

import { AlertTriangle, CheckCircle2, Gauge } from "lucide-react";
import { useOeeRestoration } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Badge, Chip } from "@/components/forge/primitives";
import type { OeeFactor } from "@/lib/types";

/** Circular OEE gauge (Efficast renders OEE as a donut). Arc = recovered OEE; ghost tick = baseline. */
function OeeRing({ oee, baseline, restored }: { oee: number; baseline: number; restored: boolean }) {
  const R = 46;
  const C = 2 * Math.PI * R;
  const frac = Math.max(0, Math.min(1, oee / 100));
  const stroke = restored ? "var(--verified)" : "var(--warning)";
  // baseline marker angle (from 12 o'clock, clockwise)
  const ba = (Math.max(0, Math.min(1, baseline / 100))) * 2 * Math.PI - Math.PI / 2;
  const bx = 60 + R * Math.cos(ba);
  const by = 60 + R * Math.sin(ba);
  return (
    <svg viewBox="0 0 120 120" className="h-32 w-32" role="img" aria-label={`Recovered OEE ${oee}% of baseline ${baseline}%`}>
      <circle cx="60" cy="60" r={R} fill="none" stroke="var(--line)" strokeWidth="9" />
      <circle
        cx="60" cy="60" r={R} fill="none" stroke={stroke} strokeWidth="9" strokeLinecap="round"
        strokeDasharray={C} strokeDashoffset={C * (1 - frac)}
        transform="rotate(-90 60 60)" style={{ transition: "stroke-dashoffset 1s cubic-bezier(.22,1,.36,1)" }}
      />
      {/* baseline tick */}
      <circle cx={bx} cy={by} r="3.5" fill="var(--ink-hi)" stroke="var(--surface-1)" strokeWidth="1.5" />
      <text x="60" y="56" textAnchor="middle" className="mono" fontSize="22" fontWeight="700" fill="var(--ink-hi)">
        {oee.toFixed(0)}%
      </text>
      <text x="60" y="72" textAnchor="middle" fontSize="9" fill="var(--ink-mut)" letterSpacing="1.5">
        OEE · A×P×Q
      </text>
    </svg>
  );
}

function FactorBar({ f }: { f: OeeFactor }) {
  const base = f.baseline ?? 0;
  const rec = f.recovered ?? 0;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[12px]">
        <span className="flex items-center gap-1.5 text-ink">
          {f.restored ? (
            <CheckCircle2 className="h-3.5 w-3.5 text-verified" aria-hidden />
          ) : (
            <AlertTriangle className="h-3.5 w-3.5 text-warning" aria-hidden />
          )}
          {f.label}
        </span>
        <span className="mono text-ink-mut">
          {base.toFixed(0)}% <span className="text-ink-mut">→</span>{" "}
          <span className={f.restored ? "text-verified" : "text-warning"}>{rec.toFixed(0)}%</span>
        </span>
      </div>
      <div className="relative h-1.5 overflow-hidden rounded-full bg-surface-3">
        {/* baseline ghost */}
        <div className="absolute inset-y-0 left-0 rounded-full bg-line-strong" style={{ width: `${base}%` }} />
        {/* recovered fill */}
        <div
          className={cn("absolute inset-y-0 left-0 rounded-full transition-[width] duration-700",
            f.restored ? "bg-verified" : "bg-warning")}
          style={{ width: `${rec}%` }}
        />
      </div>
    </div>
  );
}

/** Smoothed OEE-over-cycles trajectory — shows the dip on relapse and the climb back to baseline. */
function Trajectory({ points, baseline }: { points: { cycle: number; oee: number | null }[]; baseline: number }) {
  const pts = points.filter((p) => p.oee != null) as { cycle: number; oee: number }[];
  if (pts.length < 2) return null;
  const W = 320, H = 64, pad = 4;
  const n = pts.length;
  const x = (i: number) => pad + (i * (W - 2 * pad)) / (n - 1);
  const y = (o: number) => pad + (1 - o) * (H - 2 * pad); // o in [0,1]
  const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.oee).toFixed(1)}`).join(" ");
  const by = y(baseline / 100);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-16 w-full" preserveAspectRatio="none" role="img" aria-label="OEE trajectory across the verification window">
      <line x1={pad} x2={W - pad} y1={by} y2={by} stroke="var(--ink-hi)" strokeDasharray="3 4" strokeWidth="1" opacity="0.5" />
      <path d={line} fill="none" stroke="var(--agent)" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}

export function OeeRestorationPanel({ incidentId }: { incidentId: string }) {
  const { data } = useOeeRestoration(incidentId, 5000);
  if (!data) return null;
  if (!data.available) {
    return (
      <section className="rounded-xl border border-line bg-surface-1 p-6 text-sm text-ink-mut">
        {data.reason ?? "OEE restoration is available once the verification window has cycles."}
      </section>
    );
  }
  const restored = !!data.restored;
  const rec = data.recovered_oee?.oee_pct ?? 0;
  const base = data.baseline_oee?.oee_pct ?? 0;

  return (
    <section className="alive space-y-4 rounded-xl border border-line-strong bg-surface-1 p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Gauge className="h-4 w-4 text-agent" aria-hidden />
          <h3 className="text-sm font-semibold text-ink-hi">OEE restoration</h3>
          <span className="text-[12px] text-ink-mut">verification lens · advisory</span>
        </div>
        <Badge tone={restored ? "verified" : "warning"}>
          {restored ? <CheckCircle2 className="h-3 w-3" aria-hidden /> : <AlertTriangle className="h-3 w-3" aria-hidden />}
          {restored ? "OEE restored" : "OEE not fully restored"}
        </Badge>
      </div>

      <p className="text-sm text-ink">{data.headline}</p>

      <div className="grid items-center gap-5 sm:grid-cols-[auto_1fr]">
        <div className="flex flex-col items-center gap-1">
          <OeeRing oee={rec} baseline={base} restored={restored} />
          <div className="flex items-center gap-2 text-[11px] text-ink-mut">
            <span className="mono">baseline {base.toFixed(0)}%</span>
            <span className={cn("mono", (data.delta_pct ?? 0) >= 0 ? "text-verified" : "text-failure")}>
              {(data.delta_pct ?? 0) >= 0 ? "+" : ""}{(data.delta_pct ?? 0).toFixed(1)}
            </span>
          </div>
        </div>
        <div className="space-y-2.5">
          {(data.factors ?? []).map((f) => <FactorBar key={f.key} f={f} />)}
        </div>
      </div>

      <div>
        <div className="mb-1 flex items-center justify-between">
          <div className="label">OEE across the verification window</div>
          <Chip>world-class {data.world_class_oee_pct ?? 85}%</Chip>
        </div>
        <Trajectory points={data.trajectory ?? []} baseline={base} />
        <p className="mt-0.5 text-[11px] text-ink-mut">
          Dashed line = baseline OEE. A closed work order is not proof OEE returned — this recomputes it.
        </p>
      </div>

      {data.basis && <p className="border-t border-line pt-3 text-[11px] text-ink-mut">{data.basis}</p>}
    </section>
  );
}
