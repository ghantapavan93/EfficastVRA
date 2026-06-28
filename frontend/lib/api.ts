import type {
  AppNotification,
  AuditEvent,
  AuditIntegrity,
  CertificateView,
  ClosureRiskView,
  ComparabilityView,
  ContractView,
  DispositionView,
  DecisionView,
  DiagnosisView,
  ForecastView,
  KnowledgeList,
  MaiaAlert,
  Me,
  MissionDetail,
  MissionSummary,
  NotificationsView,
  LotAtRiskView,
  MaiaView,
  OutcomeView,
  ProvenanceView,
  RecoveryDebtView,
  SensorTrustView,
  StakeholderView,
  ReasoningView,
  ReliabilityView,
  SensitivityView,
  SignatureView,
  TimelineView,
  TroubleshootResult,
} from "./types";

// The active principal's username, sent as X-VRA-User. The role provider keeps this in sync.
let apiUser = "s.vega";
export function setApiUser(u: string) {
  apiUser = u;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public code?: string,
    public stage?: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    ...opts,
    headers: { "Content-Type": "application/json", "X-VRA-User": apiUser, ...(opts.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let body: { detail?: string; code?: string; stage?: string } = {};
    try {
      body = await res.json();
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(res.status, body.detail || res.statusText, body.code, body.stage);
  }
  if (res.status === 204) return undefined as T;
  // Guard an empty/non-JSON 200 body — calling res.json() on it throws past TanStack's isError handling
  // and white-screens the view. Return undefined for an empty body; surface a clear error otherwise.
  const text = await res.text();
  if (!text.trim()) return undefined as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError(res.status, "Malformed response from server (expected JSON).", "bad_response");
  }
}

const post = (path: string, body?: unknown) =>
  req(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });

export interface EvidenceBody {
  value_num?: number | null;
  value_text?: string;
  unit?: string;
  source?: string;
}

export const api = {
  me: () => req<Me>("/api/me"),
  missions: () => req<{ missions: MissionSummary[]; environment: string }>("/api/missions"),
  mission: (id: string) => req<MissionDetail>(`/api/missions/${id}`),
  contract: (id: string) => req<ContractView>(`/api/incidents/${id}/contract`),
  contractVersions: (id: string) =>
    req<{ versions: ContractView[] }>(`/api/incidents/${id}/contract-versions`),
  evidence: (id: string) => req<{ groups: Record<string, unknown[]>; requirements: unknown[] }>(
    `/api/incidents/${id}/evidence`,
  ),
  timeline: (id: string) => req<TimelineView>(`/api/incidents/${id}/timeline`),
  outcome: (id: string) => req<OutcomeView>(`/api/incidents/${id}/outcome`),
  audit: (id: string) =>
    req<{ events: AuditEvent[]; integrity: AuditIntegrity }>(`/api/incidents/${id}/audit`),
  knowledge: () => req<KnowledgeList>("/api/knowledge"),
  reviewKnowledge: (id: string, body: { decision: string; reason?: string }) =>
    post(`/api/knowledge/${id}/review`, body),
  notifications: () => req<NotificationsView>("/api/notifications"),
  markNotificationRead: (id: string) => post(`/api/notifications/${id}/read`),
  reasoning: (id: string) => req<ReasoningView>(`/api/incidents/${id}/reasoning`),
  forecast: (id: string) => req<ForecastView>(`/api/incidents/${id}/forecast`),
  signature: (id: string) => req<SignatureView>(`/api/incidents/${id}/signature`),
  certificate: (id: string) => req<CertificateView>(`/api/incidents/${id}/certificate`),
  closureRisk: (id: string) => req<ClosureRiskView>(`/api/incidents/${id}/closure-risk`),
  disposition: (id: string) => req<DispositionView>(`/api/incidents/${id}/disposition`),
  comparability: (id: string) => req<ComparabilityView>(`/api/incidents/${id}/comparability`),
  recoveryDebt: (id: string) => req<RecoveryDebtView>(`/api/incidents/${id}/recovery-debt`),
  sensorTrust: (id: string) => req<SensorTrustView>(`/api/incidents/${id}/sensor-trust`),
  lotAtRisk: (id: string) => req<LotAtRiskView>(`/api/incidents/${id}/lot-at-risk`),
  maiaMessages: (id: string) => req<MaiaView>(`/api/incidents/${id}/maia-messages`),
  stakeholderView: () => req<StakeholderView>(`/api/stakeholder-view`),
  grantRecoveryDebt: (id: string, body: {
    waived_condition_keys: string[];
    reason: string;
    restrictions?: string[];
    expires_in_minutes?: number;
    monitoring_requirement?: string;
    follow_up?: string;
  }) => post(`/api/incidents/${id}/recovery-debt/grant`, body),
  settleRecoveryDebt: (id: string) => post(`/api/incidents/${id}/recovery-debt/settle`),
  decision: (id: string) => req<DecisionView>(`/api/incidents/${id}/decision`),
  reliability: (id: string) => req<ReliabilityView>(`/api/incidents/${id}/reliability`),
  provenance: (id: string) => req<ProvenanceView>(`/api/incidents/${id}/provenance`),
  sensitivity: (id: string) => req<SensitivityView>(`/api/incidents/${id}/sensitivity`),
  troubleshoot: (p: { fault_code?: string; machine_model?: string; q?: string }) => {
    const qs = new URLSearchParams();
    if (p.fault_code) qs.set("fault_code", p.fault_code);
    if (p.machine_model) qs.set("machine_model", p.machine_model);
    if (p.q) qs.set("q", p.q);
    return req<TroubleshootResult>(`/api/troubleshoot?${qs.toString()}`);
  },
  alerts: () => req<{ alerts: MaiaAlert[]; environment: string }>("/api/alerts"),
  diagnosis: (id: string) => req<DiagnosisView>(`/api/incidents/${id}/diagnosis`),

  // actions (all mutations route through the backend gateway/orchestrator)
  draft: (id: string) => post(`/api/incidents/${id}/contract/draft`),
  review: (id: string) => post(`/api/incidents/${id}/contract/review`),
  submitEvidence: (reqId: string, body: EvidenceBody) => post(`/api/evidence/${reqId}/submit`, body),
  decide: (reqId: string, body: { decision: string; reason?: string }) =>
    post(`/api/approvals/${reqId}/decide`, body),
  startMonitoring: (id: string) => post(`/api/incidents/${id}/monitoring/start`),
  advance: (id: string, n: number) =>
    post(`/api/incidents/${id}/advance`, { n }) as Promise<{
      outcome: string;
      cycles: { cycle: number; verdict: string; stable_streak: number; fault: string | null }[];
      state: string;
    }>,
  approveContingency: (id: string) => post(`/api/incidents/${id}/contingency/approve`),
  completeContingency: (id: string) => post(`/api/incidents/${id}/contingency/complete`),
  triageAlert: (alertId: string) =>
    post(`/api/alerts/${alertId}/triage`) as Promise<{ ok: boolean; incident_id: string; state: string }>,
  acceptDiagnosis: (id: string) => post(`/api/incidents/${id}/diagnosis/accept`),
  callTool: (name: string, body: { args?: unknown; incident_id?: string; idempotency_key?: string }) =>
    post(`/api/tools/${name}`, body),

  // demo controller
  demoReset: () => post("/api/demo/reset"),
  demoRun: () => post("/api/demo/run"),
  demoIds: () =>
    req<{
      ids: Record<string, string>;
      incident_state: string | null;
      contract_id: string | null;
      evidence: Record<string, { id: string; status: string; role: string }>;
      approvals: Record<string, { id: string; status: string; role: string }>;
    }>("/api/demo/ids"),
};
