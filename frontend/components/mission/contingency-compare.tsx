"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, GitBranch } from "lucide-react";
import { api } from "@/lib/api";
import { useRole } from "@/lib/role";
import type { ContractView } from "@/lib/types";
import { Badge, Chip, SectionLabel } from "@/components/forge/primitives";
import { EmptyState, LoadingState } from "@/components/forge/states";

export function ContingencyCompare({ incidentId }: { incidentId: string }) {
  const { username } = useRole();
  const { data, isLoading } = useQuery({
    queryKey: ["contract-versions", incidentId, username],
    queryFn: () => api.contractVersions(incidentId),
  });
  if (isLoading) return <LoadingState label="Loading contract versions" />;
  const versions = data?.versions ?? [];
  if (versions.length < 2)
    return <EmptyState title="No contingency yet" description="The contingency comparison appears after the first recovery fails and a second contract is drafted." icon={GitBranch} />;

  const [v1, v2] = versions;
  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-failure/30 bg-failure-soft p-4">
        <SectionLabel className="mb-1 text-failure">Why the first intervention failed</SectionLabel>
        <p className="text-sm text-ink">
          The coupling-alignment correction was completed and early cycles looked like recovery, but fault
          <span className="mono text-failure"> F27</span> recurred at <span className="mono">cycle 17</span> of the verification
          window. A completed work order is not proof of recovery — bearing degradation, not misalignment, was the root cause.
        </p>
      </section>

      <div className="grid gap-3 md:grid-cols-2">
        <VersionCard c={v1} role="superseded" />
        <VersionCard c={v2} role="active" />
      </div>

      <section className="rounded-xl border border-line bg-surface-1 p-4">
        <SectionLabel className="mb-2">What changed</SectionLabel>
        <ul className="space-y-1.5 text-sm text-ink-mut">
          <Change label="Intervention" before="Coupling-alignment correction" after="Drive-end bearing replacement (BR-6205)" />
          <Change label="Hypothesis" before="Coupling misalignment from motor replacement" after="Drive-end bearing degradation" />
          <Change label="New approval" before="—" after="Release contingency (reserve bearing · assign technician)" />
          <Change label="Conditions" before="6 recovery conditions" after="Retained — 30 stable cycles still required" />
        </ul>
      </section>
    </div>
  );
}

function VersionCard({ c, role }: { c: ContractView; role: "superseded" | "active" }) {
  return (
    <div className={`rounded-xl border p-4 ${role === "active" ? "border-agent/40 bg-surface-1" : "border-line bg-surface-1 opacity-90"}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="mono text-sm text-ink-hi">{c.contract_no}-V{c.version}</span>
          <Badge tone={role === "active" ? "agent" : "steel"}>{role === "active" ? "active" : "superseded"}</Badge>
        </div>
        <Chip>{c.status}</Chip>
      </div>
      <p className="mt-2 text-xs leading-relaxed text-ink-mut">{c.objective}</p>
      <div className="mt-2 text-[11px] text-ink-faint">
        {c.conditions.machine.length + c.conditions.production.length + c.conditions.quality.length} conditions ·{" "}
        {c.evidence_requirements.length} evidence · {c.approval_requirements.length} approvals
      </div>
    </div>
  );
}

function Change({ label, before, after }: { label: string; before: string; after: string }) {
  return (
    <li className="flex flex-wrap items-center gap-2">
      <span className="label w-24 shrink-0">{label}</span>
      <span className="text-ink-faint line-through">{before}</span>
      <ArrowRight className="h-3 w-3 text-ink-faint" />
      <span className="text-ink">{after}</span>
    </li>
  );
}
