"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, Pause, Play, RotateCcw } from "lucide-react";
import { useTwin } from "@/lib/hooks";
import { ErrorState, LoadingState } from "@/components/forge/states";

const W = 720;
const H = 180;
const PAD = 28;

export function RecoveryTwin({ incidentId }: { incidentId: string }) {
  const { data: t, isLoading, isError } = useTwin(incidentId);
  const [cur, setCur] = useState(0);
  const [playing, setPlaying] = useState(false);

  const frames = useMemo(() => t?.frames ?? [], [t]);
  const n = frames.length;

  useEffect(() => { setCur(0); setPlaying(false); }, [n]);
  useEffect(() => {
    if (!playing || n === 0) return;
    if (cur >= n - 1) { setPlaying(false); return; }
    const id = setTimeout(() => setCur((c) => Math.min(c + 1, n - 1)), 150);
    return () => clearTimeout(id);
  }, [playing, cur, n]);

  if (isLoading) return <LoadingState label="Loading recovery trajectory" />;
  if (isError) return <ErrorState message="Could not load the Recovery Twin." />;
  if (!t?.available) {
    return (
      <section className="rounded-xl border border-line bg-surface-1 p-6">
        <div className="label mb-1 flex items-center gap-1.5"><Activity className="h-3.5 w-3.5" /> Recovery Twin</div>
        <p className="text-sm text-ink-mut">{t?.reason ?? "No recovery trajectory yet."}</p>
      </section>
    );
  }

  const required = t.required_stable_cycles ?? 30;
  const vibMax = t.thresholds?.vibration_max ?? null;
  const vibBase = t.thresholds?.vibration_baseline ?? null;
  const vibVals = frames.map((f) => f.vibration).filter((v): v is number => v != null);
  const top = Math.max(...vibVals, vibMax ?? 0, vibBase ?? 0) * 1.18 || 10;

  const x = (i: number) => PAD + (i / Math.max(n - 1, 1)) * (W - 2 * PAD);
  const y = (v: number) => H - PAD - (Math.max(v, 0) / top) * (H - 2 * PAD);

  const pts = frames.map((f, i) => (f.vibration == null ? null : `${x(i)},${y(f.vibration)}`)).filter(Boolean) as string[];
  const ptsToCur = frames.slice(0, cur + 1).map((f, i) => (f.vibration == null ? null : `${x(i)},${y(f.vibration)}`)).filter(Boolean) as string[];

  const f = frames[cur];
  const relapses = (t.markers ?? []).filter((m) => m.kind === "relapse");
  const streakPct = Math.min(100, Math.round((f.stable_streak / required) * 100));
  const atRelapse = !!f.fault_code;

  return (
    <section className="space-y-4 rounded-xl border border-line bg-surface-1 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="label mb-1 flex items-center gap-1.5"><Activity className="h-3.5 w-3.5 text-agent" /> Recovery Twin · live trajectory replay</div>
          <p className="max-w-2xl text-sm text-ink-mut">{t.summary}</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => { if (cur >= n - 1) setCur(0); setPlaying((p) => !p); }}
            className="inline-flex h-9 items-center gap-1.5 rounded-[10px] bg-agent px-3 text-sm font-semibold text-black transition-transform hover:scale-[1.02]">
            {playing ? <><Pause className="h-4 w-4" /> Pause</> : <><Play className="h-4 w-4" /> Replay</>}
          </button>
          <button onClick={() => { setCur(0); setPlaying(false); }}
            className="grid h-9 w-9 place-items-center rounded-[10px] border border-line text-ink-mut hover:text-ink" aria-label="Reset">
            <RotateCcw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* chart */}
      <div className="rounded-lg border border-line bg-canvas/60 p-2">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Vibration over cycles">
          {vibMax != null && (
            <g>
              <line x1={PAD} x2={W - PAD} y1={y(vibMax)} y2={y(vibMax)} stroke="var(--failure)" strokeDasharray="4 4" strokeOpacity="0.6" />
              <text x={W - PAD} y={y(vibMax) - 4} textAnchor="end" fontSize="10" fill="var(--failure)" opacity="0.8">max {vibMax} mm/s</text>
            </g>
          )}
          {vibBase != null && (
            <line x1={PAD} x2={W - PAD} y1={y(vibBase)} y2={y(vibBase)} stroke="var(--verified)" strokeDasharray="2 5" strokeOpacity="0.5" />
          )}
          {/* full faint trajectory */}
          {pts.length > 1 && <polyline points={pts.join(" ")} fill="none" stroke="var(--agent)" strokeOpacity="0.22" strokeWidth="1.5" />}
          {/* drawn-so-far */}
          {ptsToCur.length > 1 && <polyline points={ptsToCur.join(" ")} fill="none" stroke="var(--agent)" strokeWidth="2.5" />}
          {/* relapse markers */}
          {relapses.map((m) => {
            const fr = frames[m.index - 1];
            if (!fr || fr.vibration == null) return null;
            return <circle key={m.index} cx={x(m.index - 1)} cy={y(fr.vibration)} r="4.5" fill="var(--failure)" />;
          })}
          {/* cursor */}
          <line x1={x(cur)} x2={x(cur)} y1={PAD - 6} y2={H - PAD} stroke="var(--ink-mut)" strokeOpacity="0.5" />
          {f.vibration != null && <circle cx={x(cur)} cy={y(f.vibration)} r="5" fill={atRelapse ? "var(--failure)" : "var(--verified)"} stroke="var(--canvas)" strokeWidth="2" />}
        </svg>
      </div>

      {/* scrubber */}
      <input type="range" min={0} max={Math.max(n - 1, 0)} value={cur}
        onChange={(e) => { setPlaying(false); setCur(Number(e.target.value)); }}
        className="w-full accent-agent" aria-label="Scrub cycles" />

      {/* readout */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Window · cycle" value={`W${f.window} · #${f.cycle}`} />
        <Stat label="Vibration" value={f.vibration != null ? `${f.vibration.toFixed(2)} mm/s` : "—"} tone={atRelapse ? "failure" : undefined} />
        <Stat label="Temperature" value={f.temperature != null ? `${f.temperature.toFixed(1)} °C` : "—"} />
        <Stat label={`Stable streak · ${required} req`} value={`${f.stable_streak}`} tone={atRelapse ? "failure" : f.stable_streak >= required ? "verified" : undefined} />
      </div>

      {/* streak bar */}
      <div>
        <div className="mb-1 flex items-center justify-between text-[11px] text-ink-mut">
          <span>Consecutive stable cycles</span>
          {atRelapse ? <span className="flex items-center gap-1 text-failure"><AlertTriangle className="h-3 w-3" /> {f.fault_code} recurred — streak reset</span>
            : <span className="mono">{f.stable_streak}/{required}</span>}
        </div>
        <div className="h-2 overflow-hidden rounded-pill bg-surface-3">
          <div className="h-full rounded-pill transition-all" style={{ width: `${atRelapse ? 100 : streakPct}%`, background: atRelapse ? "var(--failure)" : f.stable_streak >= required ? "var(--verified)" : "var(--agent)" }} />
        </div>
      </div>

      <p className="mono text-[11px] text-ink-faint">source · {f.source} · {t.basis}</p>
    </section>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "failure" | "verified" }) {
  const color = tone === "failure" ? "text-failure" : tone === "verified" ? "text-verified" : "text-ink-hi";
  return (
    <div className="rounded-lg border border-line bg-canvas/50 p-3">
      <div className="label mb-1">{label}</div>
      <div className={`mono text-lg font-semibold ${color}`}>{value}</div>
    </div>
  );
}
