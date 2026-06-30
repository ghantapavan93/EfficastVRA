"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Activity, ArrowRight, Boxes, BrainCircuit, CheckCircle2, ChevronLeft, ChevronRight, GitBranch, RotateCcw, ScrollText, ShieldCheck, X } from "lucide-react";
import Link from "next/link";
import { BrandMark } from "@/components/forge/brand-mark";
import { SyntheticBadge } from "@/components/shell/synthetic-badge";

const reveal = {
  initial: { opacity: 0, y: 22 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-10%" },
  transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] as const },
};

const SLIDES = [
  { img: "/factory-floor.png", kicker: "01 · The intervention", title: "The work order is completed.",
    body: "A technician finishes the fix and closes the ticket. On paper, the line is back in production." },
  { img: "/agent-console.png", kicker: "02 · The verification", title: "But did production actually recover?",
    body: "The agent compares the case against hundreds of historical recoveries, checks 30 stable cycles under comparable conditions, and watches the live signals — vibration, temperature, motor current.",
    chip: "Recovery score 92% · VERIFIED RELEASE" },
  { img: "/factory-hero.png", kicker: "03 · The verdict", title: "Verified — or reopened.",
    body: "Only when every condition holds does the deterministic contract issue a verified release. If the originating fault returns, the incident reopens automatically — no human has to catch it." },
];

const FEATURES = [
  { key: "factory", title: "Cinematic factory view", icon: Activity,
    desc: "Real-time visibility across lines, assets and performance — powered by the Efficast Edge seam.",
    what: "A live OEE view across every line, asset and order — availability × performance × quality, refreshed continuously.",
    why: "You cannot verify a recovery you cannot see. Degradation and false recoveries show up here first, in the metric the plant already trusts.",
    how: "Telemetry streams through the Efficast Edge integration seam; OEE is recomputed per line/shift/order and rendered as one calm, glanceable surface." },
  { key: "insights", title: "AI-powered insights", icon: BrainCircuit,
    desc: "From raw signals to a ranked diagnosis. Detect early, propose fast — a human still decides.",
    what: "A model-driven diagnosis: it classifies the fault and ranks root causes from the live snapshot, retrieved manuals and history.",
    why: "Faster, better-grounded root cause — without letting the model decide anything safety-relevant.",
    how: "The agent reasons (optionally with a hosted model), but its output is advisory and bound to a safe action catalog. A human accepts; the deterministic evaluator owns the verdict." },
  { key: "timeline", title: "Recovery mission timeline", icon: GitBranch,
    desc: "Every intervention, every signal, every decision — tracked with perfect provenance.",
    what: "A complete, ordered record of the recovery: intervention → monitoring → relapse → reopen → verification.",
    why: "When closure is questioned, the whole story is right there — who, what, when, and why.",
    how: "Every state transition and reasoning step is appended to a hash-chained audit, stamped with policy, model and prompt versions." },
  { key: "gate", title: "Comparable-conditions gate", icon: CheckCircle2,
    desc: "The gate that protects integrity. No comparability, no verification.",
    what: "A check that the before/after ran under conditions you can responsibly compare — product, speed, load, sensor health.",
    why: "A line can look 'recovered' simply because it slowed down or changed product. The gate refuses to credit a confound.",
    how: "It scores each operating dimension; a key shift caps confidence and forces INSUFFICIENT_EVIDENCE rather than a false verified." },
  { key: "evidence", title: "Evidence & provenance", icon: Boxes,
    desc: "Every data point is admissible, traceable and tamper-evident with a hash-chained audit.",
    what: "Trust-weighted evidence behind every verdict, anchored to a tamper-evident audit trail.",
    why: "A recovery claim is only as good as its evidence. This makes the evidence inspectable and forgery-resistant.",
    how: "Per-correlation SHA-256 hash chain, optionally HMAC-signed — so a privileged attacker can't rewrite history without breaking the chain." },
  { key: "certificate", title: "Recovery certificate", icon: ScrollText,
    desc: "A governed record that tells the truth about recovery — nothing more, nothing less.",
    what: "A Return-to-Service certificate: the verdict, the conditions evaluated, the human signatures and the audit seal.",
    why: "Quality and regulated environments need a governed artifact, not a closed ticket — the manufacturing analogue of aviation RTS or pharma IQ/OQ/PQ.",
    how: "Composed deterministically from the verdict + provenance + the audit head hash. It says certified only when the contract truly holds." },
] as const;

type FeatureKey = (typeof FEATURES)[number]["key"];

export default function Landing() {
  const reduce = useReducedMotion();
  const [active, setActive] = useState<FeatureKey | null>(null);
  const activeFeature = FEATURES.find((f) => f.key === active) ?? null;

  return (
    <div className="app-canvas relative min-h-screen overflow-hidden">
      <style>{`
        @keyframes kenburns { 0%{transform:scale(1.05) translate(0,0)} 100%{transform:scale(1.14) translate(-1.5%,-1%)} }
        .kenburns{ animation: kenburns 18s ease-in-out infinite alternate; }
        @media (prefers-reduced-motion: reduce){ .kenburns{animation:none} }
      `}</style>

      {/* cohesive backdrop — one palette behind every section */}
      <div className="pointer-events-none fixed inset-0" aria-hidden style={{
        background: "radial-gradient(1000px 600px at 12% -8%, rgba(76,125,255,0.12), transparent 60%), radial-gradient(900px 560px at 92% 4%, rgba(45,212,167,0.08), transparent 58%), radial-gradient(800px 600px at 50% 116%, rgba(245,165,36,0.05), transparent 60%)",
      }} />

      <header className="relative z-20 flex items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2.5">
          <BrandMark size={30} animated />
          <span className="text-base font-semibold tracking-tight text-ink-hi">Verified Recovery</span>
        </div>
        <SyntheticBadge />
      </header>

      {/* ───────────────────── HERO ───────────────────── */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 pt-8 text-center md:pt-12">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          className="mb-5 inline-flex items-center gap-2 rounded-pill border border-line bg-surface-1/70 px-3 py-1 text-[11px] text-ink-mut backdrop-blur">
          <span className="h-1.5 w-1.5 rounded-full bg-agent" /> Post-intervention production requalification · for Efficast
        </motion.div>

        <h1 className="mx-auto max-w-3xl text-4xl font-semibold leading-[1.06] tracking-tight text-ink-hi md:text-6xl">
          <WordReveal reduce={!!reduce} segments={[
            { text: "Work completed does not mean " },
            { text: "production recovered.", className: "text-verified" },
          ]} />
        </h1>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.5, duration: 0.7 }}
          className="mx-auto mt-6 max-w-xl text-balance text-[15px] leading-relaxed text-ink-mut">
          Verified Recovery monitors what happens <em>after</em> an intervention, gathers the evidence required
          for closure, and reopens the incident when the factory does not recover as expected.
        </motion.p>
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.7, duration: 0.6 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link href="/missions" className="glow-agent inline-flex h-11 items-center gap-2 rounded-[10px] bg-agent px-5 text-sm font-semibold text-black transition-transform hover:scale-[1.02]">
            Run the Northstar mission <ArrowRight className="h-4 w-4" />
          </Link>
          <Link href="/intake" className="inline-flex h-11 items-center gap-2 rounded-[10px] border border-line-strong bg-surface-1/40 px-5 text-sm text-ink backdrop-blur hover:bg-surface-2">
            Upload your plant data
          </Link>
          <Link href="/vision" className="inline-flex h-11 items-center rounded-[10px] px-3 text-sm text-ink-mut hover:text-ink">
            See the future vision
          </Link>
        </motion.div>

        {/* the centerpiece — a self-narrating recovery story */}
        <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.9, duration: 0.7, ease: [0.22, 1, 0.36, 1] }} className="mt-12">
          <RecoveryStoryGraph reduce={!!reduce} />
        </motion.div>
      </section>

      {/* ───────────────────── STORY SLIDESHOW ───────────────────── */}
      <div className="mt-16"><StorySlideshow reduce={!!reduce} /></div>

      {/* ───────────────────── FEATURES (clickable) ───────────────────── */}
      <section className="relative z-10 mx-auto max-w-7xl px-6 py-16">
        <motion.div {...reveal} className="mb-6 text-center">
          <div className="label text-ink-mut">What runs underneath</div>
          <h2 className="mt-1 text-2xl font-semibold tracking-tight text-ink-hi">The assurance layer, in six parts</h2>
          <p className="mt-1 text-sm text-ink-mut">Tap any card for how it works.</p>
        </motion.div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <motion.button key={f.key} {...reveal} onClick={() => setActive(f.key)}
              className="alive group flex flex-col overflow-hidden rounded-2xl border border-line bg-surface-1 p-5 text-left transition-colors hover:border-line-strong focus-visible:border-agent">
              <div className="mb-3 h-36 overflow-hidden rounded-xl border border-line bg-surface-2">{cardVisual(f.key, !!reduce)}</div>
              <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-ink-hi">
                <f.icon className="h-4 w-4 text-agent" aria-hidden /> {f.title}
              </h3>
              <p className="mt-1.5 text-xs leading-relaxed text-ink-mut">{f.desc}</p>
              <span className="mt-3 inline-flex items-center gap-1 text-[11px] font-medium text-agent opacity-0 transition-opacity group-hover:opacity-100">
                How it works <ArrowRight className="h-3 w-3" />
              </span>
            </motion.button>
          ))}
        </div>
      </section>

      {/* ───────────────────── CLOSING — OUR MISSION ───────────────────── */}
      <section className="relative z-10 h-[68vh] min-h-[440px] overflow-hidden border-t border-line">
        <div className="kenburns absolute inset-0 bg-cover bg-center" style={{ backgroundImage: "url(/factory-wide.png)" }} aria-hidden />
        <div className="absolute inset-0" aria-hidden style={{ background: "linear-gradient(90deg, rgba(8,11,18,0.95) 0%, rgba(8,11,18,0.72) 42%, rgba(8,11,18,0.2) 76%, rgba(8,11,18,0.5) 100%)" }} />
        <div className="absolute inset-0" aria-hidden style={{ background: "linear-gradient(0deg, var(--forge-bg) 1%, transparent 42%)" }} />
        <motion.div {...reveal} className="relative z-10 mx-auto flex h-full max-w-7xl flex-col justify-center px-6">
          <div className="label tracking-[0.22em] text-verified">Our mission</div>
          <h2 className="mt-2 max-w-xl text-3xl font-semibold leading-tight tracking-tight text-ink-hi md:text-5xl">
            Make every intervention count.<br /><span className="text-grad">Ensure every recovery lasts.</span>
          </h2>
          <p className="mt-3 max-w-md text-sm leading-relaxed text-ink md:text-base">
            A closed work order is not a recovered line. Verify it — with a contract the model can read but never override.
          </p>
          <div className="mt-7">
            <Link href="/missions" className="glow-agent inline-flex h-11 items-center gap-2 rounded-[10px] bg-agent px-5 text-sm font-semibold text-black transition-transform hover:scale-[1.02]">
              Open a live recovery mission <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </motion.div>
      </section>

      <footer className="relative z-10 mx-auto max-w-7xl px-6 py-10 text-center">
        <div className="flex items-center justify-center gap-2"><BrandMark size={20} /><span className="text-sm font-medium text-ink">Verified Recovery</span></div>
        <p className="mt-3 text-[11px] text-ink-faint">
          Independent Efficast-aligned prototype · synthetic data · no physical machine control. Not affiliated with Efficast.
        </p>
      </footer>

      <FeatureModal feature={activeFeature} reduce={!!reduce} onClose={() => setActive(null)} />
    </div>
  );
}

/* ─────────────────────────── word-by-word headline reveal ─────────────────────────── */
function WordReveal({ segments, reduce }: { segments: { text: string; className?: string }[]; reduce: boolean }) {
  const words: { w: string; cn?: string }[] = [];
  segments.forEach((s) => s.text.split(" ").forEach((tok) => tok && words.push({ w: tok, cn: s.className })));
  const full = segments.map((s) => s.text).join("");
  return (
    <span aria-label={full}>
      {words.map((wd, i) => (
        <motion.span key={i} aria-hidden className={wd.cn} style={{ display: "inline-block", marginRight: "0.26em" }}
          initial={reduce ? false : { opacity: 0, y: 16, filter: "blur(8px)" }}
          animate={reduce ? undefined : { opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.5, delay: 0.25 + i * 0.1, ease: [0.22, 1, 0.36, 1] }}>
          {wd.w}
        </motion.span>
      ))}
    </span>
  );
}

/* ─────────────────────────── self-narrating recovery story graph ─────────────────────────── */
const PHASES = [
  { label: "Monitoring", tone: "var(--agent)", at: 0.0, caption: "The verification window opens — early cycles are watched against the Recovery Contract." },
  { label: "Apparent recovery", tone: "var(--agent)", at: 0.2, caption: "Vibration settles below the 4.0 mm/s limit. On the surface, it looks recovered." },
  { label: "Cycle-17 relapse", tone: "var(--failure)", at: 0.36, caption: "Fault F27 returns at cycle 17 — the recovery did not actually hold." },
  { label: "Reopened", tone: "var(--failure)", at: 0.52, caption: "The incident reopens automatically; the bearing-replacement contingency runs." },
  { label: "Verified", tone: "var(--verified)", at: 0.72, caption: "30 stable, comparable cycles. Only now is recovery verified." },
] as const;

const AGENT_D = "M 20 80 C 100 96, 160 118, 250 122 L 330 124 C 345 124, 352 54, 366 50 C 380 48, 398 118, 415 122";
const VER_D = "M 415 122 C 480 128, 560 150, 660 152 C 690 153, 705 153, 710 153";
const GUIDE_D = "M 20 80 C 100 96, 160 118, 250 122 L 330 124 C 345 124, 352 54, 366 50 C 380 48, 398 118, 415 122 C 480 128, 560 150, 660 152 C 690 153, 705 153, 710 153";

function RecoveryStoryGraph({ reduce }: { reduce: boolean }) {
  const [p, setP] = useState(reduce ? 1 : 0);
  const [len, setLen] = useState(0);
  const guideRef = useRef<SVGPathElement>(null);
  const raf = useRef<number>();

  const play = () => {
    if (raf.current) cancelAnimationFrame(raf.current);
    const t0 = performance.now();
    const dur = 8200;
    setP(0);
    const step = (now: number) => {
      const np = Math.min(1, (now - t0) / dur);
      setP(np);
      if (np < 1) raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
  };

  useEffect(() => { setLen(guideRef.current?.getTotalLength() ?? 0); }, []);
  useEffect(() => {
    if (reduce) { setP(1); return; }
    const id = setTimeout(play, 600);
    return () => { clearTimeout(id); if (raf.current) cancelAnimationFrame(raf.current); };
  }, [reduce]);

  const active = PHASES.reduce((acc, ph, i) => (p >= ph.at ? i : acc), 0);
  const agentDraw = Math.min(1, p / 0.55);
  const verDraw = Math.max(0, Math.min(1, (p - 0.55) / 0.45));
  const head = guideRef.current && len ? guideRef.current.getPointAtLength(p * len) : null;
  const W = 730, H = 200, threshold = 110;

  return (
    <div className="mx-auto max-w-3xl rounded-2xl border border-line-strong bg-surface-1/70 p-4 backdrop-blur sm:p-6">
      <div className="mb-2 flex items-center justify-between">
        <span className="label">Live recovery trajectory · INC-2841</span>
        <button onClick={play} className="inline-flex items-center gap-1.5 rounded-pill border border-line-strong px-2.5 py-1 text-[11px] text-ink-mut transition-colors hover:text-ink">
          <RotateCcw className="h-3 w-3" /> Replay
        </button>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Recovery trajectory: vibration improves, F27 recurs at cycle 17, the incident reopens, then recovery is verified over 30 stable cycles.">
        {/* threshold */}
        <line x1={20} x2={710} y1={threshold} y2={threshold} stroke="var(--warning)" strokeDasharray="4 6" strokeWidth={1} opacity={0.5} />
        <text x={710} y={threshold - 6} fontSize={9} fill="var(--text-faint)" textAnchor="end">vibration limit · 4.0 mm/s</text>
        {/* invisible guide for the head position */}
        <path ref={guideRef} d={GUIDE_D} fill="none" stroke="none" />
        {/* drawn segments */}
        <path d={AGENT_D} fill="none" stroke="var(--agent)" strokeWidth={3} strokeLinecap="round" pathLength={1}
          strokeDasharray={1} strokeDashoffset={1 - agentDraw} style={{ filter: "drop-shadow(0 0 6px rgba(76,125,255,0.45))" }} />
        <path d={VER_D} fill="none" stroke="var(--verified)" strokeWidth={3} strokeLinecap="round" pathLength={1}
          strokeDasharray={1} strokeDashoffset={1 - verDraw} style={{ filter: "drop-shadow(0 0 6px rgba(45,212,167,0.5))" }} />
        {/* F27 relapse marker */}
        {active >= 2 && (
          <g>
            <line x1={366} x2={366} y1={20} y2={170} stroke="var(--failure)" strokeDasharray="3 3" strokeWidth={1} opacity={0.7} />
            <circle cx={366} cy={50} r={4.5} fill="var(--failure)" />
            <text x={372} y={34} fontSize={10} fill="var(--failure)">F27 · cycle 17</text>
          </g>
        )}
        {/* travelling head */}
        {head && p < 1 && (
          <g>
            <circle cx={head.x} cy={head.y} r={9} fill={PHASES[active].tone} opacity={0.18} />
            <circle cx={head.x} cy={head.y} r={4} fill={PHASES[active].tone} stroke="var(--surface-1)" strokeWidth={1.5} />
          </g>
        )}
        {head && p >= 1 && <circle cx={710} cy={153} r={5} fill="var(--verified)" />}
      </svg>

      {/* live caption */}
      <div className="mt-2 min-h-[40px]">
        <motion.p key={active} initial={reduce ? false : { opacity: 0, y: 6 }} animate={reduce ? undefined : { opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
          className="text-sm text-ink">
          <span className="mono mr-2 text-[11px] text-ink-mut">{String(active + 1).padStart(2, "0")}/05</span>
          {PHASES[active].caption}
        </motion.p>
      </div>

      {/* the five stages, lighting up in sequence */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {PHASES.map((ph, i) => {
          const lit = i <= active;
          return (
            <span key={ph.label}
              className={`inline-flex items-center gap-1.5 rounded-pill border px-2.5 py-1 text-[11px] transition-all duration-300 ${i === active ? "scale-[1.04]" : ""}`}
              style={{ borderColor: lit ? ph.tone : "var(--line)", color: lit ? "var(--text)" : "var(--text-faint)", background: i === active ? "color-mix(in oklab, " + ph.tone + " 12%, transparent)" : "transparent" }}>
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: lit ? ph.tone : "var(--line-strong)" }} />
              {ph.label}
            </span>
          );
        })}
      </div>
    </div>
  );
}

/* ─────────────────────────── story slideshow ─────────────────────────── */
function StorySlideshow({ reduce }: { reduce: boolean }) {
  const [i, setI] = useState(0);
  const go = (n: number) => setI((n + SLIDES.length) % SLIDES.length);
  useEffect(() => {
    if (reduce) return;
    const t = setInterval(() => setI((p) => (p + 1) % SLIDES.length), 6000);
    return () => clearInterval(t);
  }, [reduce]);
  const s = SLIDES[i];
  const SCRIM = "linear-gradient(90deg, rgba(8,11,18,0.95) 0%, rgba(8,11,18,0.82) 38%, rgba(10,15,26,0.5) 72%, rgba(8,11,18,0.6) 100%)";
  return (
    <section className="relative z-10 h-[86vh] min-h-[520px] w-full overflow-hidden border-y border-line">
      {SLIDES.map((sl, idx) => (
        <div key={idx} className="absolute inset-0 transition-opacity duration-[1200ms] ease-in-out" style={{ opacity: idx === i ? 1 : 0 }} aria-hidden={idx !== i}>
          <div className={`absolute inset-0 bg-cover bg-center ${idx === i ? "kenburns" : ""}`} style={{ backgroundImage: `url(${sl.img})` }} />
          <div className="absolute inset-0" style={{ background: SCRIM }} />
          <div className="absolute inset-0" style={{ background: "linear-gradient(0deg, var(--forge-bg) 1%, transparent 46%)" }} />
        </div>
      ))}
      <div className="relative z-10 mx-auto flex h-full max-w-7xl flex-col justify-center px-6">
        <div className="label tracking-[0.22em] text-verified">The story</div>
        <motion.div key={i} initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }} className="mt-2 max-w-xl">
          <div className="mono text-[12px] tracking-wide text-agent">{s.kicker}</div>
          <h2 className="mt-2 text-3xl font-semibold leading-tight tracking-tight text-ink-hi md:text-5xl">{s.title}</h2>
          <p className="mt-3 text-sm leading-relaxed text-ink md:text-base">{s.body}</p>
          {s.chip && (
            <span className="mt-4 inline-flex items-center gap-1.5 rounded-pill border border-verified/50 bg-verified-soft px-3 py-1.5 text-[12px] text-verified backdrop-blur">
              <ShieldCheck className="h-3.5 w-3.5" /> {s.chip}
            </span>
          )}
        </motion.div>
        <div className="mt-8 flex items-center gap-3">
          <button onClick={() => go(i - 1)} aria-label="Previous slide" className="grid h-9 w-9 place-items-center rounded-full border border-line-strong bg-surface-1/60 text-ink-mut backdrop-blur hover:text-ink">
            <ChevronLeft className="h-4 w-4" />
          </button>
          <div className="flex items-center gap-2">
            {SLIDES.map((_, idx) => (
              <button key={idx} onClick={() => go(idx)} aria-label={`Go to slide ${idx + 1}`}
                className={`h-1.5 rounded-pill transition-all ${idx === i ? "w-7 bg-verified" : "w-3 bg-line-strong hover:bg-ink-mut"}`} />
            ))}
          </div>
          <button onClick={() => go(i + 1)} aria-label="Next slide" className="grid h-9 w-9 place-items-center rounded-full border border-line-strong bg-surface-1/60 text-ink-mut backdrop-blur hover:text-ink">
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </section>
  );
}

/* ─────────────────────────── feature modal ─────────────────────────── */
function FeatureModal({ feature, reduce, onClose }: { feature: (typeof FEATURES)[number] | null; reduce: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!feature) return;
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [feature, onClose]);
  if (!feature) return null;
  return (
    <div className="fixed inset-0 z-[80] grid place-items-center p-4" role="dialog" aria-modal="true" aria-label={feature.title}>
      <div className="absolute inset-0 backdrop-blur-sm" style={{ background: "var(--scrim)" }} onClick={onClose} />
      <motion.div initial={reduce ? false : { opacity: 0, scale: 0.96, y: 12 }} animate={reduce ? undefined : { opacity: 1, scale: 1, y: 0 }} transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
        className="glass relative w-full max-w-lg overflow-hidden rounded-2xl border border-line-strong shadow-[0_30px_80px_-30px_rgba(0,0,0,0.9)]">
        <div className="h-40 overflow-hidden border-b border-line bg-surface-2">{cardVisual(feature.key, reduce)}</div>
        <div className="p-6">
          <h3 className="flex items-center gap-2 text-lg font-semibold text-ink-hi">
            <feature.icon className="h-5 w-5 text-agent" aria-hidden /> {feature.title}
          </h3>
          <dl className="mt-4 space-y-3">
            {[["What", feature.what], ["Why it matters", feature.why], ["How it works", feature.how]].map(([k, v]) => (
              <div key={k}>
                <dt className="label text-agent">{k}</dt>
                <dd className="mt-0.5 text-sm leading-relaxed text-ink">{v}</dd>
              </div>
            ))}
          </dl>
          <Link href="/missions" className="mt-5 inline-flex h-10 items-center gap-2 rounded-[10px] bg-agent px-4 text-sm font-semibold text-black transition-transform hover:scale-[1.02]">
            See it in a live mission <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
        <button onClick={onClose} aria-label="Close" className="absolute right-3 top-3 grid h-8 w-8 place-items-center rounded-full border border-line-strong bg-surface-1/70 text-ink-mut backdrop-blur hover:text-ink">
          <X className="h-4 w-4" />
        </button>
      </motion.div>
    </div>
  );
}

/* ─────────────────────────── card visuals ─────────────────────────── */
function cardVisual(key: string, reduce: boolean) {
  switch (key) {
    case "factory": return <FactoryViewVisual />;
    case "insights": return <InsightsVisual reduce={reduce} />;
    case "timeline": return <TimelineVisual />;
    case "gate": return <GateVisual />;
    case "evidence": return <ProvenanceVisual />;
    case "certificate": return <CertificateVisual />;
    default: return null;
  }
}

function FactoryViewVisual() {
  return (
    <div className="relative h-full w-full">
      <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: "url(/factory-floor.png)" }} aria-hidden />
      <div className="absolute inset-0" style={{ background: "linear-gradient(0deg, rgba(8,11,18,0.72), rgba(8,11,18,0.18))" }} />
      <div className="absolute inset-0 flex flex-wrap content-end gap-1.5 p-3">
        {[["LINE 1", "78%", "agent"], ["LINE 2", "82%", "agent"], ["LINE 4", "64%", "failure"]].map(([l, v, t]) => (
          <span key={l} className={`rounded-md border px-1.5 py-0.5 text-[9px] font-medium backdrop-blur ${t === "failure" ? "border-failure/50 text-failure" : "border-agent/40 text-ink"}`}>
            {l} · OEE {v}
          </span>
        ))}
      </div>
    </div>
  );
}

function InsightsVisual({ reduce }: { reduce: boolean }) {
  return (
    <div className="relative h-full w-full p-2">
      <svg viewBox="0 0 200 110" className="h-full w-full" aria-hidden>
        {[[40, 30], [70, 22], [62, 55], [95, 44], [120, 30], [110, 66], [145, 52]].map(([x, y], i, a) => (
          <g key={i}>
            {a.slice(i + 1).map(([x2, y2], j) => Math.hypot(x - x2, y - y2) < 40 && (
              <line key={j} x1={x} y1={y} x2={x2} y2={y2} stroke="var(--agent)" strokeWidth="0.5" opacity="0.3" />
            ))}
            <circle cx={x} cy={y} r={i % 3 === 0 ? 3 : 2} fill={i % 3 === 0 ? "var(--verified)" : "var(--agent)"}>
              {!reduce && <animate attributeName="opacity" values="0.4;1;0.4" dur={`${2 + i * 0.3}s`} repeatCount="indefinite" />}
            </circle>
          </g>
        ))}
        <polyline points="20,95 40,90 55,98 70,86 90,93 110,84 140,90 180,87" fill="none" stroke="var(--agent)" strokeWidth="1.2" opacity="0.6" />
      </svg>
      <div className="absolute bottom-2 right-2 flex items-center gap-1.5 rounded-md border border-failure/50 bg-failure-soft px-2 py-1 text-[9px] text-failure">
        <Activity className="h-3 w-3" /> ANOMALY · Packer_04 · vibration
      </div>
    </div>
  );
}

function TimelineVisual() {
  const steps = [
    { t: "agent", l: "Intervention" }, { t: "failure", l: "F27 returned" }, { t: "agent", l: "Bearing repl." },
    { t: "agent", l: "30 stable" }, { t: "verified", l: "Verified" },
  ];
  const color = (t: string) => (t === "failure" ? "var(--failure)" : t === "verified" ? "var(--verified)" : "var(--agent)");
  return (
    <div className="flex h-full items-center px-3">
      <div className="relative flex w-full items-center justify-between">
        <div className="absolute inset-x-2 top-[11px] h-px bg-line-strong" />
        {steps.map((s, i) => (
          <div key={i} className="relative z-10 flex flex-col items-center gap-1.5">
            <span className="grid h-6 w-6 place-items-center rounded-full border bg-surface-2" style={{ borderColor: color(s.t) }}>
              <span className="h-2 w-2 rounded-full" style={{ background: color(s.t) }} />
            </span>
            <span className="max-w-[44px] text-center text-[8px] leading-tight text-ink-mut">{s.l}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function GateVisual() {
  const dims = [["Product mix", "Same"], ["Speed", "Same"], ["Material", "Same"], ["Environment", "In tol."], ["Changeovers", "None"]];
  return (
    <div className="flex h-full items-center gap-3 p-3">
      <div className="flex flex-col items-center gap-1">
        <CheckCircle2 className="h-9 w-9 text-verified" />
        <span className="text-[9px] font-semibold uppercase tracking-wide text-verified">Comparable</span>
        <span className="mono text-[8px] text-ink-mut">×1.00</span>
      </div>
      <div className="flex-1 space-y-1">
        {dims.map(([k, v]) => (
          <div key={k} className="flex items-center justify-between border-b border-line/60 pb-0.5 text-[9px]">
            <span className="text-ink-mut">{k}</span><span className="text-verified">{v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ProvenanceVisual() {
  return (
    <div className="relative h-full w-full p-2">
      <svg viewBox="0 0 200 110" className="h-full w-full" aria-hidden>
        {[20, 75, 130].map((x, i) => (
          <g key={i} transform={`translate(${x},${36 + i * 6})`} opacity={0.92 - i * 0.12}>
            <path d="M0,12 L20,0 L40,12 L40,34 L20,46 L0,34 Z" fill="var(--agent)" opacity="0.1" />
            <path d="M0,12 L20,0 L40,12 L20,24 Z" fill="none" stroke="var(--agent)" strokeWidth="1" />
            <path d="M0,12 L20,24 L20,46 L0,34 Z M40,12 L20,24 L20,46 L40,34 Z" fill="none" stroke="var(--agent)" strokeWidth="1" opacity="0.6" />
            <circle cx="20" cy="20" r="2.5" fill="var(--verified)" />
            {i < 2 && <line x1="40" y1="23" x2="55" y2="26" stroke="var(--verified)" strokeWidth="1" strokeDasharray="2 2" />}
          </g>
        ))}
      </svg>
      <div className="absolute bottom-2 left-2 right-2 rounded-md border border-line bg-surface-1/80 px-2 py-1">
        <div className="mono flex justify-between text-[8px] text-ink-mut"><span>EVALUATION_COMPLETED</span><span className="text-verified">hash a8f3c2e1…</span></div>
      </div>
    </div>
  );
}

function CertificateVisual() {
  return (
    <div className="flex h-full flex-col justify-between p-3">
      <div className="flex items-center justify-between">
        <span className="inline-flex items-center gap-1 rounded-md border border-verified/50 bg-verified-soft px-2 py-0.5 text-[10px] font-semibold text-verified">
          <ShieldCheck className="h-3 w-3" /> VERIFIED
        </span>
        <span className="mono text-[8px] text-ink-mut">RC-INC-2841-02</span>
      </div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[9px]">
        <span className="text-ink-mut">Asset</span><span className="text-ink">Packaging Line 4</span>
        <span className="text-ink-mut">Order</span><span className="text-ink">PO-2841</span>
        <span className="text-ink-mut">Stable cycles</span><span className="text-ink">30 comparable</span>
        <span className="text-ink-mut">Approved by</span><span className="text-ink">Quality Manager</span>
      </div>
      <div className="flex items-end justify-between">
        <svg viewBox="0 0 90 16" className="h-4 w-24" aria-hidden><path d="M2,12 q6,-12 12,-2 t12,-1 q6,8 12,0 t12,-3 q8,6 14,2 t12,-2" fill="none" stroke="var(--verified)" strokeWidth="1" opacity="0.7" /></svg>
        <div className="grid grid-cols-4 gap-px" aria-hidden>
          {Array.from({ length: 16 }).map((_, i) => <span key={i} className="h-1 w-1" style={{ background: i % 3 === 0 ? "var(--ink-hi)" : "transparent" }} />)}
        </div>
      </div>
    </div>
  );
}
