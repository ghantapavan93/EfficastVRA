"use client";

import { useMemo } from "react";
import type { TimelineCycle } from "@/lib/types";

type MetricKey = "vibration" | "temperature" | "cycle_time" | "scrap_pct";

interface Props {
  cycles: TimelineCycle[];
  metric: MetricKey;
  label: string;
  unit: string;
  threshold?: number | null;
  baseline?: number | null;
  height?: number;
}

/** Hand-built SVG trajectory: actual line + threshold + baseline + cycle markers + recurrence event.
 * Includes an accessible text summary. No chart library (keeps the bundle small, the visual exact). */
export function RecoveryTrajectory({
  cycles,
  metric,
  label,
  unit,
  threshold = null,
  baseline = null,
  height = 140,
}: Props) {
  const W = 640;
  const H = height;
  const padX = 36;
  const padY = 16;

  const points = useMemo(
    () => cycles.filter((c) => c[metric] !== null).map((c) => ({ x: c.cycle_index, y: c[metric] as number, fault: c.fault_code, recurrence: c.is_recurrence })),
    [cycles, metric],
  );

  if (points.length === 0) {
    return (
      <div className="flex h-[140px] items-center justify-center rounded-lg border border-dashed border-line text-xs text-ink-mut">
        No cycles observed yet
      </div>
    );
  }

  const xs = points.map((p) => p.x);
  const all = [...points.map((p) => p.y), ...(threshold ? [threshold] : []), ...(baseline ? [baseline] : [])];
  const maxX = Math.max(...xs, 1);
  const yMin = Math.min(...all) * 0.92;
  const yMax = Math.max(...all) * 1.08;

  const sx = (x: number) => padX + ((x - 1) / Math.max(maxX - 1, 1)) * (W - padX * 2);
  const sy = (y: number) => H - padY - ((y - yMin) / Math.max(yMax - yMin, 0.0001)) * (H - padY * 2);

  const path = points.map((p, i) => `${i === 0 ? "M" : "L"} ${sx(p.x).toFixed(1)} ${sy(p.y).toFixed(1)}`).join(" ");
  const recurrence = points.find((p) => p.recurrence);
  const last = points[points.length - 1];
  const violated = !!recurrence;

  const summary = `${label}: ${points.length} cycles observed, latest ${last.y}${unit}${
    threshold ? `, threshold ${threshold}${unit}` : ""
  }${recurrence ? `, fault recurrence at cycle ${recurrence.x}` : ""}.`;

  return (
    <figure className="overflow-hidden rounded-lg border border-line bg-raised">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={summary} className="w-full" preserveAspectRatio="none" style={{ height }}>
        {/* threshold band */}
        {threshold !== null && (
          <>
            <line x1={padX} x2={W - padX} y1={sy(threshold)} y2={sy(threshold)} stroke="var(--warning)" strokeDasharray="4 4" strokeWidth={1} opacity={0.7} />
            <rect x={padX} y={padY} width={W - padX * 2} height={Math.max(sy(threshold) - padY, 0)} fill="var(--verified-soft)" opacity={0.5} />
          </>
        )}
        {baseline !== null && (
          <line x1={padX} x2={W - padX} y1={sy(baseline)} y2={sy(baseline)} stroke="var(--text-faint)" strokeDasharray="2 4" strokeWidth={1} opacity={0.6} />
        )}
        {/* recurrence vertical marker */}
        {recurrence && (
          <line x1={sx(recurrence.x)} x2={sx(recurrence.x)} y1={padY} y2={H - padY} stroke="var(--failure)" strokeWidth={1.5} strokeDasharray="3 3" opacity={0.8} />
        )}
        {/* actual line */}
        <path d={path} fill="none" stroke={violated ? "var(--failure)" : "var(--agent)"} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" className="transition-all duration-500" />
        {/* points */}
        {points.map((p) => (
          <circle
            key={p.x}
            cx={sx(p.x)}
            cy={sy(p.y)}
            r={p.recurrence ? 4 : 2}
            fill={p.recurrence ? "var(--failure)" : p.fault ? "var(--failure)" : "var(--agent)"}
          />
        ))}
        {/* axis labels */}
        <text x={padX} y={H - 2} fontSize={9} fill="var(--text-faint)">c1</text>
        <text x={W - padX} y={H - 2} fontSize={9} fill="var(--text-faint)" textAnchor="end">c{maxX}</text>
      </svg>
      <figcaption className="flex items-center justify-between border-t border-line px-3 py-1.5 text-[11px] text-ink-mut">
        <span className="mono">{label} · {unit}</span>
        {recurrence && <span className="mono text-failure">F27 recurrence · cycle {recurrence.x}</span>}
        {!recurrence && <span className="mono">latest {last.y}{unit}</span>}
      </figcaption>
    </figure>
  );
}
