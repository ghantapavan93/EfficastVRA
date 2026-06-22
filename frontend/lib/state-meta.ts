/** Visual metadata for workflow states, verdicts, and condition statuses. Tone maps to a Forge
 * color token; every badge also shows a label + icon + shape, so state never relies on color alone. */

export type Tone =
  | "agent"
  | "verified"
  | "pending"
  | "warning"
  | "failure"
  | "approval"
  | "evidence"
  | "steel"
  | "brand";

export interface Meta {
  label: string;
  tone: Tone;
}

export const STATE_META: Record<string, Meta> = {
  ALERT_TRIAGED: { label: "Triaging alert", tone: "agent" },
  INTERVENTION_PROPOSED: { label: "Diagnosis proposed", tone: "pending" },
  INTERVENTION_RECORDED: { label: "Intervention recorded", tone: "steel" },
  RECOVERY_CONTRACT_DRAFTED: { label: "Contract drafted", tone: "agent" },
  RECOVERY_CONTRACT_REVIEWED: { label: "Contract reviewed", tone: "agent" },
  AWAITING_REQUIRED_EVIDENCE: { label: "Awaiting evidence", tone: "pending" },
  READY_FOR_MONITORING: { label: "Ready to monitor", tone: "agent" },
  MONITORING_RECOVERY: { label: "Monitoring recovery", tone: "agent" },
  RECOVERY_CONDITION_PENDING: { label: "Condition pending", tone: "pending" },
  RECOVERY_CONDITION_FAILED: { label: "Condition failed", tone: "failure" },
  INSUFFICIENT_EVIDENCE: { label: "Insufficient evidence", tone: "warning" },
  RECOVERY_FAILED: { label: "Recovery failed", tone: "failure" },
  INCIDENT_REOPENED: { label: "Incident reopened", tone: "failure" },
  CONTINGENCY_AWAITING_APPROVAL: { label: "Contingency — approval", tone: "approval" },
  CONTINGENCY_IN_PROGRESS: { label: "Contingency in progress", tone: "agent" },
  VERIFIED_RECOVERY: { label: "Verified recovery", tone: "verified" },
  ESCALATED: { label: "Escalated", tone: "warning" },
  CANCELLED: { label: "Cancelled", tone: "steel" },
};

export const VERDICT_META: Record<string, Meta> = {
  monitoring: { label: "Monitoring", tone: "agent" },
  violated: { label: "Violated", tone: "failure" },
  verified: { label: "Verified", tone: "verified" },
  insufficient_evidence: { label: "Insufficient evidence", tone: "warning" },
};

export const CONDITION_META: Record<string, Meta> = {
  NOT_EVALUATED: { label: "Not evaluated", tone: "steel" },
  BLOCKED: { label: "Blocked", tone: "warning" },
  PENDING: { label: "Pending", tone: "pending" },
  PASSING: { label: "Passing", tone: "agent" },
  PASSED: { label: "Passed", tone: "verified" },
  VIOLATED: { label: "Violated", tone: "failure" },
};

export const EVIDENCE_META: Record<string, Meta> = {
  MISSING: { label: "Missing", tone: "steel" },
  REQUESTED: { label: "Requested", tone: "pending" },
  SUBMITTED: { label: "Submitted", tone: "agent" },
  VALIDATED: { label: "Validated", tone: "verified" },
  REJECTED: { label: "Rejected", tone: "failure" },
  CONFLICTING: { label: "Conflicting", tone: "failure" },
  EXPIRED: { label: "Expired", tone: "warning" },
};

export const APPROVAL_META: Record<string, Meta> = {
  PENDING: { label: "Pending", tone: "pending" },
  APPROVED: { label: "Approved", tone: "verified" },
  REJECTED: { label: "Rejected", tone: "failure" },
};

export const STATE_GROUP_LABEL: Record<string, string> = {
  requires_decision: "Requires decision",
  monitoring: "Monitoring recovery",
  awaiting_evidence: "Awaiting evidence",
  reopened: "Reopened",
  verified: "Verified",
  escalated: "Escalated",
};

export const SEVERITY_META: Record<string, Meta> = {
  S1: { label: "S1 · Critical", tone: "failure" },
  S2: { label: "S2 · High", tone: "warning" },
  S3: { label: "S3 · Medium", tone: "pending" },
  S4: { label: "S4 · Low", tone: "steel" },
};

/** Tailwind class fragments per tone for text / soft-bg / border / dot. */
export const TONE_CLASS: Record<Tone, { text: string; bg: string; border: string; dot: string }> = {
  agent: { text: "text-agent", bg: "bg-agent-soft", border: "border-agent/40", dot: "bg-agent" },
  verified: { text: "text-verified", bg: "bg-verified-soft", border: "border-verified/40", dot: "bg-verified" },
  pending: { text: "text-pending", bg: "bg-pending-soft", border: "border-pending/40", dot: "bg-pending" },
  warning: { text: "text-warning", bg: "bg-warning-soft", border: "border-warning/40", dot: "bg-warning" },
  failure: { text: "text-failure", bg: "bg-failure-soft", border: "border-failure/40", dot: "bg-failure" },
  approval: { text: "text-approval", bg: "bg-approval-soft", border: "border-approval/40", dot: "bg-approval" },
  evidence: { text: "text-evidence", bg: "bg-evidence-soft", border: "border-evidence/40", dot: "bg-evidence" },
  steel: { text: "text-ink-mut", bg: "bg-surface-2", border: "border-line", dot: "bg-steel" },
  brand: { text: "text-brand", bg: "bg-brand-soft", border: "border-brand/40", dot: "bg-brand" },
};
