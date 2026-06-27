"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Clock, FileWarning, ShieldCheck, XCircle } from "lucide-react";
import { useContract, useMe, useRecoveryActions, useRecoveryDebt } from "@/lib/hooks";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Badge, Chip } from "@/components/forge/primitives";
import type { Tone } from "@/lib/state-meta";
import type { Condition } from "@/lib/types";

const STATUS: Record<string, { tone: Tone; label: string }> = {
  ACTIVE: { tone: "warning", label: "Active waiver" },
  SETTLED: { tone: "verified", label: "Settled" },
  BREACHED: { tone: "failure", label: "Breached — escalated" },
  CANCELLED: { tone: "steel", label: "Cancelled" },
};
const APPROVER = ["SUPERVISOR", "QUALITY_ENGINEER", "PLANT_ADMIN"];
const fmt = (iso?: string | null) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }); }
  catch { return iso; }
};

export function RecoveryDebtPanel({ incidentId }: { incidentId: string }) {
  const { data } = useRecoveryDebt(incidentId, 4000);
  const { data: contract } = useContract(incidentId);
  const { data: me } = useMe();
  const { grantDebt, settleDebt } = useRecoveryActions(incidentId);

  const isApprover = !!me && APPROVER.includes(String(me.role));
  const active = !!data?.available && data.status === "ACTIVE";

  const waivable: Condition[] = useMemo(
    () => (contract
      ? [...contract.conditions.machine, ...contract.conditions.production]
          .filter((c) => c.op !== "NOT_RECUR" && !/safety|interlock/i.test(c.key))
      : []),
    [contract],
  );

  const [key, setKey] = useState("");
  const [reason, setReason] = useState("");
  const [restriction, setRestriction] = useState("line speed <= 70%");
  const [mins, setMins] = useState(90);
  const [monitoring, setMonitoring] = useState("thermal inspection every 20 min");
  const [followUp, setFollowUp] = useState("re-measure and verify the waived condition");
  useEffect(() => { if (!key && waivable[0]) setKey(waivable[0].key); }, [key, waivable]);

  if (!data) return null;
  const st = STATUS[data.status ?? "ACTIVE"] ?? STATUS.ACTIVE;
  const grantErr = grantDebt.error as ApiError | null;

  return (
    <section className="space-y-4">
      {/* existing waiver */}
      {data.available && (
        <div className="rounded-xl border border-line bg-surface-1 p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <FileWarning className="h-4 w-4 text-agent" aria-hidden />
              <h3 className="text-sm font-semibold text-ink-hi">Recovery debt</h3>
              <span className="text-[12px] text-ink-mut">conditional recovery · concession</span>
            </div>
            <Badge tone={st.tone}>
              {st.tone === "verified" ? <ShieldCheck className="h-3 w-3" aria-hidden /> :
               st.tone === "failure" ? <XCircle className="h-3 w-3" aria-hidden /> :
               <AlertTriangle className="h-3 w-3" aria-hidden />}
              {st.label}
            </Badge>
          </div>

          <p className="mt-2 text-sm text-ink">{data.reason}</p>

          <div className="mt-3 grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
            <Field label="Waived condition(s)">{(data.waived ?? []).map((w) => w.label).join(", ") || "—"}</Field>
            <Field label="Expiry">
              {active
                ? <span className="inline-flex items-center gap-1"><Clock className="h-3.5 w-3.5 text-warning" aria-hidden />{data.minutes_remaining}m left · {fmt(data.expires_at)}</span>
                : fmt(data.expires_at)}
            </Field>
            <Field label="Monitoring">{data.monitoring_requirement || "—"}</Field>
            <Field label="Follow-up">{data.follow_up || "—"}</Field>
            <Field label="Granted by">{data.granted_by}{data.granted_role ? ` · ${data.granted_role}` : ""}</Field>
            <Field label="Granted at">{fmt(data.granted_at)}</Field>
          </div>

          {data.restrictions && data.restrictions.length > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="label">Restrictions</span>
              {data.restrictions.map((r, i) => <Chip key={i}>{r}</Chip>)}
            </div>
          )}

          {data.resolution_note && <p className="mt-3 text-[12px] text-ink-mut">{data.resolution_note}</p>}

          {active && isApprover && (
            <div className="mt-4 flex items-center gap-3 border-t border-line pt-3">
              <button
                onClick={() => settleDebt.mutate()}
                disabled={settleDebt.isPending}
                className="inline-flex items-center gap-1.5 rounded-[10px] border border-line-strong px-3 py-1.5 text-sm text-ink hover:bg-surface-2 disabled:opacity-50"
              >
                <ShieldCheck className="h-4 w-4 text-verified" aria-hidden /> Settle (verify the waived condition)
              </button>
              <span className="text-[11px] text-ink-mut">Settles only if the waived condition now passes.</span>
            </div>
          )}
          {settleDebt.error != null && (
            <p className="mt-2 text-[12px] text-failure">{(settleDebt.error as ApiError).detail}</p>
          )}

          {active && (
            <p className="mt-3 text-[11px] text-ink-mut">{data.basis}</p>
          )}
        </div>
      )}

      {/* grant a new waiver (authorised humans only) */}
      {isApprover && !active && (
        <div className="rounded-xl border border-line bg-surface-1 p-5">
          <div className="label mb-1">Grant a recovery-debt waiver</div>
          <p className="mb-3 text-[12px] text-ink-mut">
            Authorise <b className="font-medium text-ink">conditional operation</b> under restrictions while an
            unmet condition is deferred. Routes through the Agent Action Gateway (APPROVAL_REQUIRED). A relapse,
            quality, or safety condition can never be waived.
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-xs text-ink-mut">Waived condition
              <select value={key} onChange={(e) => setKey(e.target.value)} className="mt-1 w-full rounded-lg border border-line bg-surface-2 px-2 py-1.5 text-sm text-ink">
                {waivable.length === 0 && <option value="">(no waivable conditions)</option>}
                {waivable.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
              </select>
            </label>
            <label className="text-xs text-ink-mut">Expires in (minutes)
              <input type="number" min={1} max={1440} value={mins} onChange={(e) => setMins(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-line bg-surface-2 px-2 py-1.5 text-sm text-ink" />
            </label>
            <label className="text-xs text-ink-mut sm:col-span-2">Reason
              <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. temperature not fully stable; run reduced while it settles"
                className="mt-1 w-full rounded-lg border border-line bg-surface-2 px-2 py-1.5 text-sm text-ink" />
            </label>
            <label className="text-xs text-ink-mut">Restriction
              <input value={restriction} onChange={(e) => setRestriction(e.target.value)}
                className="mt-1 w-full rounded-lg border border-line bg-surface-2 px-2 py-1.5 text-sm text-ink" />
            </label>
            <label className="text-xs text-ink-mut">Monitoring
              <input value={monitoring} onChange={(e) => setMonitoring(e.target.value)}
                className="mt-1 w-full rounded-lg border border-line bg-surface-2 px-2 py-1.5 text-sm text-ink" />
            </label>
            <label className="text-xs text-ink-mut sm:col-span-2">Follow-up
              <input value={followUp} onChange={(e) => setFollowUp(e.target.value)}
                className="mt-1 w-full rounded-lg border border-line bg-surface-2 px-2 py-1.5 text-sm text-ink" />
            </label>
          </div>
          <div className="mt-3 flex items-center gap-3">
            <button
              onClick={() => grantDebt.mutate({
                waived_condition_keys: key ? [key] : [], reason,
                restrictions: restriction ? [restriction] : [], expires_in_minutes: mins,
                monitoring_requirement: monitoring, follow_up: followUp,
              })}
              disabled={grantDebt.isPending || !key || !reason}
              className="inline-flex items-center gap-1.5 rounded-[10px] border border-line-strong bg-surface-2 px-3 py-1.5 text-sm text-ink hover:bg-surface-3 disabled:opacity-50"
            >
              <FileWarning className="h-4 w-4 text-warning" aria-hidden /> Grant waiver
            </button>
            {grantErr && <span className="text-[12px] text-failure">{grantErr.detail}</span>}
          </div>
        </div>
      )}

      {!data.available && !isApprover && (
        <section className="rounded-xl border border-line bg-surface-1 p-6 text-sm text-ink-mut">
          No recovery-debt waiver on this incident. Granting one requires a supervisor or quality engineer.
        </section>
      )}
    </section>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-line/60 pb-1">
      <span className="label">{label}</span>
      <span className="text-right text-ink">{children}</span>
    </div>
  );
}
