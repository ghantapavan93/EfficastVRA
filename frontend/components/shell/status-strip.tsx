"use client";

import Link from "next/link";
import { useMissions } from "@/lib/hooks";
import { AgentActivityIndicator } from "@/components/forge/badges";
import { ProgressBar } from "@/components/forge/primitives";

const ACTIVITY: Record<string, string> = {
  MONITORING_RECOVERY: "Monitoring recovery cycles",
  CONTINGENCY_IN_PROGRESS: "Tracking contingency work",
  CONTINGENCY_AWAITING_APPROVAL: "Awaiting contingency approval",
  AWAITING_REQUIRED_EVIDENCE: "Validating evidence",
  RECOVERY_CONTRACT_DRAFTED: "Comparing recovery requirements",
};

export function StatusStrip() {
  const { data } = useMissions(2500);
  const mission = data?.missions.find(
    (m) => m.state in ACTIVITY || m.state === "MONITORING_RECOVERY",
  );
  if (!mission) return null;

  return (
    <div className="flex h-9 shrink-0 items-center gap-4 border-t border-line bg-raised px-4 text-xs">
      <AgentActivityIndicator label={ACTIVITY[mission.state] ?? "Working"} />
      <Link href={`/missions/${mission.id}`} className="mono text-ink-mut hover:text-ink">
        {mission.id}
      </Link>
      <span className="text-ink-faint">·</span>
      <span className="text-ink-mut">{mission.next_action}</span>
      <div className="ml-auto flex w-48 items-center gap-2">
        <span className="text-ink-faint">confidence</span>
        <ProgressBar value={mission.outcome_confidence} tone={mission.outcome_confidence >= 100 ? "verified" : "agent"} />
        <span className="mono text-ink-mut">{mission.outcome_confidence}%</span>
      </div>
    </div>
  );
}
