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
  recovery_progress: number;
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
  before?: Record<string, number | string>;
  after?: Record<string, number | string>;
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
    basis?: string;
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

export interface SensitivityView {
  available: boolean;
  incident_id: string;
  reason?: string;
  window_sequence?: number;
  relapse_cycle?: number | null;
  max_stable_streak?: number;
  actual_required_stable_cycles?: number;
  min_safe_window?: number | null;
  margin_cycles?: number | null;
  safe?: boolean;
  sweep?: { required_stable_cycles: number; outcome: string; close_cycle: number | null; is_contract: boolean }[];
  headline?: string;
  verdict?: string;
  advisory?: string;
}

export interface ProvenanceEvidence {
  evidence_id: string;
  kind: string | null;
  tier: string;
  tier_label: string;
  rank: number;
  source_kind: string | null;
  source: string;
  base_weight: number;
  trust: number;
  flags: string[];
  valid: boolean;
  status: string | null;
  rationale: string;
}

export interface ProvenanceView {
  available: boolean;
  incident_id: string;
  reason?: string;
  state?: string;
  outcome_type?: string | null;
  closed?: boolean;
  reopened_count?: number;
  violated_conditions?: string[];
  conditions?: { key: string; kind: string; op: string; status: string; label: string }[];
  evidence?: ProvenanceEvidence[];
  evidence_summary?: {
    count: number;
    mean_trust: number | null;
    min_trust: number | null;
    weakest: { evidence_id: string; tier: string; trust: number; flags: string[] } | null;
  };
  approvals?: { decided_by: string; decided_role: string; decision: string; reason: string; at: string | null }[];
  interventions?: { sequence: number; kind: string; title: string; status: string }[];
  reconciliation?: {
    proposed: number;
    executed: number;
    failed: number;
    denied: number;
    unreconciled: { proposal_id: string; tool: string; issue: string }[];
    orphan_executions: string[];
    ok: boolean;
  };
  audit?: { ok: boolean; broken_at_seq: number | null; count: number };
  trustworthy?: boolean;
  summary?: string;
  note?: string;
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
  basis?: string;
}

export interface SignatureSignal {
  signal: string;
  direction: string;
  op: string;
  fault_code?: string | null;
  respond_by_cycle?: number | null;
  weight: number;
  agreement?: number | null;
  derived_precursor?: boolean;
}

export interface SignatureView {
  available: boolean;
  incident_id: string;
  rung?: string;
  alignment?: number;
  signals?: SignatureSignal[];
  caveats?: string[];
  conditions_matched?: string;
  observed_cycles?: number;
  basis?: string;
  effective_confidence?: number;
  confounding_dimensions?: string[];
  rule_version?: string;
}

export interface CertCondition { key: string; kind: string; op: string; status: string; label: string }
export interface CertApproval {
  decided_by: string;
  decided_role: string;
  decision: string;
  reason?: string;
  at?: string | null;
}
export interface CertIntervention { sequence: number; kind: string; title: string; status: string }

export interface CertificateView {
  available: boolean;
  incident_id: string;
  certificate_id?: string;
  status?: string; // certified | reopened | pending
  verdict?: string;
  issued_at?: string;
  issuer?: string;
  subject?: {
    machine?: string;
    machine_code?: string | null;
    machine_model?: string | null;
    plant_id?: string;
    order_id?: string | null;
    fault_code?: string | null;
    contract_no?: string;
    contract_version?: number;
  };
  conditions?: CertCondition[];
  violated_conditions?: string[];
  evidence_summary?: { count: number; mean_trust: number | null; min_trust: number | null };
  approvals?: CertApproval[];
  interventions?: CertIntervention[];
  stable_cycles?: number;
  required_stable_cycles?: number;
  reopened_count?: number;
  signature?: { rung: string; alignment: number; conditions_matched: string };
  comparability?: { classification?: string; confidence_multiplier?: number | null; confounding_dimensions?: string[] };
  policy_provenance?: Record<string, unknown>;
  audit?: { intact: boolean; entries: number | null; head_hash: string };
  certificate_hash?: string;
  trustworthy?: boolean;
  summary?: string;
  basis?: string;
}

export interface ComparabilityDim {
  key: string;
  label: string;
  baseline: string | number | null;
  observed: string | number | null;
  status: string; // match | shift | unknown
  weight: string; // key | minor | info
  note: string;
}

export interface ComparabilityView {
  available: boolean;
  incident_id: string;
  classification?: string; // COMPARABLE | PARTIALLY_COMPARABLE | NOT_COMPARABLE | UNKNOWN
  confidence_multiplier?: number;
  key_shifts?: number;
  minor_shifts?: number;
  dimensions?: ComparabilityDim[];
  implication?: string;
  reason?: string;
  basis?: string;
}

export interface RecoveryDebtView {
  available: boolean;
  incident_id: string;
  debt_id?: string;
  status?: string; // ACTIVE | SETTLED | BREACHED | CANCELLED
  active?: boolean;
  waived?: { key: string; label: string }[];
  reason?: string; // the waiver reason when available; the "no debt" message when not
  restrictions?: string[];
  monitoring_requirement?: string;
  follow_up?: string;
  granted_by?: string;
  granted_role?: string | null;
  granted_at?: string;
  expires_at?: string;
  minutes_remaining?: number;
  settled_at?: string | null;
  settled_by?: string | null;
  resolution_note?: string | null;
  basis?: string;
}

export interface SensorTrustView {
  available: boolean;
  incident_id: string;
  status?: string; // TRUSTED | DEGRADED | UNTRUSTED | UNKNOWN
  satisfies_hard_conditions?: boolean;
  reasons?: string[];
  per_metric?: { metric: string; status: string; reasons: string[]; checks: { name: string; ok: boolean; detail: string }[] }[];
  basis?: string;
  reason?: string;
}

export interface LotAtRiskView {
  available: boolean;
  incident_id: string;
  at_risk?: boolean;
  summary?: string;
  last_good_cycle?: number | null;
  first_questionable_cycle?: number | null;
  fault_code?: string;
  affected_window?: { from: string | null; to: string | null };
  affected_lots?: { id: string; disposition: string; produced_from: string | null; produced_to: string | null }[];
  affected_lot_count?: number;
  current_dispositions?: string[];
  affected_quantity_note?: string;
  required_quality_action?: string;
  basis?: string;
}

export interface MaiaMessage {
  kind: string;
  incident_id: string;
  title: string;
  body: string;
  severity: string;
  actions: { label: string; deep_link: string }[];
  surface: string;
}
export interface MaiaView { messages: MaiaMessage[]; kinds: string[] }

export interface StakeholderView {
  available: boolean;
  persona: string;
  label?: string;
  focus?: string;
  tabs?: string[];
  can_act?: string[];
  can_approve?: string[];
  reason?: string;
}

export interface DispInvariant { key: string; label: string; ok: boolean; detail: string }

export interface DispositionView {
  available: boolean;
  incident_id: string;
  disposition?: string; // VERIFIED | CONDITIONAL | FAILED | INSUFFICIENT_EVIDENCE | ESCALATION_REQUIRED | IN_PROGRESS
  meaning?: string;
  decided?: boolean;
  can_close?: boolean;
  verdict?: string;
  reasons?: string[];
  hard_invariants?: DispInvariant[];
  human_status?: { technician: string; telemetry: string; quality: string; supervisor: string };
  conflict?: boolean;
  effective_confidence?: number | null;
  comparability?: { classification?: string; confidence_multiplier?: number | null; key_shifts?: number; confounding_dimensions?: string[] };
  policy_provenance?: Record<string, unknown>;
  stable_cycles?: number;
  required_stable_cycles?: number;
  basis?: string;
  reason?: string;
}

export interface FcrsFactor {
  key: string;
  label: string;
  weight: number;
  value: number;
  contribution: number;
  detail?: string;
}

export interface ClosureRiskView {
  available: boolean;
  incident_id: string;
  risk?: number;
  risk_pct?: number;
  band?: string; // low | elevated | high
  recommendation?: string;
  dominant_driver?: string | null;
  fault_in_window?: boolean;
  quality_released?: boolean;
  factors?: FcrsFactor[];
  basis?: string;
  reason?: string;
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
