"use client";

import { ChevronDown } from "lucide-react";
import { useState } from "react";
import type { Condition } from "@/lib/types";
import { cn } from "@/lib/utils";
import { fmtNum } from "@/lib/utils";
import { ConditionPill } from "@/components/forge/badges";
import { Chip, Tooltip } from "@/components/forge/primitives";

function targetText(c: Condition): string {
  switch (c.op) {
    case "<=": return `≤ ${c.threshold} ${c.unit}`;
    case "<": return `< ${c.threshold} ${c.unit}`;
    case ">=": return `≥ ${c.threshold} ${c.unit}`;
    case ">": return `> ${c.threshold} ${c.unit}`;
    case "within_pct": return `within ${((c.threshold ?? 0) * 100).toFixed(0)}% of ${c.baseline} ${c.unit}`;
    case "declining": return "trend declining";
    case "not_recur": return `${c.fault_code} must not recur`;
    case "count_gte": return `≥ ${c.threshold} ${c.unit}`;
    default: return `${c.op} ${c.threshold ?? ""}`;
  }
}

function deadlineText(c: Condition): string {
  if (c.deadline_kind === "cycles" && c.deadline_value) return `within ${c.deadline_value} cycles`;
  if (c.deadline_kind === "minutes" && c.deadline_value) return `within ${c.deadline_value} min`;
  if (c.deadline_kind === "window") return "across the window";
  return "—";
}

export function ConditionRow({ c }: { c: Condition }) {
  const [open, setOpen] = useState(false);
  const currentLabel =
    c.op === "not_recur"
      ? c.current_value && c.current_value > 0 ? `${c.current_value} recurrence` : "absent"
      : c.op === "count_gte"
        ? `${fmtNum(c.current_value, 0)} cycles`
        : c.current_value === null ? "—" : `${fmtNum(c.current_value, 2)} ${c.unit}`;

  const violated = c.status === "VIOLATED";
  return (
    <div className={cn("rounded-lg border bg-surface-1 transition-colors", violated ? "border-failure/40" : "border-line")}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-3 py-2.5 text-left"
        aria-expanded={open}
      >
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-ink">{c.label}</span>
            {c.sensor_tag && <Chip>{c.sensor_tag}</Chip>}
          </div>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-ink-mut">
            <span>target <span className="text-ink">{targetText(c)}</span></span>
            <span className="text-ink-faint">·</span>
            <span>{deadlineText(c)}</span>
          </div>
        </div>
        <div className="text-right">
          <div className={cn("mono text-sm", violated ? "text-failure" : "text-ink-hi")}>{currentLabel}</div>
          <div className="mt-0.5"><ConditionPill status={c.status} /></div>
        </div>
        <ChevronDown className={cn("h-4 w-4 shrink-0 text-ink-faint transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className="border-t border-line px-3 py-2.5 text-xs text-ink-mut">
          {c.rationale && <p className="mb-2 text-ink">{c.rationale}</p>}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <span><span className="label mr-1">Source</span>{c.sensor_tag ?? "evidence"}</span>
            <Tooltip content="The contract clause this condition derives from.">
              <span className="cursor-help"><span className="label mr-1">Policy</span><span className="mono">{c.policy_ref}</span></span>
            </Tooltip>
            {c.baseline !== null && <span><span className="label mr-1">Baseline</span><span className="mono">{c.baseline} {c.unit}</span></span>}
          </div>
        </div>
      )}
    </div>
  );
}
