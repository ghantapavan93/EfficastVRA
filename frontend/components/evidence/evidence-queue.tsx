"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { AlertTriangle, ArrowRight, Loader2, Upload } from "lucide-react";
import { useState } from "react";
import { useEvidence, useRecoveryActions } from "@/lib/hooks";
import { EVIDENCE_META } from "@/lib/state-meta";
import { ROLE_LABEL, useRole } from "@/lib/role";
import type { EvidenceRequirement, Role } from "@/lib/types";
import { cn } from "@/lib/utils";
import { EvidenceFreshnessBadge, EvidenceStatusBadge } from "@/components/forge/badges";
import { Badge, Button, Chip, SectionLabel } from "@/components/forge/primitives";
import { ErrorState, LoadingState } from "@/components/forge/states";

const GROUP_ORDER = ["MISSING", "REQUESTED", "REJECTED", "EXPIRED", "CONFLICTING", "SUBMITTED", "VALIDATED"];

export function EvidenceQueue({ incidentId }: { incidentId: string }) {
  const { data, isLoading, isError, refetch } = useEvidence(incidentId, 4000);
  if (isLoading) return <LoadingState label="Loading evidence queue" />;
  if (isError || !data) return <ErrorState message="Could not load the evidence queue." onRetry={() => refetch()} />;

  const groups = data.groups as Record<string, EvidenceRequirement[]>;
  const present = GROUP_ORDER.filter((g) => groups[g]?.length);

  if (present.length === 0)
    return <div className="rounded-lg border border-dashed border-line py-12 text-center text-sm text-ink-mut">No evidence requirements yet — draft the contract first.</div>;

  return (
    <div className="space-y-5">
      {present.map((g) => (
        <section key={g}>
          <div className="mb-2 flex items-center gap-2">
            <SectionLabel>{EVIDENCE_META[g]?.label ?? g}</SectionLabel>
            <span className="mono text-[11px] text-ink-faint">{groups[g].length}</span>
          </div>
          <div className="space-y-2">
            {groups[g].map((e) => <EvidenceRow key={e.id} e={e} incidentId={incidentId} />)}
          </div>
        </section>
      ))}
    </div>
  );
}

function EvidenceRow({ e, incidentId }: { e: EvidenceRequirement; incidentId: string }) {
  const { role } = useRole();
  const canSubmit = role === e.assigned_role && e.status !== "VALIDATED";
  const blocked = e.blocks_conditions?.length > 0;
  return (
    <div className="rounded-lg border border-line bg-surface-1 p-3">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-ink">{e.label}</span>
            <Chip>{ROLE_LABEL[e.assigned_role as Role]}</Chip>
            <EvidenceStatusBadge status={e.status} />
            {e.submitted && <EvidenceFreshnessBadge seconds={e.submitted.freshness_s} max={e.freshness_max_s} />}
          </div>
          <p className="mt-1 text-[11px] text-ink-mut">{e.reason_required}</p>
          {blocked && (
            <div className="mt-1.5 inline-flex items-center gap-1.5 text-[11px] text-pending">
              <ArrowRight className="h-3 w-3" /> blocks condition: <span className="mono">{e.blocks_conditions.join(", ")}</span>
            </div>
          )}
          {e.submitted && (
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-line bg-raised px-2.5 py-1.5 text-[11px]">
              <span className="text-ink-mut">submitted</span>
              <span className="mono text-ink">{e.submitted.value_num ?? e.submitted.value_text} {e.submitted.unit}</span>
              <span className="text-ink-faint">by {e.submitted.submitted_by}</span>
              {!e.submitted.valid && (
                <span className="inline-flex items-center gap-1 text-failure">
                  <AlertTriangle className="h-3 w-3" /> {e.submitted.conflict_reason || "invalid"}
                </span>
              )}
            </div>
          )}
        </div>
        <div className="shrink-0">
          {canSubmit ? (
            <SubmitDialog e={e} incidentId={incidentId} />
          ) : e.status === "VALIDATED" ? (
            <Badge tone="verified">✓ validated</Badge>
          ) : (
            <span className="text-[11px] text-ink-faint">needs {ROLE_LABEL[e.assigned_role as Role]}</span>
          )}
        </div>
      </div>
    </div>
  );
}

function SubmitDialog({ e, incidentId }: { e: EvidenceRequirement; incidentId: string }) {
  const [open, setOpen] = useState(false);
  const [num, setNum] = useState("");
  const [text, setText] = useState("");
  const { submitEvidence } = useRecoveryActions(incidentId);
  const numeric = e.kind === "NUMERIC_MEASUREMENT";
  const passFail = e.label.toLowerCase().includes("quality") || e.kind === "PHOTO";

  const submit = () => {
    const body = numeric
      ? { value_num: parseFloat(num), unit: "" }
      : passFail
        ? { value_text: text || "pass" }
        : { value_text: text || "completed" };
    submitEvidence.mutate({ reqId: e.id, body }, { onSuccess: () => setOpen(false) });
  };

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <Button size="sm" variant="agent"><Upload className="h-3.5 w-3.5" /> Submit</Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-[var(--scrim)] backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,440px)] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-line-strong bg-surface-2 p-5 shadow-e3 animate-fade-up">
          <Dialog.Title className="text-base font-semibold text-ink-hi">Submit evidence</Dialog.Title>
          <Dialog.Description className="mt-1 text-sm text-ink-mut">{e.label}</Dialog.Description>
          <div className="mt-4">
            {numeric ? (
              <label className="block">
                <span className="label">Measurement</span>
                <input
                  type="number"
                  step="0.1"
                  autoFocus
                  value={num}
                  onChange={(ev) => setNum(ev.target.value)}
                  placeholder="e.g. 3.6"
                  className="mono mt-1 h-11 w-full rounded-lg border border-line bg-surface-1 px-3 text-ink-hi outline-none focus:border-agent"
                />
              </label>
            ) : passFail ? (
              <div className="flex gap-2">
                {["pass", "fail"].map((v) => (
                  <button
                    key={v}
                    onClick={() => setText(v)}
                    className={cn("h-11 flex-1 rounded-lg border text-sm font-medium capitalize", text === v ? (v === "pass" ? "border-verified bg-verified-soft text-verified" : "border-failure bg-failure-soft text-failure") : "border-line text-ink-mut")}
                  >
                    {v}
                  </button>
                ))}
              </div>
            ) : (
              <label className="block">
                <span className="label">Note</span>
                <input
                  autoFocus
                  value={text}
                  onChange={(ev) => setText(ev.target.value)}
                  placeholder="completed"
                  className="mt-1 h-11 w-full rounded-lg border border-line bg-surface-1 px-3 text-ink outline-none focus:border-agent"
                />
              </label>
            )}
          </div>
          {submitEvidence.isError && (
            <p className="mt-2 text-xs text-failure">{(submitEvidence.error as Error)?.message}</p>
          )}
          <div className="mt-5 flex justify-end gap-2">
            <Dialog.Close asChild><Button size="sm" variant="ghost">Cancel</Button></Dialog.Close>
            <Button size="sm" variant="primary" onClick={submit} disabled={submitEvidence.isPending || (numeric && !num)}>
              {submitEvidence.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Submit evidence"}
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
