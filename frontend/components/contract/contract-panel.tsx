"use client";

import { Ban, CheckCircle2, FileSignature, ShieldAlert } from "lucide-react";
import { useContract } from "@/lib/hooks";
import type { ApprovalRequirement, Condition, EvidenceRequirement } from "@/lib/types";
import { ApprovalStatusBadge, EvidenceStatusBadge } from "@/components/forge/badges";
import { Badge, Chip, SectionLabel } from "@/components/forge/primitives";
import { ErrorState, LoadingState } from "@/components/forge/states";
import { ConditionRow } from "./condition-row";

const GRANT_LABEL: Record<string, string> = {
  begin_recovery_monitoring: "Begin recovery monitoring",
  release_quality_hold: "Release quality hold",
  disposition_affected_lots: "Disposition affected lots",
  release_contingency_work_order: "Release contingency work order",
  "reserve_bearing_BR-6205": "Reserve bearing BR-6205",
  assign_technician: "Assign technician",
  begin_second_recovery_window: "Begin second recovery window",
};

const DENY_LABEL: Record<string, string> = {
  machine_start: "Machine start",
  machine_stop: "Machine stop",
  machine_restart: "Machine restart",
  plc_modification: "PLC modification",
  setpoint_modification: "Set-point modification",
  alarm_bypass: "Alarm bypass",
  interlock_bypass: "Interlock bypass",
  loto_confirmation: "Lockout/tagout confirmation",
  safety_certification: "Safety certification",
  automatic_quality_release: "Automatic quality release",
};

export function ContractPanel({ incidentId }: { incidentId: string }) {
  const { data: c, isLoading, isError, refetch } = useContract(incidentId, 4000);
  if (isLoading) return <LoadingState label="Loading recovery contract" />;
  if (isError || !c) return <ErrorState message="Could not load the recovery contract." onRetry={() => refetch()} />;

  return (
    <div className="space-y-6">
      {/* objective */}
      <section className="rounded-xl border border-line bg-surface-1 p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileSignature className="h-4 w-4 text-agent" />
            <h2 className="text-lg font-semibold text-ink-hi">{c.contract_no} <span className="text-ink-mut">v{c.version}</span></h2>
            <Badge tone={c.status === "fulfilled" ? "verified" : c.status === "violated" ? "failure" : "agent"}>{c.status}</Badge>
          </div>
          <Chip>drafted by {c.drafted_by}</Chip>
        </div>
        <p className="mt-2 text-sm text-ink">{c.objective}</p>
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-ink-mut">
          <span><span className="label mr-1">Policy</span><span className="mono">{c.policy_version}</span></span>
          <span><span className="label mr-1">Workflow</span><span className="mono">{c.workflow_version}</span></span>
          <span><span className="label mr-1">Verdict</span><span className="mono">{c.evaluation.verdict}</span></span>
          <span><span className="label mr-1">Stable</span><span className="mono">{c.evaluation.stable_streak}/{c.evaluation.required_stable_cycles}</span></span>
        </div>
      </section>

      <ConditionGroup title="Machine recovery conditions" items={c.conditions.machine} />
      <ConditionGroup title="Production recovery conditions" items={c.conditions.production} />
      <ConditionGroup title="Quality recovery conditions" items={c.conditions.quality} />

      <section>
        <SectionLabel className="mb-2">Required human evidence</SectionLabel>
        <div className="space-y-2">
          {c.evidence_requirements.map((e) => <EvidenceReqRow key={e.id} e={e} />)}
        </div>
      </section>

      <section>
        <SectionLabel className="mb-2">Approval gates</SectionLabel>
        <div className="grid gap-3 sm:grid-cols-2">
          {c.approval_requirements.map((a) => <ApprovalScope key={a.id} a={a} />)}
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-3">
        <PolicyCard title="Verification window" body={`${c.evaluation.required_stable_cycles} consecutive stable cycles required. Nominal cycle ${(c.verification_window as any)?.cycle_seconds ?? 12.2}s.`} />
        <PolicyCard title="Closure policy" body={String((c.closure_policy as any)?.description ?? "")} />
        <PolicyCard title="Reopening policy" body={String((c.reopening_policy as any)?.description ?? "")} tone="failure" />
      </section>
      <section>
        <PolicyCard title="Escalation conditions" body={String((c.escalation_policy as any)?.description ?? "")} tone="warning" />
      </section>
    </div>
  );
}

function ConditionGroup({ title, items }: { title: string; items: Condition[] }) {
  if (!items.length) return null;
  return (
    <section>
      <SectionLabel className="mb-2">{title}</SectionLabel>
      <div className="space-y-2">
        {items.map((c) => <ConditionRow key={c.key} c={c} />)}
      </div>
    </section>
  );
}

function EvidenceReqRow({ e }: { e: EvidenceRequirement }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-line bg-surface-1 px-3 py-2">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm text-ink">{e.label}</span>
          <Chip>{e.assigned_role.replace("_", " ")}</Chip>
        </div>
        <p className="mt-0.5 text-[11px] text-ink-mut">{e.reason_required}</p>
      </div>
      <EvidenceStatusBadge status={e.status} />
    </div>
  );
}

function ApprovalScope({ a }: { a: ApprovalRequirement }) {
  return (
    <div className="rounded-lg border border-line bg-surface-1 p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-ink">
          <ShieldAlert className="h-4 w-4 text-approval" /> {a.label}
        </div>
        <ApprovalStatusBadge status={a.status} />
      </div>
      <div className="mt-2 text-[11px]">
        <div className="text-ink-mut">Approving authorises</div>
        <ul className="mt-1 space-y-0.5">
          {a.grants.map((g) => (
            <li key={g} className="flex items-center gap-1.5 text-verified"><CheckCircle2 className="h-3 w-3" /> {GRANT_LABEL[g] ?? g}</li>
          ))}
        </ul>
      </div>
      <div className="mt-2 border-t border-line pt-2 text-[11px]">
        <div className="text-ink-mut">It does NOT authorise</div>
        <ul className="mt-1 grid grid-cols-1 gap-0.5 sm:grid-cols-2">
          {a.denies.slice(0, 6).map((d) => (
            <li key={d} className="flex items-center gap-1.5 text-ink-faint"><Ban className="h-3 w-3 text-failure" /> {DENY_LABEL[d] ?? d}</li>
          ))}
        </ul>
      </div>
      <div className="mt-2 text-[10px] text-ink-faint">requires {a.required_role.replace("_", " ")} · <span className="mono">{a.policy_ref}</span></div>
    </div>
  );
}

function PolicyCard({ title, body, tone = "agent" }: { title: string; body: string; tone?: "agent" | "failure" | "warning" }) {
  const border = tone === "failure" ? "border-failure/30" : tone === "warning" ? "border-warning/30" : "border-line";
  return (
    <div className={`rounded-lg border ${border} bg-surface-1 p-3`}>
      <SectionLabel className="mb-1">{title}</SectionLabel>
      <p className="text-xs leading-relaxed text-ink-mut">{body}</p>
    </div>
  );
}
