"use client";

import { motion } from "framer-motion";
import { AlertOctagon, Bot, CheckCircle2, FileSignature, Gavel, RotateCcw, ShieldAlert, ShieldCheck, Workflow } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { announce } from "@/lib/announce";
import { useAudit, useTimeline } from "@/lib/hooks";
import type { TimelineCycle } from "@/lib/types";
import { cn, fmtClock } from "@/lib/utils";
import { RecoveryTrajectory } from "@/components/charts/recovery-trajectory";
import { ForecastPanel } from "@/components/timeline/forecast-panel";
import { Badge, Chip, SectionLabel } from "@/components/forge/primitives";
import { ErrorState, LoadingState } from "@/components/forge/states";

type Metric = "vibration" | "temperature" | "cycle_time" | "scrap_pct";
const METRICS: { key: Metric; label: string; unit: string; threshold: number | null; baseline: number }[] = [
  { key: "vibration", label: "Vibration RMS", unit: "mm/s", threshold: 4.0, baseline: 3.1 },
  { key: "temperature", label: "Temperature", unit: "°C", threshold: null, baseline: 63 },
  { key: "cycle_time", label: "Cycle time", unit: "s", threshold: 12.81, baseline: 12.2 },
  { key: "scrap_pct", label: "Scrap", unit: "%", threshold: 2.0, baseline: 1.6 },
];

const TYPE_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  STATE_TRANSITION: Workflow,
  CONTRACT_DRAFTED: FileSignature,
  CONTRACT_VIOLATED: AlertOctagon,
  INCIDENT_REOPENED: RotateCcw,
  APPROVAL_RECORDED: Gavel,
  RECOVERY_VERIFIED: CheckCircle2,
};

function AuditIntegrityBadge({ incidentId }: { incidentId: string }) {
  const { data } = useAudit(incidentId);
  const integrity = data?.integrity;
  if (!integrity) return null;
  // An empty chain (count 0) is not "verified" — there is nothing to attest. Only claim verified once
  // there are entries AND the recomputed chain matches.
  if (integrity.ok && integrity.count === 0)
    return (
      <span title="No audit entries yet">
        <Badge tone="pending">
          <ShieldCheck className="h-3 w-3" aria-hidden /> tamper-evident · no entries
        </Badge>
      </span>
    );
  if (integrity.ok)
    return (
      <span title={`Hash chain verified across ${integrity.count} audit entries`}>
        <Badge tone="verified">
          <ShieldCheck className="h-3 w-3" aria-hidden /> tamper-evident · verified
        </Badge>
      </span>
    );
  return (
    <span title={`Chain broken at seq ${integrity.broken_at_seq}`}>
      <Badge tone="failure">
        <ShieldAlert className="h-3 w-3" aria-hidden /> audit tampering detected
      </Badge>
    </span>
  );
}

export function VerificationTimeline({ incidentId }: { incidentId: string }) {
  const { data, isLoading, isError, refetch } = useTimeline(incidentId, 3000);
  const [metric, setMetric] = useState<Metric>("vibration");
  const announced = useRef(false);

  const recurrence = useMemo(() => data?.cycles.find((c) => c.is_recurrence) ?? null, [data]);
  const reopened = useMemo(() => data?.events.some((e) => e.type === "INCIDENT_REOPENED"), [data]);

  useEffect(() => {
    if (reopened && !announced.current) {
      announced.current = true;
      announce(`Recovery Contract violated at cycle ${recurrence?.cycle_index ?? "?"}. Work completed. Recovery not proven. Incident reopened automatically.`);
    }
  }, [reopened, recurrence?.cycle_index]);

  if (isLoading) return <LoadingState label="Loading verification timeline" />;
  if (isError || !data) return <ErrorState message="Could not load the timeline." onRetry={() => refetch()} />;

  const m = METRICS.find((x) => x.key === metric)!;

  return (
    <div className="space-y-5">
      <ForecastPanel incidentId={incidentId} />

      {/* trajectory */}
      <section className="rounded-xl border border-line bg-surface-1 p-4">
        <div className="mb-3 flex items-center justify-between">
          <SectionLabel>Expected vs actual — {m.label}</SectionLabel>
          <div className="flex gap-1">
            {METRICS.map((x) => (
              <button
                key={x.key}
                onClick={() => setMetric(x.key)}
                className={cn("rounded-md px-2 py-1 text-[11px]", metric === x.key ? "bg-agent-soft text-agent" : "text-ink-mut hover:text-ink")}
              >
                {x.label}
              </button>
            ))}
          </div>
        </div>
        <RecoveryTrajectory cycles={data.cycles} metric={metric} label={m.label} unit={m.unit} threshold={m.threshold} baseline={m.baseline} />
      </section>

      {/* cycle ticker */}
      {data.cycles.length > 0 && <CycleTicker cycles={data.cycles} />}

      {/* cycle-17 reveal */}
      {recurrence && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.52, ease: [0.3, 0.7, 0.1, 1] }}
          role="alert"
          className="overflow-hidden rounded-xl border border-failure/40 bg-failure-soft"
        >
          <div className="flex items-center gap-2 border-b border-failure/30 px-4 py-2.5 text-failure">
            <AlertOctagon className="h-4 w-4" />
            <span className="text-sm font-semibold">Recovery Contract violated at cycle {recurrence.cycle_index}.</span>
          </div>
          <div className="space-y-1 px-4 py-3 text-sm">
            <p className="text-ink">Work completed. Recovery not proven.</p>
            <p className="text-ink-mut">Incident reopened automatically — the originating fault F27 recurred during the verification window.</p>
          </div>
        </motion.div>
      )}

      {/* event spine */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <SectionLabel>Verification events</SectionLabel>
          <AuditIntegrityBadge incidentId={incidentId} />
        </div>
        <ol className="relative space-y-1 border-l border-line pl-5">
          <style>{`@keyframes evIn{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:none}}
            @keyframes evGlow{0%,100%{opacity:.55}50%{opacity:1}}`}</style>
          {data.events.map((e, i) => {
            const Icon = TYPE_ICON[e.type] ?? Bot;
            const critical = e.type === "CONTRACT_VIOLATED" || e.type === "INCIDENT_REOPENED";
            const verified = e.type === "RECOVERY_VERIFIED";
            return (
              <li key={e.seq} className="relative py-1.5"
                  style={{ animation: "evIn .42s ease-out both", animationDelay: `${Math.min(i * 45, 900)}ms` }}>
                <span
                  className={cn(
                    "absolute -left-[27px] grid h-5 w-5 place-items-center rounded-full border-2 bg-canvas",
                    critical ? "border-failure text-failure" : verified ? "border-verified text-verified" : "border-line text-ink-mut",
                  )}
                  style={critical ? { boxShadow: "0 0 12px var(--failure)", animation: "evGlow 1.8s ease-in-out infinite" }
                    : verified ? { boxShadow: "0 0 12px var(--verified)", animation: "evGlow 2.2s ease-in-out infinite" } : undefined}
                >
                  <Icon className="h-2.5 w-2.5" />
                </span>
                <div className="flex items-baseline gap-2">
                  <span className="mono text-[10px] text-ink-faint">{fmtClock(e.at)}</span>
                  <span className={cn("text-[13px]", critical ? "text-failure" : verified ? "text-verified" : "text-ink")}>{e.summary}</span>
                </div>
                <div className="mt-0.5 flex items-center gap-2 text-[10px] text-ink-faint">
                  <span>{e.actor}{e.role ? ` · ${e.role}` : ""}</span>
                  {e.prev_state && e.new_state && <Chip>{e.prev_state} → {e.new_state}</Chip>}
                </div>
              </li>
            );
          })}
        </ol>
      </section>
    </div>
  );
}

function CycleTicker({ cycles }: { cycles: TimelineCycle[] }) {
  return (
    <section className="rounded-xl border border-line bg-surface-1 p-3">
      <style>{`
        @keyframes cyPop{from{opacity:0;transform:scale(.35)}to{opacity:1;transform:none}}
        @keyframes cyFault{0%,100%{box-shadow:0 0 0 0 rgba(255,93,93,.55)}50%{box-shadow:0 0 0 4px rgba(255,93,93,.0)}}
      `}</style>
      <SectionLabel className="mb-2">Cycle-by-cycle ({cycles.length} observed)</SectionLabel>
      <div className="flex flex-wrap gap-1" role="list" aria-label="Observed cycles">
        {cycles.map((c, i) => {
          const fault = !!c.fault_code;
          return (
            <div
              key={`${c.window}-${c.cycle_index}`}
              role="listitem"
              title={`Cycle ${c.cycle_index}: vib ${c.vibration} mm/s${fault ? ` · ${c.fault_code}` : ""}`}
              className={cn(
                "grid h-6 w-6 place-items-center rounded text-[9px] font-medium",
                fault ? "bg-failure text-white ring-2 ring-failure/40" : "bg-verified-soft text-verified",
              )}
              style={{
                animation: fault
                  ? "cyPop .3s ease-out both, cyFault 1.7s ease-in-out infinite .5s"
                  : "cyPop .3s ease-out both",
                animationDelay: fault ? undefined : `${Math.min(i * 26, 1300)}ms`,
              }}
            >
              {c.cycle_index}
            </div>
          );
        })}
      </div>
      <div className="mt-2 flex items-center gap-4 text-[10px] text-ink-faint">
        <span className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-verified-soft" /> stable</span>
        <span className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-failure" /> fault recurrence</span>
      </div>
    </section>
  );
}
