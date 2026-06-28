"use client";

import { useQuery } from "@tanstack/react-query";
import { Gauge, Repeat } from "lucide-react";
import { CountUp } from "@/components/forge/count-up";

interface RelPoint {
  p_pred: number;
  observed: number;
  count: number;
}
interface Calib {
  available: boolean;
  trials: number;
  seed: number;
  brier: number;
  auc: number;
  accuracy: number;
  early_warning_rate: number;
  n_genuine: number;
  n_false: number;
  reliability_curve: RelPoint[];
  basis: string;
}

function useCalibration() {
  return useQuery({
    queryKey: ["calibration"],
    queryFn: async () => {
      const r = await fetch("/api/calibration", { cache: "no-store", headers: { "X-VRA-User": "s.vega" } });
      return r.json() as Promise<Calib>;
    },
    refetchInterval: false,
  });
}

const S = 320;
const M = 38;
const R = 14;
const PW = S - M - R;
const PH = S - M - R;
const px = (p: number) => M + p * PW;
const py = (o: number) => S - M - o * PH;

export function CalibrationPanel() {
  const { data } = useCalibration();
  if (!data || !data.available) return null;
  const pts = [...data.reliability_curve].sort((a, b) => a.p_pred - b.p_pred);
  const maxCount = Math.max(1, ...pts.map((p) => p.count));
  const line = pts.map((p) => `${px(p.p_pred).toFixed(1)},${py(p.observed).toFixed(1)}`).join(" ");

  return (
    <section className="alive relative mt-4 overflow-hidden rounded-xl border border-line bg-surface-1 p-4">
      <style>{`@keyframes calDraw{to{stroke-dashoffset:0}}@keyframes calFade{to{opacity:1}}@keyframes calDrift{0%{transform:translate3d(-6%,-4%,0)}100%{transform:translate3d(6%,4%,0)}}`}</style>
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.07]"
        style={{
          background: "radial-gradient(55% 55% at 28% 18%, var(--agent), transparent 70%)",
          animation: "calDrift 16s ease-in-out infinite alternate",
        }}
      />

      <div className="relative flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Gauge className="h-4 w-4 text-agent" aria-hidden />
          <h3 className="text-sm font-semibold text-ink-hi">Signature calibration</h3>
          <span className="text-[12px] text-ink-mut">falsifiability · advisory</span>
        </div>
        <span className="inline-flex items-center gap-1.5 text-[11px] text-ink-mut">
          <Repeat className="h-3 w-3" aria-hidden /> {data.trials} scenarios · seed {data.seed} · reproducible
        </span>
      </div>

      <div className="relative mt-3 grid gap-4 md:grid-cols-[320px_1fr]">
        <figure className="rounded-lg border border-line bg-surface-2 p-2">
          <svg
            viewBox={`0 0 ${S} ${S}`}
            className="w-full"
            role="img"
            aria-label={`Reliability diagram. Brier ${data.brier}, AUC ${data.auc}.`}
          >
            <defs>
              <pattern id="cal-grid" width={PW / 10} height={PH / 10} patternUnits="userSpaceOnUse">
                <path
                  d={`M ${PW / 10} 0 L 0 0 0 ${PH / 10}`}
                  fill="none"
                  stroke="var(--line)"
                  strokeWidth="0.5"
                  opacity="0.5"
                />
              </pattern>
              <linearGradient id="cal-area" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--agent)" stopOpacity="0.22" />
                <stop offset="100%" stopColor="var(--agent)" stopOpacity="0" />
              </linearGradient>
            </defs>

            <rect x={M} y={R} width={PW} height={PH} fill="url(#cal-grid)" />
            <line
              x1={px(0)}
              y1={py(0)}
              x2={px(1)}
              y2={py(1)}
              stroke="var(--ink-mut)"
              strokeWidth="1"
              strokeDasharray="4 4"
              opacity="0.55"
            />
            <line x1={M} y1={R} x2={M} y2={S - M} stroke="var(--line)" strokeWidth="1" />
            <line x1={M} y1={S - M} x2={S - R} y2={S - M} stroke="var(--line)" strokeWidth="1" />

            {pts.length > 1 && (
              <polygon
                points={`${px(pts[0].p_pred).toFixed(1)},${py(0)} ${line} ${px(pts[pts.length - 1].p_pred).toFixed(1)},${py(0)}`}
                fill="url(#cal-area)"
              />
            )}
            <polyline
              points={line}
              fill="none"
              stroke="var(--agent)"
              strokeWidth="2.5"
              strokeLinejoin="round"
              strokeLinecap="round"
              strokeDasharray="1200"
              strokeDashoffset="1200"
              style={{ animation: "calDraw 1.4s ease-out forwards" }}
            />
            {pts.map((p, i) => {
              const err = Math.abs(p.p_pred - p.observed);
              const col = err < 0.1 ? "var(--verified)" : err < 0.25 ? "var(--agent)" : "var(--failure)";
              return (
                <circle
                  key={i}
                  cx={px(p.p_pred)}
                  cy={py(p.observed)}
                  r={3 + Math.sqrt(p.count / maxCount) * 5}
                  fill={col}
                  stroke="var(--surface-1)"
                  strokeWidth="1.5"
                  style={{ opacity: 0, animation: `calFade .5s ease ${0.7 + i * 0.08}s forwards` }}
                >
                  <title>{`predicted ${(p.p_pred * 100).toFixed(0)}% → observed ${(p.observed * 100).toFixed(0)}% (n=${p.count})`}</title>
                </circle>
              );
            })}

            <text x={M + PW / 2} y={S - 6} textAnchor="middle" fill="var(--ink-mut)" fontSize="10">
              predicted P(recovery holds)
            </text>
            <text
              x={12}
              y={R + PH / 2}
              textAnchor="middle"
              fill="var(--ink-mut)"
              fontSize="10"
              transform={`rotate(-90 12 ${R + PH / 2})`}
            >
              observed frequency
            </text>
          </svg>
          <figcaption className="mt-1 px-1 text-[11px] text-ink-mut">
            On the dashed diagonal = perfectly calibrated. Dot size = scenarios in the bin.
          </figcaption>
        </figure>

        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <Metric label="Brier score" value={data.brier} decimals={3} hint="lower is better" tone={data.brier < 0.15 ? "verified" : data.brier < 0.25 ? "agent" : "failure"} />
            <Metric label="ROC AUC" value={data.auc} decimals={3} hint="0.5 chance → 1.0 perfect" tone={data.auc > 0.85 ? "verified" : "agent"} />
            <Metric label="Accuracy" value={Math.round(data.accuracy * 100)} suffix="%" hint="@ 0.5 threshold" tone="agent" />
            <Metric label="Early warning" value={Math.round(data.early_warning_rate * 100)} suffix="%" hint="latent relapses flagged" tone={data.early_warning_rate > 0.7 ? "verified" : "agent"} />
          </div>
          <div className="rounded-lg border border-line bg-surface-2 p-3 text-[12px] text-ink-mut">
            <div className="label mb-1 text-ink">What this proves</div>
            The Expected Recovery Signature is <span className="text-ink">falsifiable</span>: across{" "}
            {data.n_genuine} genuine and {data.n_false} latent-relapse scenarios it separates them with AUC{" "}
            {data.auc.toFixed(2)} and a Brier of {data.brier.toFixed(2)} — and the curve honestly shows where
            it is over-confident rather than claiming perfection.
          </div>
          <p className="text-[11px] text-ink-mut">{data.basis}</p>
        </div>
      </div>
    </section>
  );
}

function Metric({
  label,
  value,
  decimals = 0,
  suffix = "",
  hint,
  tone,
}: {
  label: string;
  value: number;
  decimals?: number;
  suffix?: string;
  hint: string;
  tone: "verified" | "agent" | "failure";
}) {
  const color = tone === "verified" ? "text-verified" : tone === "failure" ? "text-failure" : "text-ink-hi";
  return (
    <div className="rounded-lg border border-line bg-surface-2 p-3">
      <div className="label">{label}</div>
      <div className={`mono mt-1 text-xl ${color}`}><CountUp value={value} decimals={decimals} suffix={suffix} /></div>
      <div className="text-[10px] text-ink-mut">{hint}</div>
    </div>
  );
}
