"use client";

import { motion } from "framer-motion";
import { ArrowRight, Boxes, Cpu, RotateCcw, TriangleAlert } from "lucide-react";
import Link from "next/link";
import type { MissionSummary } from "@/lib/types";
import { cn } from "@/lib/utils";
import { AgentActivityIndicator } from "@/components/forge/badges";
import { StateBadge, SeverityIndicator } from "@/components/forge/badges";
import { Chip, ProgressBar } from "@/components/forge/primitives";

export function MissionCard({ m, prominent = false }: { m: MissionSummary; prominent?: boolean }) {
  if (prominent) return <ProminentCard m={m} />;
  return (
    <Link
      href={`/missions/${m.id}`}
      className="group flex items-center gap-4 rounded-lg border border-line bg-surface-1 px-4 py-3 transition-colors hover:border-line-strong hover:bg-surface-2"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="mono text-xs text-ink-mut">{m.id}</span>
          <StateBadge state={m.state} />
          {m.reopened_count > 0 && (
            <Chip className="text-failure">
              <RotateCcw className="h-3 w-3" /> reopened ×{m.reopened_count}
            </Chip>
          )}
        </div>
        <div className="mt-1 truncate text-sm text-ink">{m.title}</div>
      </div>
      <div className="hidden items-center gap-2 md:flex">
        {m.missing_evidence > 0 && <Chip className="text-pending">{m.missing_evidence} evidence</Chip>}
        <SeverityIndicator severity={m.severity} />
      </div>
      <div className="w-28 shrink-0">
        <div className="mb-1 flex justify-between text-[10px] text-ink-faint">
          <span>progress</span>
          <span className="mono">{m.recovery_progress}%</span>
        </div>
        <ProgressBar value={m.recovery_progress} tone={m.state === "VERIFIED_RECOVERY" ? "verified" : "agent"} />
      </div>
      <ArrowRight className="h-4 w-4 shrink-0 text-ink-faint transition-transform group-hover:translate-x-0.5 group-hover:text-ink" />
    </Link>
  );
}

function ProminentCard({ m }: { m: MissionSummary }) {
  const reopened = m.reopened_count > 0;
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.26, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        "relative overflow-hidden rounded-xl border bg-surface-1 p-5",
        reopened
          ? "border-failure/30 shadow-[0_20px_55px_-26px_rgba(255,93,93,.55)]"
          : "border-agent/30 shadow-[0_20px_55px_-26px_rgba(76,125,255,.6)]",
      )}
    >
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-agent to-transparent opacity-60" />
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="mono text-xs text-ink-mut">{m.id}</span>
            <StateBadge state={m.state} />
            <SeverityIndicator severity={m.severity} />
            {reopened && (
              <Chip className="text-failure">
                <RotateCcw className="h-3 w-3" /> reopened ×{m.reopened_count}
              </Chip>
            )}
          </div>
          <h2 className="mt-2 text-xl font-semibold tracking-tight text-ink-hi">{m.title}</h2>
          <p className="mt-1 max-w-2xl text-sm text-ink-mut">{m.objective}</p>
        </div>
        <AgentActivityIndicator label={m.next_action} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat icon={Cpu} label="Machine" value={m.machine?.code ?? "—"} sub={m.machine?.name} />
        <Stat icon={Boxes} label="Order" value={m.order?.id ?? "—"} sub={m.order ? `${m.order.qty_remaining.toLocaleString()} units left` : undefined} />
        <Stat icon={TriangleAlert} label="Fault" value={m.fault_code ?? "—"} sub={m.contract_no ? `${m.contract_no} v${m.contract_version}` : "no contract"} />
        <div className="rounded-lg border border-line bg-raised px-3 py-2">
          <div className="label">Recovery progress</div>
          <div className="mono mt-1 text-lg text-ink-hi">{m.recovery_progress}%</div>
          <div className="mt-1.5"><ProgressBar value={m.recovery_progress} tone={m.state === "VERIFIED_RECOVERY" ? "verified" : reopened ? "failure" : "agent"} /></div>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-ink-mut">
          <span className="label">Next</span>
          <span className="text-ink">{m.next_action}</span>
          <span className="text-ink-faint">·</span>
          <span>owner: {m.owner}</span>
        </div>
        <Link
          href={`/missions/${m.id}`}
          className="inline-flex h-9 items-center gap-2 rounded-[10px] bg-agent px-4 text-sm font-semibold text-white transition-transform hover:scale-[1.02]"
        >
          Open mission <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </motion.div>
  );
}

function Stat({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="rounded-lg border border-line bg-raised px-3 py-2">
      <div className="label flex items-center gap-1.5">
        <Icon className="h-3 w-3" /> {label}
      </div>
      <div className="mono mt-1 truncate text-sm text-ink-hi">{value}</div>
      {sub && <div className="truncate text-[11px] text-ink-mut">{sub}</div>}
    </div>
  );
}
