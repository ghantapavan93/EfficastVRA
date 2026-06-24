"use client";

import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { SyntheticBadge } from "@/components/shell/synthetic-badge";

const STAGES = [
  { label: "Intervention completed", tone: "var(--text-mut)" },
  { label: "Monitoring", tone: "var(--agent)" },
  { label: "Apparent recovery", tone: "var(--agent)" },
  { label: "Cycle-17 relapse", tone: "var(--failure)" },
  { label: "Reopened", tone: "var(--failure)" },
  { label: "Verified", tone: "var(--verified)" },
];

export default function Landing() {
  const reduce = useReducedMotion();
  return (
    <div className="app-canvas grid-motif relative min-h-screen overflow-hidden">
      {/* subtle top illumination */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-80 bg-[radial-gradient(60%_120%_at_50%_-20%,var(--brand-soft),transparent)]" />
      <header className="relative flex items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-[10px] bg-brand-soft text-brand">
            <ShieldCheck className="h-4 w-4" />
          </span>
          <span className="text-sm font-semibold tracking-tight text-ink-hi">Verified Recovery Agent</span>
        </div>
        <SyntheticBadge />
      </header>

      <main className="relative mx-auto flex max-w-5xl flex-col items-center px-6 pt-10 text-center md:pt-16">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="mb-4 inline-flex items-center gap-2 rounded-pill border border-line bg-surface-1 px-3 py-1 text-[11px] text-ink-mut"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-agent" /> Industrial recovery verification · designed for 2032
        </motion.div>

        <h1 className="max-w-3xl text-4xl font-semibold leading-[1.05] tracking-tight text-ink-hi md:text-6xl">
          Work completed is not
          <br />
          <span className="text-brand">production recovered.</span>
        </h1>
        <p className="mt-5 max-w-xl text-balance text-[15px] leading-relaxed text-ink-mut">
          Verified Recovery monitors what happens <em>after</em> an intervention, gathers the evidence
          required for closure, and reopens the incident when the factory does not recover as expected.
        </p>

        <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/missions"
            className="inline-flex h-11 items-center gap-2 rounded-[10px] bg-brand px-5 text-sm font-semibold text-black transition-transform hover:scale-[1.02]"
          >
            Open live recovery mission <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/missions"
            className="inline-flex h-11 items-center rounded-[10px] border border-line-strong px-5 text-sm text-ink hover:bg-surface-2"
          >
            View how verification works
          </Link>
        </div>

        {/* Recovery trajectory */}
        <div className="mt-14 w-full max-w-3xl rounded-xl border border-line bg-raised/70 p-4">
          <HeroTrajectory reduce={!!reduce} />
          <div className="mt-3 flex flex-wrap items-center justify-center gap-x-5 gap-y-1.5">
            {STAGES.map((s, i) => (
              <motion.span
                key={s.label}
                initial={{ opacity: reduce ? 1 : 0.3 }}
                animate={{ opacity: 1 }}
                transition={{ delay: reduce ? 0 : 0.5 + i * 0.45 }}
                className="inline-flex items-center gap-1.5 text-[11px] text-ink-mut"
              >
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: s.tone }} />
                {s.label}
              </motion.span>
            ))}
          </div>
        </div>
        <p className="mt-6 pb-12 text-[11px] text-ink-faint">
          Independent Efficast-aligned prototype · synthetic data · no physical machine control.
        </p>
      </main>
    </div>
  );
}

function HeroTrajectory({ reduce }: { reduce: boolean }) {
  // Vibration-like trajectory: degraded → improving → spike at 17 → reopened dip → verified-low.
  const W = 720;
  const H = 180;
  const pre = "M 20 60 C 90 70, 120 120, 180 124 C 230 128, 300 126, 330 122";
  const spike = "C 345 120, 352 56, 366 52 C 380 50, 388 110, 410 116"; // cycle-17 relapse
  const recover = "C 470 122, 540 140, 620 142 C 660 143, 690 143, 700 143";
  const threshold = 116;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Recovery trajectory: vibration improves, F27 recurs at cycle 17, incident reopens, then verified recovery over 30 stable cycles.">
      <line x1={20} x2={700} y1={threshold} y2={threshold} stroke="var(--warning)" strokeDasharray="4 5" strokeWidth={1} opacity={0.55} />
      <text x={700} y={threshold - 6} fontSize={9} fill="var(--text-faint)" textAnchor="end">vibration limit 4.0 mm/s</text>
      {/* pre-recovery + spike (agent → failure) */}
      <motion.path
        d={`${pre} ${spike}`}
        fill="none"
        stroke="var(--agent)"
        strokeWidth={2.5}
        strokeLinecap="round"
        initial={reduce ? false : { pathLength: 0 }}
        animate={reduce ? undefined : { pathLength: 1 }}
        transition={{ duration: 2.2, ease: "easeInOut" }}
      />
      {/* recovery (verified) */}
      <motion.path
        d={`M 410 116 ${recover}`}
        fill="none"
        stroke="var(--verified)"
        strokeWidth={2.5}
        strokeLinecap="round"
        initial={reduce ? false : { pathLength: 0, opacity: 0 }}
        animate={reduce ? undefined : { pathLength: 1, opacity: 1 }}
        transition={{ duration: 1.6, ease: "easeInOut", delay: 2.4 }}
      />
      {/* cycle-17 marker */}
      <motion.g initial={reduce ? false : { opacity: 0 }} animate={reduce ? undefined : { opacity: 1 }} transition={{ delay: 1.7 }}>
        <line x1={366} x2={366} y1={20} y2={160} stroke="var(--failure)" strokeDasharray="3 3" strokeWidth={1} opacity={0.7} />
        <circle cx={366} cy={52} r={4} fill="var(--failure)" />
        <text x={372} y={34} fontSize={10} fill="var(--failure)">F27 · cycle 17</text>
      </motion.g>
    </svg>
  );
}
