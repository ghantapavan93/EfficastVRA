"use client";

/**
 * MachineArt — original generative "digital-twin" illustrations of the supported machine classes.
 *
 * Pure SVG (no photos/deps): a detailed mechanical schematic of each machine inside a futuristic HUD frame
 * — corner brackets, an internal blueprint grid, a sweeping scan line, a soft glow/bloom, a live status
 * dot, and data callouts (bearing IDs, vibration, pressure, temperatures). Subtly animated (belt travel,
 * pulley/gear spin, injection stroke, hydraulic flow, gauge sweep) and fully reduced-motion-safe.
 */

type Kind = "conveyor" | "press" | "hydraulic";

const STYLE = `
  .ma { color: var(--agent); }
  .ma-l { stroke: currentColor; fill: none; stroke-width: 1.3; stroke-linecap: round; stroke-linejoin: round; }
  .ma-s { stroke: currentColor; fill: none; stroke-width: .8; opacity: .4; }
  .ma-f { fill: currentColor; opacity: .06; }
  .ma-a { stroke: var(--verified); fill: none; stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; }
  .ma-t { fill: currentColor; opacity: .8; font-family: var(--font-mono); }
  .ma-tv { fill: var(--verified); font-family: var(--font-mono); }
  @keyframes ma-belt { to { stroke-dashoffset: -32; } }
  @keyframes ma-spin { to { transform: rotate(360deg); } }
  @keyframes ma-carry { 0% { transform: translateX(0); opacity:0 } 8%{opacity:1} 92%{opacity:1} 100% { transform: translateX(74px); opacity:0 } }
  @keyframes ma-ram { 0%,100% { transform: translateX(0) } 45% { transform: translateX(15px) } }
  @keyframes ma-flow { to { stroke-dashoffset: -26; } }
  @keyframes ma-needle { 0%,100% { transform: rotate(-34deg) } 50% { transform: rotate(36deg) } }
  @keyframes ma-vib { 0%,100% { opacity:.15; r:3 } 50% { opacity:.55; r:8 } }
  @keyframes ma-scan { 0% { transform: translateY(6px); opacity:0 } 12%,88% { opacity:.5 } 100% { transform: translateY(150px); opacity:0 } }
  @keyframes ma-blink { 0%,100% { opacity:1 } 50% { opacity:.35 } }
  @keyframes ma-trace { to { stroke-dashoffset: -40 } }
  .ma-belt { stroke-dasharray: 7 9; animation: ma-belt 1.2s linear infinite; }
  .ma-spin { animation: ma-spin 7s linear infinite; }
  .ma-carry { animation: ma-carry 4s linear infinite; }
  .ma-ram { animation: ma-ram 3.2s ease-in-out infinite; }
  .ma-flow { stroke-dasharray: 5 7; animation: ma-flow 1.5s linear infinite; }
  .ma-needle { animation: ma-needle 4s ease-in-out infinite; transform-box: fill-box; transform-origin: bottom center; }
  .ma-vib { animation: ma-vib 2.2s ease-in-out infinite; }
  .ma-scan { animation: ma-scan 5.5s linear infinite; }
  .ma-status { animation: ma-blink 2s ease-in-out infinite; }
  .ma-trace { stroke-dasharray: 4 4; animation: ma-trace 1.4s linear infinite; }
  @media (prefers-reduced-motion: reduce) {
    .ma-belt,.ma-spin,.ma-carry,.ma-ram,.ma-flow,.ma-needle,.ma-vib,.ma-scan,.ma-status,.ma-trace { animation: none !important; }
  }
`;

function Chrome({ uid, title, code }: { uid: string; title: string; code: string }) {
  const brackets: [number, number, number, number][] = [
    [8, 8, 1, 1], [252, 8, -1, 1], [8, 152, 1, -1], [252, 152, -1, -1],
  ];
  return (
    <>
      <defs>
        <pattern id={`g-${uid}`} width="11" height="11" patternUnits="userSpaceOnUse">
          <path d="M11,0 L0,0 L0,11" fill="none" stroke="currentColor" strokeWidth="0.3" opacity="0.16" />
        </pattern>
        <filter id={`glow-${uid}`} x="-15%" y="-15%" width="130%" height="130%">
          <feGaussianBlur stdDeviation="1.1" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      <rect x="2" y="2" width="256" height="156" rx="6" fill={`url(#g-${uid})`} />
      {brackets.map(([x, y, sx, sy], i) => (
        <path key={i} className="ma-a" opacity="0.7" d={`M${x},${y + 13 * sy} L${x},${y} L${x + 13 * sx},${y}`} />
      ))}
      <text x="16" y="20" fontSize="7" letterSpacing="1.2" className="ma-t">{title}</text>
      <text x="16" y="150" fontSize="6.5" letterSpacing="1" className="ma-t" opacity="0.5">{code}</text>
      <g className="ma-status">
        <circle cx="243" cy="16" r="3" fill="var(--verified)" />
        <text x="237" y="18" fontSize="6" className="ma-tv" textAnchor="end">LIVE</text>
      </g>
      <rect className="ma-scan" x="6" y="0" width="248" height="1.4" fill="var(--agent)" opacity="0.5" />
    </>
  );
}

function Callout({ ax, ay, lx, ly, label, value }: { ax: number; ay: number; lx: number; ly: number; label: string; value?: string }) {
  const right = lx >= ax;
  return (
    <g>
      <circle cx={ax} cy={ay} r="1.7" fill="var(--verified)" />
      <path className="ma-s" d={`M${ax},${ay} L${lx},${ly}`} />
      <text x={lx + (right ? 3 : -3)} y={ly} fontSize="6.4" className="ma-t" textAnchor={right ? "start" : "end"}>{label}</text>
      {value && <text x={lx + (right ? 3 : -3)} y={ly + 7} fontSize="6" className="ma-tv" textAnchor={right ? "start" : "end"}>{value}</text>}
    </g>
  );
}

function Conveyor({ uid }: { uid: string }) {
  return (
    <svg viewBox="0 0 260 160" className="ma h-full w-full" role="img" aria-label="Conveyor-drive assembly digital-twin schematic">
      <style>{STYLE}</style>
      <Chrome uid={uid} title="CONVEYOR-DRIVE" code="CDX-220" />
      <g filter={`url(#glow-${uid})`}>
        <line className="ma-s" x1="20" y1="120" x2="240" y2="120" />
        {/* motor with cooling fins + terminal box */}
        <rect className="ma-l" x="22" y="66" width="48" height="46" rx="3" />
        <rect className="ma-f" x="22" y="66" width="48" height="46" rx="3" />
        {[28, 34, 40, 46, 52, 58, 64].map((x) => <line key={x} className="ma-s" x1={x} y1="68" x2={x} y2="110" />)}
        <rect className="ma-l" x="36" y="58" width="14" height="9" rx="1" />
        {/* coupling */}
        <line className="ma-l" x1="70" y1="89" x2="86" y2="89" />
        <rect className="ma-a" x="80" y="82" width="6" height="14" rx="1" />
        {/* drive pulley with gear teeth + spokes */}
        <g className="ma-spin" style={{ transformOrigin: "112px 89px" }}>
          <circle className="ma-l" cx="112" cy="89" r="18" />
          <circle className="ma-f" cx="112" cy="89" r="18" />
          {Array.from({ length: 12 }).map((_, i) => {
            const a = (i / 12) * Math.PI * 2;
            return <line key={i} className="ma-s" x1={112 + Math.cos(a) * 18} y1={89 + Math.sin(a) * 18} x2={112 + Math.cos(a) * 21} y2={89 + Math.sin(a) * 21} />;
          })}
          <line className="ma-s" x1="112" y1="73" x2="112" y2="105" />
          <line className="ma-s" x1="96" y1="89" x2="128" y2="89" />
          <circle className="ma-l" cx="112" cy="89" r="3" />
        </g>
        {/* tail roller */}
        <circle className="ma-l" cx="214" cy="89" r="12" />
        <circle className="ma-f" cx="214" cy="89" r="12" />
        {/* belt + carried product */}
        <line className="ma-l ma-belt" x1="112" y1="71" x2="214" y2="77" />
        <line className="ma-l ma-belt" x1="112" y1="107" x2="214" y2="101" />
        <rect className="ma-a ma-carry" x="124" y="62" width="11" height="9" rx="1" />
        <rect className="ma-a ma-carry" x="124" y="62" width="11" height="9" rx="1" style={{ animationDelay: "2s" }} />
        {/* bearing housing + vibration */}
        <rect className="ma-l" x="148" y="112" width="22" height="11" rx="2" />
        <circle cx="155" cy="118" r="1" fill="currentColor" /><circle cx="163" cy="118" r="1" fill="currentColor" />
        <circle className="ma-vib" cx="159" cy="89" r="4" fill="var(--verified)" stroke="none" />
        {/* live vibration micro-trace */}
        <polyline className="ma-a ma-trace" points="180,40 186,34 192,46 198,36 204,42 210,38 216,41" opacity="0.8" />
      </g>
      <Callout ax={159} ay={89} lx={186} ly={70} label="DRIVE-END BRG" value="BR-6205" />
      <Callout ax={112} ay={89} lx={60} ly={36} label="VIBRATION" value="3.1 mm/s" />
    </svg>
  );
}

function Press({ uid }: { uid: string }) {
  return (
    <svg viewBox="0 0 260 160" className="ma h-full w-full" role="img" aria-label="Injection-molding press digital-twin schematic">
      <style>{STYLE}</style>
      <Chrome uid={uid} title="INJECTION PRESS" code="IMX-90" />
      <g filter={`url(#glow-${uid})`}>
        <line className="ma-s" x1="20" y1="124" x2="240" y2="124" />
        {/* tie bars */}
        <line className="ma-s" x1="34" y1="54" x2="150" y2="54" />
        <line className="ma-s" x1="34" y1="108" x2="150" y2="108" />
        {/* fixed platen */}
        <rect className="ma-l" x="30" y="44" width="16" height="74" rx="2" />
        <rect className="ma-f" x="30" y="44" width="16" height="74" rx="2" />
        {[52, 64, 76, 88, 100, 110].map((y) => <circle key={y} cx="38" cy={y} r="1" fill="currentColor" />)}
        {/* moving platen + ram */}
        <rect className="ma-l ma-ram" x="98" y="48" width="16" height="66" rx="2" />
        <rect className="ma-f ma-ram" x="98" y="48" width="16" height="66" rx="2" />
        {/* mold with cavity */}
        <rect className="ma-a" x="54" y="62" width="38" height="38" rx="3" />
        <line className="ma-s" x1="73" y1="62" x2="73" y2="100" />
        <circle className="ma-s" cx="66" cy="81" r="5" /><circle className="ma-s" cx="80" cy="81" r="5" />
        {/* barrel with heater bands + hopper + screw */}
        <rect className="ma-l" x="128" y="74" width="86" height="22" rx="9" />
        <rect className="ma-f" x="128" y="74" width="86" height="22" rx="9" />
        {[146, 160, 174, 188].map((x) => <line key={x} className="ma-s" x1={x} y1="74" x2={x} y2="96" />)}
        <path className="ma-l" d="M168,74 l9,-18 l18,0 l9,18" />
        {[176, 181, 186, 191].map((x, i) => <circle key={x} cx={x} cy={62 + (i % 2) * 4} r="1.4" fill="currentColor" opacity="0.6" />)}
        <line className="ma-a ma-ram" x1="128" y1="85" x2="168" y2="85" />
        <path className="ma-a" d="M128,85 l-12,0" />
        {/* live melt-temp micro-trace */}
        <polyline className="ma-a ma-trace" points="150,40 156,36 162,44 168,38 174,42 180,37 186,41" opacity="0.8" />
      </g>
      <Callout ax={73} ay={81} lx={40} ly={34} label="CLAMP" value="90 t" />
      <Callout ax={188} ay={85} lx={206} ly={120} label="MELT TEMP" value="230°C" />
    </svg>
  );
}

function Hydraulic({ uid }: { uid: string }) {
  return (
    <svg viewBox="0 0 260 160" className="ma h-full w-full" role="img" aria-label="Hydraulic power unit digital-twin schematic">
      <style>{STYLE}</style>
      <Chrome uid={uid} title="HYDRAULIC UNIT" code="HPU-50" />
      <g filter={`url(#glow-${uid})`}>
        <line className="ma-s" x1="20" y1="126" x2="240" y2="126" />
        {/* reservoir with oil level + sight glass */}
        <rect className="ma-l" x="22" y="82" width="92" height="42" rx="3" />
        <rect className="ma-f" x="22" y="82" width="92" height="42" rx="3" />
        <line className="ma-s" x1="22" y1="96" x2="114" y2="96" />
        <rect className="ma-a" x="100" y="98" width="6" height="20" rx="1" />
        {/* motor + pump with coupling */}
        <circle className="ma-l" cx="48" cy="58" r="18" />
        <g className="ma-spin" style={{ transformOrigin: "48px 58px" }}>
          {Array.from({ length: 8 }).map((_, i) => {
            const a = (i / 8) * Math.PI * 2;
            return <line key={i} className="ma-s" x1={48 + Math.cos(a) * 6} y1={58 + Math.sin(a) * 6} x2={48 + Math.cos(a) * 16} y2={58 + Math.sin(a) * 16} />;
          })}
        </g>
        <rect className="ma-a" x="64" y="52" width="6" height="12" rx="1" />
        <circle className="ma-l" cx="86" cy="58" r="12" />
        <circle className="ma-f" cx="86" cy="58" r="12" />
        {/* manifold block + pipes with flow */}
        <rect className="ma-l" x="118" y="62" width="20" height="26" rx="2" />
        <path className="ma-l ma-flow" d="M98,58 h22 M138,70 h26 v-26 h12" />
        {/* accumulator */}
        <rect className="ma-a" x="160" y="36" width="22" height="50" rx="10" />
        <line className="ma-s" x1="160" y1="52" x2="182" y2="52" />
        <text x="171" y="64" fontSize="6" className="ma-t" textAnchor="middle">N₂</text>
        {/* pressure gauge with ticks + needle */}
        <circle className="ma-l" cx="212" cy="58" r="18" />
        <circle className="ma-f" cx="212" cy="58" r="18" />
        {Array.from({ length: 9 }).map((_, i) => {
          const a = (-Math.PI * 0.7) + (i / 8) * (Math.PI * 1.4);
          return <line key={i} className="ma-s" x1={212 + Math.cos(a) * 14} y1={58 + Math.sin(a) * 14} x2={212 + Math.cos(a) * 17} y2={58 + Math.sin(a) * 17} />;
        })}
        <line className="ma-a ma-needle" x1="212" y1="58" x2="212" y2="46" />
        <circle cx="212" cy="58" r="2" fill="var(--verified)" />
      </g>
      <Callout ax={212} ay={58} lx={206} ly={92} label="PRESSURE" value="180 bar" />
      <Callout ax={86} ay={58} lx={70} ly={34} label="OIL TEMP" value="46°C" />
    </svg>
  );
}

const ART: Record<Kind, (p: { uid: string }) => JSX.Element> = { conveyor: Conveyor, press: Press, hydraulic: Hydraulic };

/** Map a machine code / fault code / class name to one of the three illustrations. */
export function kindFor(text: string | undefined): Kind {
  const t = (text || "").toLowerCase();
  if (t.includes("imx") || t.includes("press") || t.includes("inject") || t.includes("e12")) return "press";
  if (t.includes("hpu") || t.includes("hydraul") || t.includes("p09")) return "hydraulic";
  return "conveyor";
}

export function MachineArt({ kind, className }: { kind: Kind; className?: string }) {
  const Art = ART[kind] ?? Conveyor;
  return (
    <div className={className} aria-hidden>
      <Art uid={kind} />
    </div>
  );
}
