"use client";

import { Suspense } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useMission } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { StateBadge } from "@/components/forge/badges";
import { Badge, Chip } from "@/components/forge/primitives";
import { ErrorState, LoadingState } from "@/components/forge/states";
import { ActionBar } from "@/components/mission/action-bar";
import { AgentReasoning } from "@/components/mission/agent-reasoning";
import { DecisionPanel } from "@/components/mission/decision-panel";
import { ReliabilityPanel } from "@/components/mission/reliability-panel";
import { RecoverySignaturePanel } from "@/components/mission/recovery-signature-panel";
import { ClosureRiskPanel } from "@/components/mission/closure-risk-panel";
import { DispositionPanel } from "@/components/mission/disposition-panel";
import { OeeRestorationPanel } from "@/components/mission/oee-restoration-panel";
import { DecisionRoom } from "@/components/mission/decision-room";
import { MissionSpine } from "@/components/mission/mission-spine";
import { UploadedVerification } from "@/components/mission/uploaded-verification";
import { RecoveryTwin } from "@/components/mission/recovery-twin";
import { MissionQA } from "@/components/mission/mission-qa";
import { EvidencePlanner } from "@/components/mission/evidence-planner";
import { RecoveryDebtPanel } from "@/components/mission/recovery-debt-panel";
import { SensorTrustPanel } from "@/components/mission/sensor-trust-panel";
import { LotAtRiskPanel } from "@/components/mission/lot-at-risk-panel";
import { StakeholderPanel } from "@/components/mission/stakeholder-panel";
import { CommandCenter } from "@/components/mission/command-center";
import { ComparableConditionsPanel } from "@/components/mission/comparable-conditions-panel";
import { ProvenancePanel } from "@/components/mission/provenance-panel";
import { DiagnosisPanel } from "@/components/mission/diagnosis-panel";
import { ContingencyCompare } from "@/components/mission/contingency-compare";
import { MissionHeader } from "@/components/mission/mission-header";
import { ContractPanel } from "@/components/contract/contract-panel";
import { EvidenceQueue } from "@/components/evidence/evidence-queue";
import { OutcomePanel } from "@/components/outcome/outcome-panel";
import { RecoveryCertificate } from "@/components/outcome/recovery-certificate";
import { VerificationTimeline } from "@/components/timeline/verification-timeline";

export default function Page({ params }: { params: { id: string } }) {
  return (
    <Suspense fallback={<LoadingState />}>
      <MissionDetail id={params.id} />
    </Suspense>
  );
}

function MissionDetail({ id }: { id: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();
  const tab = sp.get("tab") ?? "overview";
  const { data: m, isLoading, isError, refetch } = useMission(id, 3000);

  const setTab = (t: string) => router.replace(`${pathname}?tab=${t}`, { scroll: false });

  if (isLoading) return <LoadingState label="Loading mission" />;
  if (isError || !m) return <div className="p-6"><ErrorState message="Mission not found or backend unreachable." onRetry={() => refetch()} /></div>;

  const tabs = [
    { key: "overview", label: "Overview" },
    { key: "ask", label: "Ask the agent" },
    ...(m.origin_alert_id ? [{ key: "diagnosis", label: "Agent Diagnosis" }] : []),
    { key: "reasoning", label: "Agent Reasoning" },
    { key: "decision", label: "Decision Intelligence" },
    { key: "reliability", label: "Recovery Confidence" },
    { key: "signature", label: "Recovery Signature" },
    { key: "twin", label: "Recovery Twin" },
    { key: "comparability", label: "Comparable Conditions" },
    { key: "closure-risk", label: "Closure Risk" },
    { key: "disposition", label: "Disposition" },
    { key: "decision-room", label: "Decision Room" },
    { key: "evidence-planner", label: "Evidence Planner" },
    { key: "oee", label: "OEE Restoration" },
    { key: "recovery-debt", label: "Recovery Debt" },
    { key: "sensor-trust", label: "Sensor Trust" },
    { key: "lot-at-risk", label: "Lot-at-Risk" },
    { key: "contract", label: "Recovery Contract" },
    { key: "evidence", label: "Evidence" },
    { key: "timeline", label: "Verification Timeline" },
    ...(m.reopened_count > 0 ? [{ key: "contingency", label: "Contingency" }] : []),
    { key: "provenance", label: "Provenance" },
    { key: "outcome", label: "Outcome" },
    { key: "certificate", label: "Certificate" },
    { key: "stakeholder", label: "Your View" },
  ];

  return (
    <div>
      <MissionHeader m={m} />

      {/* sticky action + tab bar */}
      <div className="sticky top-0 z-20 border-b border-line bg-canvas/85 backdrop-blur">
        <div className="mx-auto max-w-6xl px-6 py-3">
          <ActionBar m={m} />
        </div>
        <div className="mx-auto max-w-6xl overflow-x-auto px-6">
          <nav className="flex gap-1" role="tablist" aria-label="Mission views">
            {tabs.map((t) => (
              <button
                key={t.key}
                role="tab"
                aria-selected={tab === t.key}
                onClick={() => setTab(t.key)}
                className={cn(
                  "relative whitespace-nowrap px-3 py-2.5 text-sm transition-colors",
                  tab === t.key ? "text-ink-hi" : "text-ink-mut hover:text-ink",
                )}
              >
                {t.label}
                {tab === t.key && <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-pill bg-agent" />}
              </button>
            ))}
          </nav>
        </div>
      </div>

      <div className="mx-auto max-w-6xl space-y-5 px-6 pt-6">
        <UploadedVerification id={id} m={m} onDone={() => refetch()} />
        <MissionSpine incidentId={id} />
      </div>

      <div key={tab} className="tab-in mx-auto max-w-6xl px-6 py-6">
        {tab === "overview" && <Overview m={m} />}
        {tab === "ask" && <MissionQA incidentId={id} />}
        {tab === "diagnosis" && <DiagnosisPanel incidentId={id} />}
        {tab === "reasoning" && <AgentReasoning incidentId={id} />}
        {tab === "decision" && <DecisionPanel incidentId={id} />}
        {tab === "reliability" && <ReliabilityPanel incidentId={id} />}
        {tab === "signature" && <RecoverySignaturePanel incidentId={id} />}
        {tab === "twin" && <RecoveryTwin incidentId={id} />}
        {tab === "comparability" && <ComparableConditionsPanel incidentId={id} />}
        {tab === "closure-risk" && <ClosureRiskPanel incidentId={id} />}
        {tab === "disposition" && <DispositionPanel incidentId={id} />}
        {tab === "decision-room" && <DecisionRoom incidentId={id} />}
        {tab === "evidence-planner" && <EvidencePlanner incidentId={id} />}
        {tab === "oee" && <OeeRestorationPanel incidentId={id} />}
        {tab === "recovery-debt" && <RecoveryDebtPanel incidentId={id} />}
        {tab === "sensor-trust" && <SensorTrustPanel incidentId={id} />}
        {tab === "lot-at-risk" && <LotAtRiskPanel incidentId={id} />}
        {tab === "stakeholder" && <StakeholderPanel incidentId={id} />}
        {tab === "contract" && <ContractPanel incidentId={id} />}
        {tab === "evidence" && <EvidenceQueue incidentId={id} />}
        {tab === "timeline" && <VerificationTimeline incidentId={id} />}
        {tab === "contingency" && <ContingencyCompare incidentId={id} />}
        {tab === "provenance" && <ProvenancePanel incidentId={id} />}
        {tab === "outcome" && <OutcomePanel incidentId={id} />}
        {tab === "certificate" && <RecoveryCertificate incidentId={id} />}
      </div>
    </div>
  );
}

function Overview({ m }: { m: import("@/lib/types").MissionDetail }) {
  const b = m.worker_brief;
  return (
    <div className="space-y-5">
      <CommandCenter m={m} />
      {b && (
        <section className="rounded-xl border border-line bg-surface-1 p-5">
          <div className="label mb-1">In plain words</div>
          <h2 className="text-lg font-semibold text-ink-hi">{b.headline}</h2>
          {b.what_happened && <p className="mt-1.5 text-sm text-ink">{b.what_happened}</p>}
          <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
            <span>
              <span className="label mr-2">Do now</span>
              <span className="text-ink">{b.what_to_do_now}</span>
            </span>
            <span>
              <span className="label mr-2">Owner</span>
              <span className="mono text-ink">{b.who}</span>
            </span>
          </div>
        </section>
      )}
      <div className="grid gap-5 lg:grid-cols-3">
      <section className="lg:col-span-2 space-y-3">
        <div className="label">Interventions being verified</div>
        {m.interventions.map((i) => (
          <div key={i.id} className="rounded-lg border border-line bg-surface-1 p-3">
            <div className="flex items-center gap-2">
              <span className="grid h-6 w-6 place-items-center rounded-md bg-surface-3 text-[11px] mono text-ink-mut">{i.sequence}</span>
              <span className="text-sm font-medium text-ink">{i.title}</span>
              <Chip>{i.status.toLowerCase()}</Chip>
            </div>
            <p className="mt-1.5 pl-8 text-xs text-ink-mut">{i.hypothesis}</p>
          </div>
        ))}
      </section>
      <aside className="space-y-3">
        <div className="rounded-lg border border-line bg-surface-1 p-4">
          <div className="label mb-2">Recovery snapshot</div>
          <Row label="State"><StateBadge state={m.state} /></Row>
          <Row label="Next"><span className="text-ink">{m.next_action}</span></Row>
          <Row label="Missing evidence"><span className="mono text-ink">{m.missing_evidence}</span></Row>
          <Row label="Reopened"><span className="mono text-ink">×{m.reopened_count}</span></Row>
          <Row label="Progress">
            {m.recovery_progress >= 100 ? <Badge tone="verified">100%</Badge> : <span className="mono text-ink">{m.recovery_progress}%</span>}
          </Row>
        </div>
      </aside>
      </div>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-t border-line py-1.5 first:border-t-0 text-xs">
      <span className="text-ink-mut">{label}</span>
      {children}
    </div>
  );
}
