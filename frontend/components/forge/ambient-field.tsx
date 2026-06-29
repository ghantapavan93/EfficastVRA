"use client";

/**
 * AmbientField — an original, generative, futuristic backdrop rendered behind the whole app.
 *
 * Three layers, all pure CSS/SVG (no images pulled, no canvas, no per-frame JS): drifting signal "orbs",
 * a slowly-breathing telemetry constellation (a seeded node mesh whose nodes twinkle), and a slow HUD scan
 * line. Deterministic (seeded at module load → identical on server + client, no hydration drift). Subtle by
 * design — it adds depth without hurting legibility — and fully frozen under prefers-reduced-motion.
 */

// Deterministic PRNG (mulberry32) seeded constant — stable node layout across SSR + client.
function mulberry32(seed: number) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const _rnd = mulberry32(7);
const NODES = Array.from({ length: 26 }, () => ({
  x: +(_rnd() * 100).toFixed(2),
  y: +(_rnd() * 100).toFixed(2),
  dur: +(4 + _rnd() * 6).toFixed(2),
  delay: +(_rnd() * 6).toFixed(2),
}));
const EDGES: [number, number][] = [];
for (let i = 0; i < NODES.length; i++) {
  for (let j = i + 1; j < NODES.length; j++) {
    const dist = Math.hypot(NODES[i].x - NODES[j].x, NODES[i].y - NODES[j].y);
    if (dist < 22) EDGES.push([i, j]);
  }
}

export function AmbientField() {
  return (
    <div className="ambient-field pointer-events-none absolute inset-0 z-0 overflow-hidden" aria-hidden>
      <style>{`
        @keyframes af-orb {
          0%   { transform: translate3d(0,0,0) scale(1); }
          50%  { transform: translate3d(var(--dx,40px),var(--dy,-30px),0) scale(1.12); }
          100% { transform: translate3d(0,0,0) scale(1); }
        }
        @keyframes af-twinkle { 0%,100% { opacity:.12; } 50% { opacity:.55; } }
        @keyframes af-mesh { 0%,100% { transform: translate3d(0,0,0); } 50% { transform: translate3d(1.2%,-1%,0); } }
        @keyframes af-scan { 0% { transform: translateY(-12vh); opacity:0; } 8%,70% { opacity:.5; } 100% { transform: translateY(112vh); opacity:0; } }
        .af-orb { position:absolute; border-radius:9999px; filter: blur(46px); will-change: transform; }
        .ambient-field svg .af-node { animation: af-twinkle var(--d,6s) ease-in-out infinite; }
        @media (prefers-reduced-motion: reduce) {
          .af-orb, .ambient-field svg g, .af-scan, .ambient-field svg .af-node { animation: none !important; transform: none !important; }
        }
      `}</style>

      {/* drifting signal orbs */}
      <div className="af-orb" style={{ width: 420, height: 420, left: "4%", top: "-8%", background: "radial-gradient(circle, rgba(76,125,255,0.20), transparent 68%)", animation: "af-orb 26s ease-in-out infinite", ["--dx" as string]: "60px", ["--dy" as string]: "40px" }} />
      <div className="af-orb" style={{ width: 360, height: 360, right: "2%", top: "6%", background: "radial-gradient(circle, rgba(245,165,36,0.12), transparent 66%)", animation: "af-orb 32s ease-in-out infinite", ["--dx" as string]: "-50px", ["--dy" as string]: "50px" }} />
      <div className="af-orb" style={{ width: 480, height: 480, left: "38%", bottom: "-16%", background: "radial-gradient(circle, rgba(45,212,167,0.13), transparent 68%)", animation: "af-orb 38s ease-in-out infinite", ["--dx" as string]: "40px", ["--dy" as string]: "-40px" }} />

      {/* telemetry constellation */}
      <svg className="absolute inset-0 h-full w-full opacity-70" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice">
        <g style={{ animation: "af-mesh 30s ease-in-out infinite" }}>
          {EDGES.map(([a, b], i) => (
            <line key={i} x1={NODES[a].x} y1={NODES[a].y} x2={NODES[b].x} y2={NODES[b].y}
              stroke="var(--agent)" strokeWidth={0.08} opacity={0.1} />
          ))}
          {NODES.map((n, i) => (
            <circle key={i} className="af-node" cx={n.x} cy={n.y} r={0.55}
              fill={i % 7 === 0 ? "var(--verified)" : "var(--agent)"}
              style={{ ["--d" as string]: `${n.dur}s`, animationDelay: `${n.delay}s` }} />
          ))}
        </g>
      </svg>

      {/* slow HUD scan */}
      <div className="af-scan absolute inset-x-0 top-0 h-px" aria-hidden
        style={{ background: "linear-gradient(90deg, transparent, rgba(76,125,255,0.5), transparent)", animation: "af-scan 18s linear infinite" }} />
    </div>
  );
}
