"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type EvidenceBody } from "./api";
import { useRole } from "./role";

// Queries are keyed by the active username too, so switching role refetches with the new identity.
export function useMe() {
  const { username } = useRole();
  return useQuery({ queryKey: ["me", username], queryFn: api.me });
}

export function useMissions(refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({ queryKey: ["missions", username], queryFn: api.missions, refetchInterval });
}

export function useMission(id: string, refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({ queryKey: ["mission", id, username], queryFn: () => api.mission(id), refetchInterval });
}

export function useContract(id: string, refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({ queryKey: ["contract", id, username], queryFn: () => api.contract(id), refetchInterval });
}

export function useEvidence(id: string, refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({ queryKey: ["evidence", id, username], queryFn: () => api.evidence(id), refetchInterval });
}

export function useTimeline(id: string, refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({ queryKey: ["timeline", id, username], queryFn: () => api.timeline(id), refetchInterval });
}

export function useOutcome(id: string) {
  const { username } = useRole();
  return useQuery({ queryKey: ["outcome", id, username], queryFn: () => api.outcome(id) });
}

export function useAudit(id: string) {
  const { username } = useRole();
  return useQuery({ queryKey: ["audit", id, username], queryFn: () => api.audit(id) });
}

export function useReasoning(id: string, refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({
    queryKey: ["reasoning", id, username],
    queryFn: () => api.reasoning(id),
    refetchInterval,
  });
}

export function useTroubleshoot(params: { fault_code?: string; machine_model?: string; q?: string }) {
  const enabled = Boolean(params.fault_code || params.machine_model || params.q);
  return useQuery({
    queryKey: ["troubleshoot", params],
    queryFn: () => api.troubleshoot(params),
    enabled,
  });
}

export function useForecast(id: string, refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({
    queryKey: ["forecast", id, username],
    queryFn: () => api.forecast(id),
    refetchInterval,
  });
}

export function useSignature(id: string, refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({
    queryKey: ["signature", id, username],
    queryFn: () => api.signature(id),
    refetchInterval,
  });
}

export function useCertificate(id: string, refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({
    queryKey: ["certificate", id, username],
    queryFn: () => api.certificate(id),
    refetchInterval,
  });
}

export function useClosureRisk(id: string, refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({
    queryKey: ["closure-risk", id, username],
    queryFn: () => api.closureRisk(id),
    refetchInterval,
  });
}

export function useDisposition(id: string, refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({
    queryKey: ["disposition", id, username],
    queryFn: () => api.disposition(id),
    refetchInterval,
  });
}

export function useComparability(id: string, refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({
    queryKey: ["comparability", id, username],
    queryFn: () => api.comparability(id),
    refetchInterval,
  });
}

export function useRecoveryDebt(id: string, refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({
    queryKey: ["recovery-debt", id, username],
    queryFn: () => api.recoveryDebt(id),
    refetchInterval,
  });
}

export function useDecision(id: string, refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({
    queryKey: ["decision", id, username],
    queryFn: () => api.decision(id),
    refetchInterval,
  });
}

export function useReliability(id: string, refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({
    queryKey: ["reliability", id, username],
    queryFn: () => api.reliability(id),
    refetchInterval,
  });
}

export function useProvenance(id: string, refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({
    queryKey: ["provenance", id, username],
    queryFn: () => api.provenance(id),
    refetchInterval,
  });
}

export function useSensitivity(id: string, refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({
    queryKey: ["sensitivity", id, username],
    queryFn: () => api.sensitivity(id),
    refetchInterval,
  });
}

export function useAlerts(refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({ queryKey: ["alerts", username], queryFn: api.alerts, refetchInterval });
}

export function useKnowledge(refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({ queryKey: ["knowledge", username], queryFn: api.knowledge, refetchInterval });
}

export function useReviewKnowledge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: string; decision: string; reason?: string }) =>
      api.reviewKnowledge(v.id, { decision: v.decision, reason: v.reason }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["knowledge"] }),
  });
}

export function useNotifications(refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({ queryKey: ["notifications", username], queryFn: api.notifications, refetchInterval });
}

export function useMarkNotificationRead() {
  const qc = useQueryClient();
  const { username } = useRole();
  return useMutation({
    mutationFn: (id: string) => api.markNotificationRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications", username] }),
  });
}

export function useDiagnosis(id: string, refetchInterval?: number) {
  const { username } = useRole();
  return useQuery({
    queryKey: ["diagnosis", id, username],
    queryFn: () => api.diagnosis(id),
    refetchInterval,
  });
}

/** Triage a MAIA alert with the agent (creates an incident with a proposed intervention). */
export function useTriageAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (alertId: string) => api.triageAlert(alertId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts"] });
      qc.invalidateQueries({ queryKey: ["missions"] });
    },
  });
}

/** Mutations that invalidate every view of an incident after a backend state change. */
export function useRecoveryActions(id: string) {
  const qc = useQueryClient();
  const invalidate = () => {
    for (const key of ["missions", "mission", "contract", "evidence", "timeline", "outcome", "audit", "reasoning", "diagnosis", "alerts", "forecast", "signature", "certificate", "closure-risk", "disposition", "comparability", "recovery-debt", "decision", "reliability", "provenance", "sensitivity"]) {
      qc.invalidateQueries({ queryKey: key === "missions" ? ["missions"] : [key, id] });
    }
  };
  return {
    invalidate,
    draft: useMutation({ mutationFn: () => api.draft(id), onSuccess: invalidate }),
    review: useMutation({ mutationFn: () => api.review(id), onSuccess: invalidate }),
    startMonitoring: useMutation({ mutationFn: () => api.startMonitoring(id), onSuccess: invalidate }),
    advance: useMutation({ mutationFn: (n: number) => api.advance(id, n), onSuccess: invalidate }),
    approveContingency: useMutation({ mutationFn: () => api.approveContingency(id), onSuccess: invalidate }),
    completeContingency: useMutation({ mutationFn: () => api.completeContingency(id), onSuccess: invalidate }),
    acceptDiagnosis: useMutation({ mutationFn: () => api.acceptDiagnosis(id), onSuccess: invalidate }),
    submitEvidence: useMutation({
      mutationFn: (v: { reqId: string; body: EvidenceBody }) => api.submitEvidence(v.reqId, v.body),
      onSuccess: invalidate,
    }),
    decide: useMutation({
      mutationFn: (v: { reqId: string; decision: string; reason?: string }) =>
        api.decide(v.reqId, { decision: v.decision, reason: v.reason }),
      onSuccess: invalidate,
    }),
    grantDebt: useMutation({
      mutationFn: (body: {
        waived_condition_keys: string[];
        reason: string;
        restrictions?: string[];
        expires_in_minutes?: number;
        monitoring_requirement?: string;
        follow_up?: string;
      }) => api.grantRecoveryDebt(id, body),
      onSuccess: invalidate,
    }),
    settleDebt: useMutation({ mutationFn: () => api.settleRecoveryDebt(id), onSuccess: invalidate }),
  };
}
