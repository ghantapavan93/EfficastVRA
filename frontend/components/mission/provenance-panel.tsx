"use client";

import { CheckCircle2, FileSearch, GitCompareArrows, ShieldCheck, XCircle } from "lucide-react";
import { useProvenance } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Badge, Chip } from "@/components/forge/primitives";
import { EmptyState, ErrorState, LoadingState } from "@/components/forge/states";
import type { ProvenanceEvidence } from "@/lib/types";

const trustTone = (t: number) => (t >= 0.85 ? "verified" : t >= 0.5 ? "pending" : "failure");

export function ProvenancePanel({ incidentId }: { incidentId: string }) {
  const { data, isLoading, isError, refetch } = useProvenance(incidentId, 4000);
  if (isLoading) return <LoadingState label="Reconstructing decision provenance" />;
  if (isError || !data) return <ErrorState message="Provenance unavailable." onRetry={() => refetch()} />;
  if (!data.available) return <EmptyState title="No provenance yet" description={data.reason || "Available once a recovery contract exists."} />;

  const ev = data.evidence_summary;
  const rec = data.reconciliation;
  const audit = data.audit;

  return (
    <div className="space-y-4">
      {/* headline: can we trust this closure? */}
      <section className="rounded-xl border border-line bg-surface-1 p-4">
        <div className="flex items-center gap-2">
          <FileSearch className="h-4 w-4 text-agent" aria-hidden />
          <h2 className="text-sm font-semibold text-ink-hi">Closure provenance</h2>
          <span className="text-[12px] text-ink-mut">why decided · advisory</span>
          <Badge tone={data.trustworthy ? "verified" : "pending"} className="ml-auto">
            {data.trustworthy ? "trustworthy" : "review needed"}
          </Badge>
        </div>
        <p className="mt-2 text-sm text-ink">{data.summary}</p>
        <p className="mt-1 text-[11px] text-ink-mut">{data.note}</p>
      </section>

      {/* reconciliation + audit — the two trust gates */}
      <section className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-line bg-surface-1 p-4">
          <div className="label mb-2 flex items-center gap-1.5"><GitCompareArrows className="h-3.5 w-3.5 text-ink-mut" aria-hidden /> Action reconciliation</div>
          <div className="flex items-center gap-2">
            <Badge tone={rec?.ok ? "verified" : "failure"}>{rec?.ok ? "reconciled" : "discrepancy"}</Badge>
            <span className="text-[11px] text-ink-mut">self-reported vs actual</span>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <Chip>{rec?.proposed ?? 0} proposed</Chip>
            <Chip>{rec?.executed ?? 0} executed</Chip>
            {(rec?.failed ?? 0) > 0 && <Chip>{rec?.failed} failed</Chip>}
            {(rec?.denied ?? 0) > 0 && <Chip>{rec?.denied} denied</Chip>}
          </div>
          {rec && rec.unreconciled.length > 0 && (
            <ul className="mt-2 space-y-1 text-[11px] text-failure">
              {rec.unreconciled.map((u) => <li key={u.proposal_id}>⚠ {u.tool}: {u.issue}</li>)}
            </ul>
          )}
          <p className="mt-2 text-[11px] text-ink-mut">Cross-checks that the gateway&apos;s proposal↔execution log is internally consistent (it does not, by itself, prove an action was authorized).</p>
        </div>
        <div className="rounded-xl border border-line bg-surface-1 p-4">
          <div className="label mb-2 flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5 text-ink-mut" aria-hidden /> Audit chain</div>
          <div className="flex items-center gap-2">
            <Badge tone={audit?.ok && (audit?.count ?? 0) > 0 ? "verified" : "failure"}>
              {audit?.ok ? "intact" : "broken"}
            </Badge>
            <span className="mono text-[11px] text-ink-mut">{audit?.count ?? 0} entries</span>
          </div>
          {audit && audit.broken_at_seq != null && (
            <p className="mt-2 text-[11px] text-failure">Tamper detected at seq {audit.broken_at_seq}.</p>
          )}
          <p className="mt-2 text-[11px] text-ink-mut">Hash-chained, tamper-evident; recomputed on read.</p>
        </div>
      </section>

      {/* trust-weighted evidence */}
      <section className="rounded-xl border border-line bg-surface-1 p-4">
        <div className="label mb-2">Evidence &amp; trust</div>
        {ev && (
          <p className="mb-2 text-[12px] text-ink-mut">
            {ev.count} items · mean trust <span className="mono text-ink">{ev.mean_trust}</span> · weakest{" "}
            <span className="mono text-ink">{ev.min_trust}</span>
            {ev.weakest && ev.weakest.flags.length > 0 && ` (${ev.weakest.flags.join(", ")})`}
          </p>
        )}
        <div className="space-y-1.5">
          {(data.evidence ?? []).map((e: ProvenanceEvidence) => (
            <div key={e.evidence_id} className="flex items-center gap-2 rounded-md border border-line bg-surface-2 px-2.5 py-1.5">
              <Badge tone={trustTone(e.trust)}>{e.trust}</Badge>
              <span className="text-xs text-ink">{e.tier_label}</span>
              {e.source && <span className="text-[11px] text-ink-mut">· {e.source}</span>}
              {e.flags.map((f) => <Chip key={f}>{f}</Chip>)}
              <span className="ml-auto text-[10px] text-ink-faint">{e.status}</span>
            </div>
          ))}
          {(data.evidence ?? []).length === 0 && <p className="text-[12px] text-ink-mut">No evidence submitted yet.</p>}
        </div>
      </section>

      {/* approvals + interventions */}
      <section className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-line bg-surface-1 p-4">
          <div className="label mb-2">Human approvals</div>
          <div className="space-y-1.5">
            {(data.approvals ?? []).map((a, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                {a.decision === "approve" ? <CheckCircle2 className="h-3.5 w-3.5 text-verified" aria-hidden /> : <XCircle className="h-3.5 w-3.5 text-failure" aria-hidden />}
                <span className="text-ink">{a.decided_by}</span>
                <span className="text-[11px] text-ink-mut">({a.decided_role.replace(/_/g, " ")})</span>
                <span className="ml-auto text-[11px] text-ink-mut">{a.decision}</span>
              </div>
            ))}
            {(data.approvals ?? []).length === 0 && <p className="text-[12px] text-ink-mut">No approvals recorded yet.</p>}
          </div>
        </div>
        <div className="rounded-xl border border-line bg-surface-1 p-4">
          <div className="label mb-2">Interventions</div>
          <div className="space-y-1.5">
            {(data.interventions ?? []).map((iv) => (
              <div key={iv.sequence} className="flex items-center gap-2 text-xs">
                <span className="mono text-ink-mut">#{iv.sequence}</span>
                <span className="text-ink">{iv.title || iv.kind}</span>
                <span className={cn("ml-auto text-[11px]", iv.status === "COMPLETED" ? "text-ink-mut" : "text-warning")}>{iv.status.toLowerCase()}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
