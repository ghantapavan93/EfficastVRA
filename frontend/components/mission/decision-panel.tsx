"use client";

import { CheckCircle2, Coins, ShieldAlert, TrendingUp } from "lucide-react";
import { useDecision } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Badge, Chip } from "@/components/forge/primitives";
import { EmptyState, ErrorState, LoadingState } from "@/components/forge/states";
import type { DecisionOption, DecisionView, FmeaRow } from "@/lib/types";

const usd = (n: number) => `$${n.toLocaleString()}`;

export function DecisionPanel({ incidentId }: { incidentId: string }) {
  const { data, isLoading, isError, refetch } = useDecision(incidentId, 3000);
  if (isLoading) return <LoadingState label="Computing decision intelligence" />;
  if (isError || !data) return <ErrorState message="Decision intelligence unavailable." onRetry={() => refetch()} />;
  if (!data.available) return <EmptyState title="No decision intelligence yet" description="Available once the recovery is being verified." />;

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-line bg-surface-1 p-4">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-agent" aria-hidden />
          <h2 className="text-sm font-semibold text-ink-hi">Decision intelligence</h2>
          <span className="text-[12px] text-ink-mut">risk-adjusted · advisory</span>
          <Badge tone={data.p_relapse >= 0.6 ? "failure" : "verified"} className="ml-auto">
            {Math.round(data.p_relapse * 100)}% relapse risk ({data.forecast_state})
          </Badge>
        </div>
        <p className="mt-2 text-sm text-ink">{data.summary}</p>
      </section>

      {/* production & cost exposure */}
      <section className="rounded-xl border border-line bg-surface-1 p-4">
        <div className="label mb-2 flex items-center gap-1.5"><Coins className="h-3.5 w-3.5 text-ink-mut" aria-hidden /> Production &amp; cost exposure</div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Stat label="Units remaining" value={data.impact.units_remaining.toLocaleString()} />
          <Stat label="Throughput / hr" value={String(data.impact.throughput_per_hour)} />
          <Stat label="Hours to complete" value={`${data.impact.hours_to_complete} h`} />
          <Stat label="False-closure exposure" value={usd(data.impact.false_closure_exposure_usd)} tone="failure" />
        </div>
        <p className="mt-2 text-[11px] text-ink-mut">
          Assumptions (illustrative): downtime {usd(data.impact.assumptions.downtime_cost_per_hour)}/h · scrap{" "}
          {usd(data.impact.assumptions.scrap_cost_per_unit)}/unit · contingency prep {usd(data.impact.assumptions.contingency_prep_cost)}.
        </p>
      </section>

      {/* risk-adjusted options */}
      <section className="rounded-xl border border-line bg-surface-1 p-4">
        <div className="label mb-1">Risk-adjusted options (expected cost)</div>
        <p className="mb-3 text-xs text-ink">{data.recommendation.why}</p>
        <div className="grid gap-2 sm:grid-cols-3">
          {data.options.map((o: DecisionOption) => (
            <div
              key={o.action}
              className={cn(
                "rounded-lg border bg-surface-2 p-3",
                o.recommended ? "border-verified" : "border-line",
              )}
              style={o.recommended ? { borderWidth: 2 } : undefined}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-ink">{o.label}</span>
                {o.recommended && <Badge tone="verified"><CheckCircle2 className="h-3 w-3" aria-hidden /> pick</Badge>}
              </div>
              <div className="mono mt-1 text-lg text-ink-hi">{usd(o.expected_cost_usd)}</div>
              <p className="mt-1 text-[11px] text-ink-mut">{o.rationale}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FMEA */}
      <section className="rounded-xl border border-line bg-surface-1 p-4">
        <div className="label mb-1 flex items-center gap-1.5"><ShieldAlert className="h-3.5 w-3.5 text-ink-mut" aria-hidden /> Failure mode &amp; effects (FMEA · RPN = S×O×D)</div>
        <p className="mb-2 text-[11px] text-ink-mut">{data.fmea_note}</p>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-ink-mut">
                <th className="py-1 pr-2 text-left font-normal">Failure mode</th>
                <th className="px-1 text-center font-normal">S</th>
                <th className="px-1 text-center font-normal">O</th>
                <th className="px-1 text-center font-normal">D</th>
                <th className="px-1 text-center font-normal">RPN</th>
                <th className="pl-1 text-center font-normal">blind</th>
              </tr>
            </thead>
            <tbody>
              {data.fmea.map((m: FmeaRow) => (
                <tr key={m.failure_mode} className="border-t border-line">
                  <td className="py-1.5 pr-2 text-ink">
                    <div className="font-medium">{m.failure_mode}</div>
                    <div className="text-[11px] text-ink-mut">{m.effect}</div>
                  </td>
                  <td className="px-1 text-center mono text-ink">{m.severity}</td>
                  <td className="px-1 text-center mono text-ink">{m.occurrence}</td>
                  <td className="px-1 text-center mono text-ink">{m.detection}</td>
                  <td className="px-1 text-center"><span className={cn("mono", m.rpn >= 200 ? "text-failure" : m.rpn >= 100 ? "text-warning" : "text-verified")}>{m.rpn}</span></td>
                  <td className="pl-1 text-center mono text-ink-mut line-through">{m.rpn_without_agent}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <p className="rounded-lg border border-line bg-surface-1 px-3 py-2 text-[11px] text-ink-mut">
        {data.advisory}
      </p>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "failure" }) {
  return (
    <div className="rounded-md border border-line bg-surface-2 p-2.5">
      <div className="label">{label}</div>
      <div className={cn("mono mt-1 text-sm", tone === "failure" ? "text-failure" : "text-ink-hi")}>{value}</div>
    </div>
  );
}
