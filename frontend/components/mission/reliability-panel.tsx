"use client";

import { Activity, BarChart3, Gauge, GitBranch, Sigma } from "lucide-react";
import { useReliability } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Badge, Chip } from "@/components/forge/primitives";
import { EmptyState, ErrorState, LoadingState } from "@/components/forge/states";

const pct = (n: number | undefined) => (n == null ? "—" : `${Math.round(n * 100)}%`);

export function ReliabilityPanel({ incidentId }: { incidentId: string }) {
  const { data, isLoading, isError, refetch } = useReliability(incidentId, 3000);
  if (isLoading) return <LoadingState label="Computing recovery confidence" />;
  if (isError || !data) return <ErrorState message="Reliability statistics unavailable." onRetry={() => refetch()} />;
  if (!data.available) return <EmptyState title="No statistics yet" description={data.reason || "Available once the recovery is being verified."} />;

  const stable = data.stable_cycles ?? 0;
  const need = data.cycles_for_target ?? 0;
  const proven = stable >= need && stable > 0;
  const progress = need > 0 ? Math.min(100, (stable / need) * 100) : 0;
  const hazard = data.hazard;
  const hazardTone = hazard?.pattern === "early_life" ? "failure" : hazard?.pattern === "wear_out" ? "warning" : "pending";

  return (
    <div className="space-y-4">
      {/* verdict confidence hero */}
      <section className="rounded-xl border border-line bg-surface-1 p-4">
        <div className="flex items-center gap-2">
          <Sigma className="h-4 w-4 text-agent" aria-hidden />
          <h2 className="text-sm font-semibold text-ink-hi">Recovery confidence</h2>
          <span className="text-[12px] text-ink-mut">reliability demonstration · advisory</span>
          <Badge tone={proven ? "verified" : "pending"} className="ml-auto">
            {proven ? "statistically demonstrated" : "not yet proven"}
          </Badge>
        </div>
        <p className="mt-2 text-sm text-ink">{data.verdict_confidence}</p>
      </section>

      {/* the success-run statistics */}
      <section className="rounded-xl border border-line bg-surface-1 p-4">
        <div className="label mb-2 flex items-center gap-1.5"><Gauge className="h-3.5 w-3.5 text-ink-mut" aria-hidden /> Zero-failure demonstration test</div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Stat label="Stable cycles" value={`${stable} / ${data.required_stable_cycles ?? "—"}`} hint="fault-free run / contract window" />
          <Stat label="Confidence now" value={pct(data.confidence_now)} tone={proven ? "verified" : "warning"} hint={`relapse ≤ ${pct(data.target_relapse_rate)}/cycle`} />
          <Stat label="At full window" value={pct(data.confidence_at_window)} hint="if the window completes clean" />
          <Stat label="Cycles for target" value={String(need)} hint={`for ${pct(data.confidence_level)} confidence`} />
        </div>

        {/* progress toward the target-confidence cycle count */}
        <div className="mt-3">
          <div className="mb-1 flex items-center justify-between text-[11px] text-ink-mut">
            <span>Progress to {pct(data.confidence_level)} confidence ({stable}/{need} cycles)</span>
            <span className="mono">{Math.round(progress)}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-pill bg-surface-2" role="progressbar" aria-valuenow={Math.round(progress)} aria-valuemin={0} aria-valuemax={100}>
            <div className={cn("h-full rounded-pill", proven ? "bg-verified" : "bg-agent")} style={{ width: `${progress}%` }} />
          </div>
        </div>

        <div className="mt-3 text-[12px] text-ink">
          <div className="rounded-md border border-line bg-surface-2 p-2.5">
            Demonstrated ceiling: per-cycle relapse{" "}
            <span className="mono text-ink-hi">≤ {pct(data.demonstrated_relapse_ceiling)}</span>{" "}
            at {pct(data.confidence_level)} confidence.
          </div>
        </div>
      </section>

      {/* Wald sequential test (SPRT) */}
      {data.sprt && (
        <section className="rounded-xl border border-line bg-surface-1 p-4">
          <div className="label mb-2 flex items-center gap-1.5"><GitBranch className="h-3.5 w-3.5 text-ink-mut" aria-hidden /> Sequential test (Wald SPRT)</div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={data.sprt.decision === "accept" ? "verified" : data.sprt.decision === "reject" ? "failure" : "pending"}>
              {data.sprt.decision === "continue" ? "undecided" : data.sprt.decision}
            </Badge>
            {data.sprt.decided_at_cycle != null && <Chip>decided at cycle {data.sprt.decided_at_cycle}</Chip>}
            <Chip>H₀ ≤{pct(data.sprt.p0)} vs H₁ ≥{pct(data.sprt.p1)}</Chip>
            <Chip>α=β={pct(data.sprt.alpha)}</Chip>
          </div>
          <p className="mt-2 text-sm text-ink">{data.sprt_summary}</p>
          {/* LLR position between the accept (down) and reject (up) bounds */}
          <div className="mt-3">
            <div className="mb-1 flex items-center justify-between text-[11px] text-ink-mut">
              <span>accept ≤ {data.sprt.accept_bound}</span>
              <span className="mono text-ink">LLR {data.sprt.llr}</span>
              <span>reject ≥ {data.sprt.reject_bound}</span>
            </div>
            <div className="relative h-2 w-full overflow-hidden rounded-pill bg-surface-2">
              {(() => {
                const lo = data.sprt.accept_bound, hi = data.sprt.reject_bound;
                const x = Math.max(0, Math.min(100, ((data.sprt.llr - lo) / (hi - lo)) * 100));
                return <div className="absolute top-1/2 h-3 w-1 -translate-y-1/2 rounded-pill bg-agent" style={{ left: `${x}%` }} aria-hidden />;
              })()}
            </div>
          </div>
        </section>
      )}

      {/* bathtub-curve hazard read */}
      {hazard && (
        <section className="rounded-xl border border-line bg-surface-1 p-4">
          <div className="label mb-2 flex items-center gap-1.5"><Activity className="h-3.5 w-3.5 text-ink-mut" aria-hidden /> Hazard read (bathtub curve)</div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={hazardTone}>{hazard.pattern.replace(/_/g, " ")}</Badge>
            {hazard.weibull_shape_hint && <Chip>Weibull {hazard.weibull_shape_hint}</Chip>}
            {hazard.mean_cycles_to_relapse != null && <Chip>mean relapse ≈ cycle {hazard.mean_cycles_to_relapse}</Chip>}
            <Chip>n = {hazard.sample_size} ({hazard.data_confidence})</Chip>
          </div>
          <p className="mt-2 text-sm text-ink">{hazard.interpretation}</p>
          <p className="mt-1 text-[11px] text-ink-mut">{hazard.data_note}</p>
        </section>
      )}

      {/* recommendation on the window */}
      {data.recommendation && (
        <section className="rounded-xl border border-line bg-surface-1 p-4">
          <div className="label mb-1 flex items-center gap-1.5"><BarChart3 className="h-3.5 w-3.5 text-ink-mut" aria-hidden /> Window recommendation</div>
          <p className="text-sm text-ink">{data.recommendation}</p>
        </section>
      )}

      <p className="rounded-lg border border-line bg-surface-1 px-3 py-2 text-[11px] text-ink-mut">{data.advisory}</p>
    </div>
  );
}

function Stat({ label, value, tone, hint }: { label: string; value: string; tone?: "failure" | "verified" | "warning"; hint?: string }) {
  return (
    <div className="rounded-md border border-line bg-surface-2 p-2.5">
      <div className="label">{label}</div>
      <div className={cn("mono mt-1 text-sm", tone === "failure" ? "text-failure" : tone === "verified" ? "text-verified" : tone === "warning" ? "text-warning" : "text-ink-hi")}>{value}</div>
      {hint && <div className="mt-0.5 text-[10px] text-ink-mut">{hint}</div>}
    </div>
  );
}
