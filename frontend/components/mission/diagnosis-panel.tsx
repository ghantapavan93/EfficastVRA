"use client";

import { AlertTriangle, ArrowRight, BookOpen, Radar, ShieldAlert } from "lucide-react";
import { useDiagnosis, useMe, useRecoveryActions } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Badge, Button, Chip } from "@/components/forge/primitives";
import { AgentActivityIndicator } from "@/components/forge/badges";
import { EmptyState, ErrorState, LoadingState } from "@/components/forge/states";
import type { DiagnosisRootCause, DiagnosisView } from "@/lib/types";

export function DiagnosisPanel({ incidentId }: { incidentId: string }) {
  const { data, isLoading, isError, refetch } = useDiagnosis(incidentId, 4000);
  const { data: me } = useMe();
  const actions = useRecoveryActions(incidentId);

  if (isLoading) return <LoadingState label="Loading agent diagnosis" />;
  if (isError || !data) return <ErrorState message="Diagnosis unavailable." onRetry={() => refetch()} />;
  if (!data.available)
    return (
      <EmptyState
        title="No agent diagnosis"
        description="This incident did not originate from a MAIA alert. Diagnosis is recorded when the agent triages an inbound alert."
      />
    );

  const canAccept = me?.role === "supervisor" || me?.role === "plant_admin";
  const pending = !data.accepted && data.state === "INTERVENTION_PROPOSED";

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-surface-1 p-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-ink-hi">Agent diagnosis</h2>
            <AgentActivityIndicator label={pending ? "awaiting acceptance" : "diagnosis recorded"} active={pending} />
          </div>
          <p className="mt-1 text-xs text-ink-mut">
            The agent triaged an inbound MAIA alert, ranked the likely causes, and proposed an
            intervention. A human accepts before any work is recorded.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {data.origin_alert_id && <Chip>origin {data.origin_alert_id}</Chip>}
          {data.degradation_kind && <Chip>{data.degradation_kind.replace(/_/g, " ")}</Chip>}
          {typeof data.diagnostic_confidence === "number" && (
            <Badge tone="agent">diagnostic confidence {Math.round(data.diagnostic_confidence * 100)}%</Badge>
          )}
        </div>
      </header>

      {data.alert && (
        <section className="rounded-lg border border-line bg-surface-1 p-4">
          <div className="label mb-2 flex items-center gap-1.5">
            <Radar className="h-3.5 w-3.5 text-evidence" aria-hidden /> Inbound MAIA alert
          </div>
          <p className="text-sm text-ink">{data.alert.message}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {Object.entries(data.alert.signals).map(([k, v]) => (
              <Chip key={k}>
                {k.replace(/_/g, " ")}: {String(v)}
              </Chip>
            ))}
          </div>
        </section>
      )}

      <section className="rounded-lg border border-line bg-surface-1 p-4">
        <div className="label mb-2">Ranked root causes</div>
        <ol className="space-y-2">
          {data.root_causes.map((rc: DiagnosisRootCause, i) => (
            <li key={i} className="flex items-start gap-3 rounded-md border border-line bg-surface-2 p-2.5">
              <span
                className={cn(
                  "mt-0.5 grid h-5 min-w-5 place-items-center rounded-md px-1 text-[10px] font-semibold uppercase",
                  rc.likelihood === "primary" ? "bg-warning-soft text-warning" : "bg-surface-3 text-ink-mut",
                )}
              >
                {rc.likelihood}
              </span>
              <div className="min-w-0">
                <div className="text-sm text-ink">{rc.cause}</div>
                {rc.basis && <div className="mt-0.5 text-xs text-ink-mut">{rc.basis}</div>}
              </div>
            </li>
          ))}
        </ol>
      </section>

      {data.recommended_intervention && (
        <section className="rounded-lg border border-line bg-surface-1 p-4">
          <div className="label mb-2 flex items-center gap-1.5">
            <ArrowRight className="h-3.5 w-3.5 text-agent" aria-hidden /> Proposed intervention
          </div>
          <div className="text-sm font-medium text-ink">{data.recommended_intervention.title}</div>
          <p className="mt-1 text-xs leading-relaxed text-ink-mut">{data.recommended_intervention.description}</p>
          {data.contingency && (
            <p className="mt-2 flex items-start gap-1.5 rounded-md border border-line bg-surface-2 p-2 text-xs text-ink-mut">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" aria-hidden />
              Contingency: {data.contingency.note}
            </p>
          )}
          {data.citations.length > 0 && (
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              <BookOpen className="h-3.5 w-3.5 text-ink-mut" aria-hidden />
              {data.citations.map((c, i) => (
                <Chip key={i}>
                  {c.document_id}
                  {c.section ? ` § ${c.section}` : ""}
                </Chip>
              ))}
            </div>
          )}
        </section>
      )}

      {pending ? (
        <AcceptPanel data={data} canAccept={canAccept} actions={actions} />
      ) : (
        data.accepted && (
          <p className="rounded-lg border border-verified/40 bg-verified-soft px-3 py-2 text-xs text-verified">
            Diagnosis accepted — intervention recorded. Recovery verification has taken over.
          </p>
        )
      )}
    </div>
  );
}

function AcceptPanel({
  data,
  canAccept,
  actions,
}: {
  data: DiagnosisView;
  canAccept: boolean;
  actions: ReturnType<typeof useRecoveryActions>;
}) {
  return (
    <section className="rounded-lg border border-approval/40 bg-surface-1 p-4">
      <div className="flex items-center gap-1.5 text-sm font-semibold text-ink-hi">
        <ShieldAlert className="h-4 w-4 text-approval" aria-hidden /> Accept diagnosis
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div className="rounded-md border border-line bg-surface-2 p-3">
          <div className="label mb-1 text-verified">You are accepting</div>
          <ul className="space-y-1 text-xs text-ink">
            <li>Record the proposed {data.recommended_intervention?.title.toLowerCase()}</li>
            <li>Dispatch a technician to perform the physical work</li>
            <li>Begin recovery verification once complete</li>
          </ul>
        </div>
        <div className="rounded-md border border-line bg-surface-2 p-3">
          <div className="label mb-1 text-failure">You are not authorizing</div>
          <ul className="space-y-1 text-xs text-ink-mut">
            <li>Any machine start / stop / restart</li>
            <li>PLC or set-point modification</li>
            <li>Automatic quality release or closure</li>
          </ul>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between gap-3">
        <p className="text-xs text-ink-mut">
          {canAccept
            ? "Accepting records the intervention; the agent never accepts its own diagnosis."
            : "Only a supervisor or plant admin may accept the diagnosis."}
        </p>
        <Button
          variant="approval"
          disabled={!canAccept || actions.acceptDiagnosis.isPending}
          onClick={() => actions.acceptDiagnosis.mutate()}
        >
          {actions.acceptDiagnosis.isPending ? "Recording…" : "Accept & record intervention"}
        </Button>
      </div>
    </section>
  );
}
