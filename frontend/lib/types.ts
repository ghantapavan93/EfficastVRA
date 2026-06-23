/** Types aligned with backend serializers (app/api/serializers.py). Business rules live in the
 * backend; these only shape what the UI renders. */

export type Role = "supervisor" | "technician" | "quality_engineer" | "plant_admin";

export interface Me {
  user_id: string;
  username: string;
  role: Role;
  plant_id: string;
  tenant_id: string;
  environment: string;
  demo_mode: boolean;
}

export type StateGroup =
  | "requires_decision"
  | "monitoring"
  | "awaiting_evidence"
  | "reopened"
  | "verified"
  | "escalated";

export interface MissionSummary {
  id: string;
  title: string;
  objective: string;
  machine: { id: string; code: string; name: string } | null;
  order: { id: string; product: string; qty_remaining: number } | null;
  state: string;
  state_group: StateGroup;
  stage: string;
  severity: string;
  next_action: string;
  owner: string;
  missing_evidence: number;
  reopened_count: number;
  fault_code: string | null;
  origin_alert_id: string | null;
  contract_no: string | null;
  contract_version: number | null;
  outcome_confidence: number;
  opened_at: string | null;
  updated_at: string | null;
  is_active: boolean;
}

export interface RailStage {
  stage: string;
  status: "complete" | "active" | "upcoming" | "blocked" | "failed" | "reopened";
}

export interface MissionDetail extends MissionSummary {
  interventions: {
    id: string;
    sequence: number;
    kind: string;
    title: string;
    status: string;
    hypothesis: string;
    completed_at: string | null;
  }[];
  progress_rail: RailStage[];
  worker_brief: { headline: string; what_happened: string; what_to_do_now: string; who: string };
  agent_responsibility: string;
  human_responsibility: string;
  environment: string;
}

export type ConditionStatus =
  | "NOT_EVALUATED"
  | "BLOCKED"
  | "PENDING"
  | "PASSING"
  | "PASSED"
  | "VIOLATED";

export interface Condition {
  key: string;
  label: string;
  op: string;
  threshold: number | null;
  unit: string;
  baseline: number | null;
  current_value: number | null;
  status: ConditionStatus;
  sensor_tag: string | null;
  fault_code: string | null;
  deadline_kind: string;
  deadline_value: number | null;
  policy_ref: string;
  rationale: string;
}

export interface Evaluation {
  verdict: "monitoring" | "violated" | "verified" | "insufficient_evidence";
  summary: string;
  observed_cycles: number;
  stable_streak: number;
  required_stable_cycles: number;
  technical_pass: boolean;
  awaiting_quality: boolean;
  violated_keys: string[];
  blocked_keys: string[];
}

export interface EvidenceRequirement {
  id: string;
  key: string;
  label: string;
  kind: string;
  assigned_role: Role;
  reason_required: string;
  required_before: string;
  freshness_max_s: number | null;
  status: string;
  blocks_conditions: string[];
  due_at: string | null;
  submitted: {
    id: string;
    value_num: number | null;
    value_text: string;
    unit: string;
    source: string;
    submitted_by: string;
    submitted_role: Role;
    valid: boolean;
    status: string;
    freshness_s: number | null;
    conflict_reason: string;
    at: string | null;
  } | null;
}

export interface ApprovalRequirement {
  id: string;
  key: string;
  label: string;
  required_role: Role;
  required_before: string;
  grants: string[];
  denies: string[];
  status: "PENDING" | "APPROVED" | "REJECTED";
  policy_ref: string;
  decision: {
    decided_by: string;
    decided_role: Role;
    decision: string;
    reason: string;
    at: string | null;
  } | null;
}

export interface ContractView {
  id: string;
  contract_no: string;
  version: number;
  status: string;
  objective: string;
  drafted_by: string;
  policy_version: string;
  workflow_version: string;
  incident_id: string;
  superseded_by: string | null;
  conditions: { machine: Condition[]; production: Condition[]; quality: Condition[] };
  evaluation: Evaluation;
  verification_window: Record<string, unknown>;
  closure_policy: Record<string, unknown>;
  reopening_policy: Record<string, unknown>;
  escalation_policy: Record<string, unknown>;
  evidence_requirements: EvidenceRequirement[];
  approval_requirements: ApprovalRequirement[];
}

export interface TimelineCycle {
  kind: "cycle";
  cycle_index: number;
  window: string;
  at: string | null;
  vibration: number | null;
  temperature: number | null;
  cycle_time: number | null;
  scrap_pct: number | null;
  fault_code: string | null;
  source: string;
  freshness_s: number;
  is_recurrence: boolean;
}

export interface TimelineAudit {
  kind: "audit";
  seq: number;
  type: string;
  summary: string;
  actor: string;
  role: string | null;
  at: string | null;
  prev_state: string | null;
  new_state: string | null;
  detail: Record<string, unknown>;
}

export interface TimelineView {
  events: TimelineAudit[];
  cycles: TimelineCycle[];
}

export interface KnowledgeCandidate {
  id: string;
  title: string;
  lesson: string;
  component: string;
  applicable_models: string[];
  conditions: Record<string, unknown>;
  supporting_evidence: string[];
  failed_intervention: string;
  successful_intervention: string;
  status: string;
  reviewer_role: Role;
  review_due: string | null;
  pending_review: boolean;
  incident_id?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  review_reason?: string;
}

export interface KnowledgeList {
  knowledge: KnowledgeCandidate[];
  pending: number;
  approved: number;
}

export interface OutcomeView {
  incident_id: string;
  state: string;
  outcome_type: string | null;
  summary: string;
  before: Record<string, number | string>;
  after: Record<string, number | string>;
  stable_cycles: number;
  required_stable_cycles: number;
  reopened_count: number;
  interventions: { sequence: number; kind: string; title: string; status: string; failed: boolean }[];
  lots: { id: string; qty: number; disposition: string }[];
  quality_released: boolean;
  policy_version: string | null;
  knowledge_candidate: KnowledgeCandidate | null;
  closed_at: string | null;
}

export interface AuditEvent {
  seq: number;
  type: string;
  summary: string;
  actor: string;
  role: string | null;
  at: string | null;
  policy_version: string;
  workflow_version: string;
  model_version: string;
  prev_state: string | null;
  new_state: string | null;
  detail: Record<string, unknown>;
}

export type ReasoningNode =
  | "perceive"
  | "retrieve"
  | "hypothesize"
  | "draft"
  | "self_critique"
  | "decide"
  | "observe"
  | "reflect";

export interface ReasoningCitation {
  document_id?: string;
  section?: string;
  revision?: string;
  approval_status?: string;
  excerpt?: string;
}

export interface ReasoningStep {
  seq: number;
  node: ReasoningNode;
  node_label: string;
  title: string;
  rationale: string;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  citations: ReasoningCitation[];
  confidence: number | null;
  revision: number;
  contract_id: string | null;
  model_version: string;
  prompt_version: string;
  at: string | null;
}

export interface ReasoningView {
  incident_id: string;
  provider: string | null;
  prompt_version: string | null;
  confidence: number | null;
  step_count: number;
  steps: ReasoningStep[];
  note: string;
}

export interface AppNotification {
  id: string;
  incident_id: string | null;
  to_role: Role;
  channel: string;
  kind: string;
  title: string;
  body: string;
  status: "unread" | "read";
  action_path: string;
  at: string | null;
}

export interface NotificationsView {
  notifications: AppNotification[];
  unread: number;
  role: Role;
}

export interface AuditIntegrity {
  ok: boolean;
  broken_at_seq: number | null;
  count: number;
}

export interface DecisionOption {
  action: string;
  label: string;
  expected_cost_usd: number;
  rationale: string;
  recommended?: boolean;
}

export interface FmeaRow {
  failure_mode: string;
  effect: string;
  severity: number;
  occurrence: number;
  detection: number;
  detection_without_agent: number;
  rpn: number;
  rpn_without_agent: number;
}

export interface DecisionView {
  available: boolean;
  incident_id: string;
  p_relapse: number;
  forecast_state: string;
  impact: {
    order_id: string | null;
    units_remaining: number;
    throughput_per_hour: number;
    hours_to_complete: number;
    false_closure_exposure_usd: number;
    assumptions: { downtime_cost_per_hour: number; scrap_cost_per_unit: number; contingency_prep_cost: number };
  };
  options: DecisionOption[];
  recommendation: { action: string; label: string; headline: string; why: string };
  fmea: FmeaRow[];
  fmea_note: string;
  summary: string;
  advisory: string;
}

export interface ReliabilityView {
  available: boolean;
  incident_id: string;
  reason?: string;
  stable_cycles?: number;
  observed_cycles?: number;
  required_stable_cycles?: number;
  target_relapse_rate?: number;
  confidence_level?: number;
  confidence_now?: number;
  confidence_at_window?: number;
  demonstrated_relapse_ceiling?: number;
  cycles_for_target?: number;
  window_grade?: string;
  sprt?: {
    decision: "accept" | "reject" | "continue";
    decided_at_cycle: number | null;
    n: number;
    llr: number;
    accept_bound: number;
    reject_bound: number;
    clean_cycles_to_accept: number | null;
    p0: number;
    p1: number;
    alpha: number;
    beta: number;
  };
  sprt_summary?: string;
  hazard?: {
    relapse_cycles_observed: number[];
    mean_cycles_to_relapse: number | null;
    sample_size: number;
    pattern: string;
    weibull_shape_hint: string | null;
    interpretation: string;
    data_confidence: string;
    data_note: string;
  };
  verdict_confidence?: string;
  headline?: string;
  recommendation?: string;
  advisory: string;
}

export interface TroubleshootResult {
  query: { fault_code: string | null; machine_model: string | null; text: string };
  machine: { model?: string; equipment_class?: string; label?: string } | null;
  summary: string;
  likely_causes: { cause: string; likelihood: string; basis?: string }[];
  approved_procedures: { document_id?: string; section?: string; revision?: string; approval_status?: string; excerpt?: string }[];
  history: { incident_id: string; fault_code: string | null; outcome: string | null; summary: string }[];
  what_worked: string;
  signals_to_check: { key: string; label: string; op: string; threshold: number | null; unit: string }[];
  early_warning: string;
  knowledge: { title: string; lesson: string; status: string; pending_review: boolean; failed_intervention?: string; successful_intervention?: string }[];
  cautions: { document_id?: string; reason?: string; approval_status?: string; revision?: string; excerpt?: string }[];
}

export interface ForecastHypothesis {
  id: string;
  label: string;
  support: number;
  evidence?: string;
}

export interface ForecastView {
  available: boolean;
  incident_id: string;
  observed_cycles?: number;
  p_recovery_holds?: number;
  p_relapse?: number;
  predicted_relapse_cycle?: number | null;
  fault_cycle?: number | null;
  lead_cycles?: number | null;
  divergence?: number;
  leading_indicator?: string;
  hypotheses?: ForecastHypothesis[];
  series?: { cycle: number; p_relapse: number }[];
  headline?: string;
}

export interface MaiaAlert {
  id: string;
  source: string;
  kind: string;
  machine_id: string;
  order_id: string | null;
  fault_code: string | null;
  severity: string;
  message: string;
  signals: Record<string, number | string>;
  detected_at: string | null;
  status: string;
  resulted_in_incident: string | null;
}

export interface DiagnosisRootCause {
  cause: string;
  likelihood: string;
  basis?: string;
}

export interface DiagnosisView {
  available: boolean;
  incident_id: string;
  origin_alert_id: string | null;
  alert?: MaiaAlert | null;
  degradation_kind?: string | null;
  root_causes: DiagnosisRootCause[];
  recommended_intervention?: {
    kind: string;
    title: string;
    description: string;
    component_id?: string | null;
    hypothesis?: string;
  } | null;
  contingency?: { kind: string; note: string } | null;
  diagnostic_confidence?: number | null;
  citations: { document_id?: string; section?: string }[];
  perceived?: Record<string, unknown>;
  proposed_intervention?: { id: string; kind: string; title: string; status: string } | null;
  accepted: boolean;
  state: string;
  model_version?: string;
}
