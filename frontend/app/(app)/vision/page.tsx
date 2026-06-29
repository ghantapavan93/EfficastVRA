"use client";

import { Award, Boxes, Network, RefreshCw } from "lucide-react";
import { Reveal } from "@/components/forge/reveal";
import { MachineArt } from "@/components/forge/machine-art";

const MACHINES = [
  { kind: "conveyor" as const, label: "Conveyor-drive assembly", code: "CDX-220 · F27" },
  { kind: "press" as const, label: "Injection-molding press", code: "IMX-90 · E12" },
  { kind: "hydraulic" as const, label: "Hydraulic power unit", code: "HPU-50 · P09" },
];

/* ──────────────────────────── cinematic hero ──────────────────────────── */
function VisionHero() {
  return (
    <section className="relative overflow-hidden rounded-3xl border border-line-strong">
      <style>{`
        @keyframes cine-aurora { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }
        @keyframes cine-draw { 0%{stroke-dashoffset:1200} 42%{stroke-dashoffset:0} 86%{stroke-dashoffset:0} 100%{stroke-dashoffset:1200} }
        @keyframes cine-ring { 0%,42%{stroke-dashoffset:114} 58%{stroke-dashoffset:0} 86%{stroke-dashoffset:0} 100%{stroke-dashoffset:114} }
        @keyframes cine-seal { 0%,48%{opacity:0;transform:scale(.6)} 60%{opacity:1;transform:scale(1)} 84%{opacity:.85} 100%{opacity:0} }
        @keyframes cine-rise { 0%{transform:translateY(0);opacity:0} 30%{opacity:.7} 100%{transform:translateY(-60px);opacity:0} }
        @media (prefers-reduced-motion: reduce){ .cine *{animation:none !important} #cine-sig{stroke-dashoffset:0 !important} #cine-ring{stroke-dashoffset:0 !important} #cine-seal{opacity:1 !important;transform:none !important} }
      `}</style>

      {/* cinematic gradient backdrop */}
      <div className="cine pointer-events-none absolute inset-0" aria-hidden
        style={{
          background: "linear-gradient(115deg, #070b14 0%, #0b1322 35%, #0a1a24 60%, #0a0f18 100%)",
        }} />
      <div className="cine pointer-events-none absolute inset-0 opacity-70" aria-hidden
        style={{
          background: "radial-gradient(60% 90% at 18% 10%, rgba(76,125,255,0.28), transparent 60%), radial-gradient(55% 80% at 88% 30%, rgba(45,212,167,0.20), transparent 60%), radial-gradient(50% 70% at 60% 120%, rgba(245,165,36,0.12), transparent 60%)",
          backgroundSize: "200% 200%",
          animation: "cine-aurora 18s ease-in-out infinite",
        }} />
      {/* rising signal motes */}
      <div className="cine pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
        {[14, 32, 51, 68, 84].map((x, i) => (
          <span key={i} className="absolute h-1 w-1 rounded-full bg-agent"
            style={{ left: `${x}%`, bottom: "12%", animation: `cine-rise ${6 + i}s ease-in ${i * 1.3}s infinite`, opacity: 0.6 }} />
        ))}
      </div>

      {/* recovery-arc visual */}
      <svg className="cine absolute inset-x-0 bottom-0 h-[58%] w-full" viewBox="0 0 900 260" preserveAspectRatio="none" aria-hidden>
        <line x1="0" y1="150" x2="900" y2="150" stroke="var(--line)" strokeOpacity="0.4" strokeWidth="1" />
        <path id="cine-sig"
          d="M30,150 L250,150 L286,210 L322,92 L360,205 L398,108 L438,182 L492,120 L560,114 L820,112"
          fill="none" stroke="var(--agent)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
          style={{ strokeDasharray: 1200, animation: "cine-draw 8s ease-in-out infinite", filter: "drop-shadow(0 0 6px rgba(76,125,255,0.6))" }} />
        <g id="cine-seal" style={{ animation: "cine-seal 8s ease-in-out infinite", transformOrigin: "820px 112px" }}>
          <circle cx="820" cy="112" r="26" fill="rgba(45,212,167,0.12)" />
          <circle id="cine-ring" cx="820" cy="112" r="18" fill="none" stroke="var(--verified)" strokeWidth="3"
            strokeLinecap="round" transform="rotate(-90 820 112)"
            style={{ strokeDasharray: 114, animation: "cine-ring 8s ease-in-out infinite" }} />
          <path d="M811,112 l6,7 l12,-15" fill="none" stroke="var(--verified)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        </g>
      </svg>

      {/* headline */}
      <div className="relative px-7 py-16 sm:px-12 sm:py-24">
        <div className="label tracking-[0.22em] text-agent">The future of verified recovery</div>
        <h1 className="mt-3 max-w-3xl text-4xl font-semibold leading-[1.05] tracking-tight text-grad sm:text-6xl">
          From monitoring<br />to requalification.
        </h1>
        <p className="mt-5 max-w-xl text-base text-ink sm:text-lg">
          Everyone watches the line. The next decade <span className="text-ink-hi">proves it recovered</span> —
          with a contract, not a hunch. A closed work order is not a recovered line.
        </p>
        <div className="mt-6 flex flex-wrap gap-2 text-[11px] text-ink-mut">
          <span className="rounded-pill border border-line-strong bg-surface-1/60 px-3 py-1">deterministic verdict</span>
          <span className="rounded-pill border border-line-strong bg-surface-1/60 px-3 py-1">reopen on relapse</span>
          <span className="rounded-pill border border-line-strong bg-surface-1/60 px-3 py-1">model out of the loop</span>
        </div>
      </div>
    </section>
  );
}

/* ──────────────────────────── pillar motifs ──────────────────────────── */
const Motif = {
  fleet: (
    <svg viewBox="0 0 48 48" className="h-10 w-10" aria-hidden fill="none">
      {[10, 18, 26].map((y, i) => (
        <path key={i} d={`M6,${y} q6,-8 12,0 t12,0`} stroke="var(--agent)" strokeWidth="1.6" opacity={0.4 + i * 0.2} />
      ))}
      <circle cx="40" cy="18" r="3.5" fill="var(--verified)" />
    </svg>
  ),
  transfer: (
    <svg viewBox="0 0 48 48" className="h-10 w-10" aria-hidden fill="none">
      <rect x="6" y="26" width="12" height="14" rx="2" stroke="var(--agent)" strokeWidth="1.6" />
      <rect x="30" y="26" width="12" height="14" rx="2" stroke="var(--agent)" strokeWidth="1.6" />
      <path d="M16,18 q8,-12 16,0" stroke="var(--verified)" strokeWidth="1.8" />
      <path d="M30,18 l3,-1 l-1,3" stroke="var(--verified)" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  ),
  cert: (
    <svg viewBox="0 0 48 48" className="h-10 w-10" aria-hidden fill="none">
      <circle cx="24" cy="20" r="12" stroke="var(--verified)" strokeWidth="1.6" />
      <path d="M18,20 l4,5 l9,-11" stroke="var(--verified)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M18,32 l-3,10 l9,-5 l9,5 l-3,-10" stroke="var(--brand)" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  ),
  loop: (
    <svg viewBox="0 0 48 48" className="h-10 w-10" aria-hidden fill="none">
      <rect x="18" y="18" width="12" height="12" rx="2" stroke="var(--verified)" strokeWidth="1.8" />
      <path d="M24,6 a18,18 0 1 1 -12.7,5.3" stroke="var(--agent)" strokeWidth="1.6" />
      <path d="M11,8 l0,5 l5,0" stroke="var(--agent)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
};

const PILLARS = [
  { icon: Motif.fleet, lucide: Network, tag: "horizon", title: "Fleet-learned signatures",
    body: "Every verified recovery sharpens the next. Recovery signatures learned across the fleet — not hand-tuned thresholds — while the deterministic contract still owns the verdict." },
  { icon: Motif.transfer, lucide: Boxes, tag: "horizon", title: "Cross-plant transfer",
    body: "A recovery proven on one conveyor transfers to its siblings, and to the next plant — so a machine class is onboarded as data, not a rebuild." },
  { icon: Motif.cert, lucide: Award, tag: "near", title: "Regulatory-grade certificates",
    body: "Digital Return-to-Service records aligned with aviation RTS and pharma IQ/OQ/PQ — audit-ready requalification, not a closed ticket. The certificate exists today; the regulatory framing is next." },
  { icon: Motif.loop, lucide: RefreshCw, tag: "horizon", title: "Autonomous re-verification",
    body: "The agent proposes and re-checks continuously as conditions drift — yet the deterministic core decides every closure. Autonomy in the reasoning, never in the verdict." },
];

const TAG_CLS: Record<string, string> = {
  now: "border-verified/40 text-verified",
  near: "border-agent/40 text-agent",
  horizon: "border-brand/40 text-brand",
};

const ROADMAP = [
  { phase: "Now", tone: "now", items: ["Deterministic Recovery Contracts", "Reopen-on-relapse", "OEE-restoration verification", "Shadow-mode scorecard", "Signed, tamper-evident audit"] },
  { phase: "Near", tone: "near", items: ["Live model reasoning on real data", "MAIA-handoff (close → verify → reopen)", "Real-data threshold calibration", "Regulatory certificate framing"] },
  { phase: "Horizon", tone: "horizon", items: ["Fleet-learned recovery signatures", "Cross-plant transfer", "Autonomous re-verification", "Causal recovery graphs"] },
];

export default function VisionPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-12 px-6 py-8">
      <VisionHero />

      {/* the shift */}
      <Reveal className="mx-auto max-w-3xl text-center">
        <div className="label text-ink-mut">The shift</div>
        <p className="mt-2 text-2xl font-medium leading-snug text-ink-hi sm:text-3xl">
          Everyone <span className="text-ink-mut">monitors</span>. The future{" "}
          <span className="text-grad">verifies</span> — and reopens when the line relapses.
        </p>
      </Reveal>

      {/* pillars */}
      <div className="grid gap-4 sm:grid-cols-2">
        {PILLARS.map((p, i) => (
          <Reveal key={p.title} delay={i * 90}>
            <article className="alive h-full rounded-2xl border border-line bg-surface-1 p-6">
              <div className="flex items-start justify-between">
                <div className="grid h-14 w-14 place-items-center rounded-xl border border-line bg-surface-2">{p.icon}</div>
                <span className={`rounded-pill border px-2.5 py-1 text-[10px] uppercase tracking-wider ${TAG_CLS[p.tag]}`}>{p.tag}</span>
              </div>
              <h3 className="mt-4 flex items-center gap-2 text-lg font-semibold text-ink-hi">
                <p.lucide className="h-4 w-4 text-agent" aria-hidden /> {p.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-mut">{p.body}</p>
            </article>
          </Reveal>
        ))}
      </div>

      {/* machine classes */}
      <Reveal>
        <div className="rounded-2xl border border-line bg-surface-1 p-6">
          <div className="text-center">
            <div className="label text-ink-mut">Built for real machines</div>
            <p className="mt-1 text-xl font-medium text-ink-hi sm:text-2xl">One deterministic engine, every machine class.</p>
            <p className="mx-auto mt-1 max-w-xl text-sm text-ink-mut">
              A machine class is declared as data — not rebuilt in code. The same Recovery Contract verifies a
              drivetrain, a press, and a hydraulic unit.
            </p>
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            {MACHINES.map((mch, i) => (
              <Reveal key={mch.kind} delay={i * 110}>
                <div className="alive rounded-xl border border-line bg-surface-2 p-3">
                  <div className="h-40 w-full overflow-hidden rounded-lg border border-line bg-surface-1/60">
                    <MachineArt kind={mch.kind} className="h-full w-full p-1.5" />
                  </div>
                  <div className="mt-2 text-sm font-medium text-ink">{mch.label}</div>
                  <div className="mono text-[11px] text-ink-mut">{mch.code}</div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </Reveal>

      {/* roadmap */}
      <Reveal>
        <div className="rounded-2xl border border-line bg-surface-1 p-6">
          <div className="label mb-4">The horizon — honestly staged</div>
          <div className="grid gap-5 sm:grid-cols-3">
            {ROADMAP.map((col) => (
              <div key={col.phase} className="relative">
                <div className={`mb-3 inline-flex rounded-pill border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider ${TAG_CLS[col.tone]}`}>{col.phase}</div>
                <ul className="space-y-2">
                  {col.items.map((it) => (
                    <li key={it} className="flex items-start gap-2 text-sm text-ink">
                      <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${col.tone === "now" ? "bg-verified" : col.tone === "near" ? "bg-agent" : "bg-brand"}`} aria-hidden />
                      {it}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <p className="mt-5 border-t border-line pt-4 text-[11px] text-ink-mut">
            <span className="text-verified">Now</span> = shipped &amp; tested · <span className="text-agent">Near</span> = seam built, needs real data/keys ·
            <span className="text-brand"> Horizon</span> = vision, not yet built. We tag what&apos;s real — that discipline is the product.
          </p>
        </div>
      </Reveal>

      {/* close */}
      <Reveal className="py-6 text-center">
        <p className="mx-auto max-w-2xl text-3xl font-semibold leading-tight tracking-tight text-grad sm:text-4xl">
          A closed work order is not a recovered line.
        </p>
        <p className="mt-3 text-sm text-ink-mut">The future proves it — with a contract the model can read but never override.</p>
      </Reveal>
    </div>
  );
}
