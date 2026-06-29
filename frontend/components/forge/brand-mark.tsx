"use client";

/**
 * BrandMark — the product's generative emblem: a recovery signal that dips on a fault and resolves into a
 * verified node. Scales from a 16px favicon to a hero lockup. Original SVG; uses theme tokens.
 */
export function BrandMark({ size = 24, className, animated = false }: { size?: number; className?: string; animated?: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" className={className} role="img" aria-label="Verified Recovery Agent">
      <defs>
        <linearGradient id="bm-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="var(--agent)" />
          <stop offset="1" stopColor="var(--verified)" />
        </linearGradient>
      </defs>
      <rect x="1.5" y="1.5" width="29" height="29" rx="8" fill="var(--surface-2)" stroke="url(#bm-grad)" strokeWidth="1.6" />
      {/* recovery signal — dips on the fault, recovers, settles */}
      <path
        d="M6,18 L10.5,18 L13,24 L16,8.5 L19,19 L21,15 L25,15"
        fill="none" stroke="var(--agent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
        style={animated ? { strokeDasharray: 60, animation: "bm-draw 2.6s ease-in-out infinite" } : undefined}
      />
      {/* verified node + check */}
      <circle cx="25" cy="15" r="3.4" fill="var(--verified)" />
      <path d="M23.5,15 l1,1.15 l2.1,-2.5" fill="none" stroke="var(--surface-2)" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      {animated && <style>{`@keyframes bm-draw{0%{stroke-dashoffset:60}45%{stroke-dashoffset:0}80%{stroke-dashoffset:0}100%{stroke-dashoffset:60}}`}</style>}
    </svg>
  );
}
