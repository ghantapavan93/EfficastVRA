"use client";

import { FlaskConical } from "lucide-react";

/** Persistent, visible disclosure that this is synthetic + an independent prototype.
 * Required by the product brief — never hidden in a footer. */
export function SyntheticBadge({ compact = false }: { compact?: boolean }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-pill border border-brand/30 bg-brand-soft px-2.5 py-1 text-[11px] font-medium text-brand"
      title="Synthetic manufacturing environment · Independent Efficast-aligned prototype · No physical machine control"
    >
      <FlaskConical className="h-3 w-3" aria-hidden />
      {compact ? "SYNTHETIC DEMO" : "Synthetic environment · Independent Efficast-aligned prototype"}
    </span>
  );
}
