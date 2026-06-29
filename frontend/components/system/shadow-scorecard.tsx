"use client";

import { AlertTriangle, CheckCircle2, MinusCircle, ShieldCheck, XCircle } from "lucide-react";
import { useShadowScorecard } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Badge, Chip, SectionLabel } from "@/components/forge/primitives";
import { CountUp } from "@/components/forge/count-up";
import type { Tone } from "@/lib/state-meta";
import type { ShadowScenarioRow } from "@/lib/types";

const DISPO_TONE: Record<string, Tone> = {
  verified: "verified",
  failed: "failure",
  insufficient_evidence: "steel",
  conditional: "pending",
  reopened: "warning",
  in_progress: "agent",
  escalated: "warning",
};
const SHORT: Record<string, string> = {
  verified: "Verified",
  failed: "Failed",
  insufficient_evidence: "Insufficient",
  conditional: "Conditional",
  reopened: "Reopened",
  in_progress: "In progress",
  escalated: "Escalated",
};
const dispo = (k: string) => SHORT[k] ?? k;

function StatTile({ label, value, sub, tone }: { label: string; value: React.ReactNode; sub: string; tone: Tone }) {
  const ring =
    tone === "verified" ? "border-verified/40" : tone === "failure" ? "border-failure/40" : "border-line";
  const text =
    tone === "verified" ? "text-verified" : tone === "failure" ? "text-failure" : "text-ink-hi";
  return (
    <div className={cn("rounded-lg border bg-surface-2 p-3", ring)}>
      <div className="label">{label}</div>
      <div className={cn("mono mt-1 text-2xl font-bold tnum", text)}>{value}</div>
      <div className="mt-0.5 text-[11px] text-ink-mut">{sub}</div>
    </div>
  );
}

function ConfusionMatrix({ classes, matrix }: { classes: string[]; matrix: Record<string, Record<string, number>> }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[11px]">
        <thead>
          <tr>
            <th className="p-1.5 text-left text-ink-mut">
              <span className="opacity-70">actual ↓ / proposed →</span>
            </th>
            {classes.map((c) => (
              <th key={c} className="p-1.5 text-center font-medium text-ink">{dispo(c)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {classes.map((a) => (
            <tr key={a}>
              <td className="p-1.5 font-medium text-ink">{dispo(a)}</td>
              {classes.map((b) => {
                const v = matrix[a]?.[b] ?? 0;
                const diag = a === b;
                return (
                  <td key={b} className="p-1">
                    <div
                      className={cn(
                        "mono grid h-8 place-items-center rounded tnum",
                        v === 0 ? "text-ink-faint" : diag ? "bg-verified/15 text-verified" : "bg-warning/15 text-warning",
                      )}
                    >
                      {v}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Verdict({ r }: { r: ShadowScenarioRow }) {
  if (r.caught) return <Badge tone="verified"><CheckCircle2 className="h-3 w-3" aria-hidden /> caught</Badge>;
  if (r.agree) return <Badge tone="verified"><CheckCircle2 className="h-3 w-3" aria-hidden /> agrees</Badge>;
  if (r.abstained) return <Badge tone="warning"><MinusCircle className="h-3 w-3" aria-hidden /> more cautious</Badge>;
  return <Badge tone="failure"><XCircle className="h-3 w-3" aria-hidden /> diverges</Badge>;
}

function ScenarioRow({ r }: { r: ShadowScenarioRow }) {
  return (
    <div className="rounded-lg border border-line bg-surface-1 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-ink">{r.title}</span>
            {r.false_verification && (
              <Badge tone="failure"><AlertTriangle className="h-3 w-3" aria-hidden /> false verification</Badge>
            )}
          </div>
          <p className="mt-0.5 max-w-2xl text-[12px] text-ink-mut">{r.description}</p>
        </div>
        <div className="flex items-center gap-1.5">
          <Badge tone={DISPO_TONE[r.expected] ?? "steel"}>plant: {dispo(r.expected)}</Badge>
          <span className="text-ink-mut">→</span>
          <Badge tone={DISPO_TONE[r.proposed] ?? "steel"}>us: {dispo(r.proposed)}</Badge>
          <Verdict r={r} />
        </div>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px] text-ink-mut">
        {r.signature_rung && <Chip>{r.signature_rung.replace(/_/g, " ")}</Chip>}
        {r.comparability && <Chip>conditions {r.comparability.toLowerCase().replace(/_/g, " ")}</Chip>}
        {r.sensor_trust && <Chip>sensor {r.sensor_trust}</Chip>}
        <Chip>{r.events_accepted}/{r.events_total} events</Chip>
        {Object.entries(r.anomalies).map(([k, n]) => (
          <span key={k} className="rounded border border-warning/40 px-1.5 py-0.5 text-warning">{k.replace(/_/g, " ")} ×{n}</span>
        ))}
      </div>
      {r.reasons.length > 0 && <p className="mt-1.5 text-[11px] text-ink">{r.reasons.join(" ")}</p>}
    </div>
  );
}

export function ShadowScorecard() {
  const { data } = useShadowScorecard(15000);
  if (!data) return null;
  const fc = data.false_closure;
  const sm = data.summary;
  const recallPct = fc.recall != null ? Math.round(fc.recall * 100) : null;
  const agreePct = sm.agreement_rate != null ? Math.round(sm.agreement_rate * 100) : null;

  return (
    <section className="alive mt-4 rounded-xl border border-line-strong bg-surface-1 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-agent" aria-hidden />
          <SectionLabel className="mb-0">Shadow Mode Scorecard</SectionLabel>
          <span className="text-[12px] text-ink-mut">Tier-0 · evaluate without touching their system</span>
        </div>
        <Badge tone="verified"><ShieldCheck className="h-3 w-3" aria-hidden /> {sm.writes_performed} writes to their system</Badge>
      </div>
      <p className="mt-1 mb-3 text-xs text-ink-mut">
        The same deterministic cores, run over labeled event bundles, compared to the outcome the plant
        published — the artifact an Efficast evaluator would ask for before trusting (or connecting) anything.
      </p>

      <div className="grid gap-2 sm:grid-cols-4">
        <StatTile label="Relapses caught" tone="verified"
          value={<><CountUp value={recallPct ?? 0} />%</>} sub={`${fc.caught}/${fc.positives} true false-closures`} />
        <StatTile label="Wrongly verified" tone={fc.missed_catastrophic === 0 ? "verified" : "failure"}
          value={<CountUp value={fc.missed_catastrophic} />} sub="failed recoveries rubber-stamped" />
        <StatTile label="Agreement w/ plant" tone="steel"
          value={<><CountUp value={agreePct ?? 0} />%</>} sub={`${sm.scenarios} scenarios · κ ${sm.cohens_kappa ?? "—"}`} />
        <StatTile label="False alarms" tone="steel"
          value={<CountUp value={fc.fp} />} sub="genuine recoveries flagged failed" />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <div>
          <div className="label mb-2">Confusion matrix</div>
          <ConfusionMatrix classes={data.confusion_matrix.classes} matrix={data.confusion_matrix.matrix} />
          <p className="mt-2 text-[11px] text-ink-mut">
            Diagonal = agreement. Off-diagonal here is us being <span className="text-warning">more cautious</span> than
            the plant (abstaining on a confound / untrusted sensor), never a missed relapse.
          </p>
        </div>
        <div>
          <div className="label mb-2">Reconciliation — {sm.events_accepted}/{sm.events_total} events accepted</div>
          <div className="flex flex-wrap gap-1.5">
            {Object.keys(data.reconciliation_totals).length === 0 ? (
              <span className="text-[12px] text-ink-mut">clean stream</span>
            ) : (
              Object.entries(data.reconciliation_totals).map(([k, n]) => (
                <Chip key={k}>{k.replace(/_/g, " ")} ×{n}</Chip>
              ))
            )}
          </div>
          <p className="mt-2 text-[11px] text-ink-mut">
            Duplicated webhooks and suspect samples are deduped/flagged before anything is scored — never
            dropped silently.
          </p>
        </div>
      </div>

      <div className="mt-4 space-y-2">
        <div className="label">Per-scenario verdicts</div>
        {data.scenarios.map((r) => <ScenarioRow key={r.key} r={r} />)}
      </div>

      <p className="mt-3 border-t border-line pt-3 text-[11px] text-ink-mut">{data.basis}</p>
    </section>
  );
}
