"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Ban, CheckCircle2, ChevronsRight, Gavel, Loader2, ShieldAlert, Zap } from "lucide-react";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { useContract, useRecoveryActions } from "@/lib/hooks";
import { useRole } from "@/lib/role";
import type { MissionDetail } from "@/lib/types";
import { Button } from "@/components/forge/primitives";
import { useShell } from "@/components/shell/shell-context";

export function ActionBar({ m }: { m: MissionDetail }) {
  const id = m.id;
  const { role } = useRole();
  const { agentPaused } = useShell();
  const { data: contract } = useContract(id);
  const a = useRecoveryActions(id);
  const [err, setErr] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const apprId = (key: string) => contract?.approval_requirements.find((x) => x.key === key)?.id;
  const evId = (key: string) => contract?.evidence_requirements.find((x) => x.key === key)?.id;
  const isSup = role === "supervisor" || role === "plant_admin";

  const run = async (fn: () => Promise<unknown>) => {
    setErr(null);
    setPending(true);
    try {
      await fn();
    } catch (e) {
      setErr(e instanceof ApiError ? e.detail : (e as Error).message);
    } finally {
      setPending(false);
    }
  };

  let content: React.ReactNode = null;
  const s = m.state;

  if (s === "INTERVENTION_RECORDED") {
    content = (
      <Primary disabled={agentPaused || pending} onClick={() => run(() => a.draft.mutateAsync())}>
        <Zap className="h-4 w-4" /> Draft recovery contract
      </Primary>
    );
  } else if (s === "RECOVERY_CONTRACT_DRAFTED") {
    content = isSup ? (
      <Primary disabled={pending} onClick={() => run(async () => {
        await a.review.mutateAsync();
        const rid = apprId("contract_review");
        if (rid) await a.decide.mutateAsync({ reqId: rid, decision: "approve", reason: "begin monitoring" });
      })}>
        <Gavel className="h-4 w-4" /> Review & approve contract
      </Primary>
    ) : <Reason text="A supervisor must review and approve the recovery contract." />;
  } else if (["RECOVERY_CONTRACT_REVIEWED", "AWAITING_REQUIRED_EVIDENCE", "READY_FOR_MONITORING"].includes(s)) {
    content = (
      <Primary disabled={agentPaused || pending} onClick={() => run(() => a.startMonitoring.mutateAsync())}>
        <ChevronsRight className="h-4 w-4" /> Begin recovery monitoring
      </Primary>
    );
  } else if (s === "MONITORING_RECOVERY") {
    const awaitingQuality = contract?.evaluation.awaiting_quality;
    content = (
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="agent" disabled={agentPaused || pending} onClick={() => run(() => a.advance.mutateAsync(1))}>
          {pending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Advance 1 cycle"}
        </Button>
        <Button variant="outline" disabled={agentPaused || pending} onClick={() => run(() => a.advance.mutateAsync(5))}>Advance 5</Button>
        {awaitingQuality && role === "quality_engineer" && (
          <Button variant="approval" disabled={pending} onClick={() => run(async () => {
            const fp = evId("first_piece_quality");
            if (fp) await a.submitEvidence.mutateAsync({ reqId: fp, body: { value_text: "pass" } });
            const qr = apprId("quality_release");
            if (qr) await a.decide.mutateAsync({ reqId: qr, decision: "approve", reason: "first-piece passed" });
          })}>
            <CheckCircle2 className="h-4 w-4" /> Release quality
          </Button>
        )}
      </div>
    );
  } else if (s === "CONTINGENCY_AWAITING_APPROVAL") {
    content = isSup ? (
      <ApproveContingencyDialog disabled={pending} onConfirm={() => run(() => a.approveContingency.mutateAsync())} />
    ) : <Reason text="A supervisor must approve the bearing-replacement contingency." />;
  } else if (s === "CONTINGENCY_IN_PROGRESS") {
    content = (
      <Primary disabled={agentPaused || pending} onClick={() => run(() => a.completeContingency.mutateAsync())}>
        <ChevronsRight className="h-4 w-4" /> Complete bearing replacement
      </Primary>
    );
  } else if (s === "VERIFIED_RECOVERY") {
    content = (
      <span className="inline-flex items-center gap-2 text-sm font-medium text-verified">
        <CheckCircle2 className="h-4 w-4" /> Recovery verified — incident closed.
      </span>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex flex-wrap items-center gap-3">
        <span className="label">Next action</span>
        {content}
      </div>
      {err && <p className="text-xs text-failure">{err}</p>}
    </div>
  );
}

function Primary({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return <Button variant="primary" {...props}>{children}</Button>;
}

function Reason({ text }: { text: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-ink-mut">
      <Ban className="h-3.5 w-3.5 text-ink-faint" /> {text}
    </span>
  );
}

function ApproveContingencyDialog({ onConfirm, disabled }: { onConfirm: () => void; disabled: boolean }) {
  const [open, setOpen] = useState(false);
  const [ack, setAck] = useState(false);
  return (
    <Dialog.Root open={open} onOpenChange={(o) => { setOpen(o); setAck(false); }}>
      <Dialog.Trigger asChild>
        <Button variant="approval" disabled={disabled}><ShieldAlert className="h-4 w-4" /> Approve bearing contingency</Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-[var(--scrim)] backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(94vw,480px)] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-line-strong bg-surface-2 p-5 shadow-e3 animate-fade-up">
          <Dialog.Title className="text-base font-semibold text-ink-hi">Approve bearing-replacement contingency</Dialog.Title>
          <Dialog.Description className="mt-1 text-sm text-ink-mut">Review the scope before approving. Backend authorization remains authoritative.</Dialog.Description>

          <div className="mt-4 rounded-lg border border-verified/30 bg-verified-soft p-3">
            <div className="label text-verified">You are authorizing</div>
            <ul className="mt-1.5 space-y-1 text-sm text-ink">
              {["Release bearing-replacement work order", "Reserve bearing BR-6205", "Assign technician", "Begin a second verification window after completion"].map((g) => (
                <li key={g} className="flex items-center gap-2"><CheckCircle2 className="h-3.5 w-3.5 text-verified" /> {g}</li>
              ))}
            </ul>
          </div>
          <div className="mt-3 rounded-lg border border-line bg-surface-1 p-3">
            <div className="label">You are NOT authorizing</div>
            <ul className="mt-1.5 grid grid-cols-2 gap-1 text-[13px] text-ink-mut">
              {["Machine start / stop / restart", "PLC or set-point change", "Alarm or interlock bypass", "Lockout/tagout confirmation", "Safety certification", "Automatic quality release"].map((d) => (
                <li key={d} className="flex items-center gap-1.5"><Ban className="h-3.5 w-3.5 text-failure" /> {d}</li>
              ))}
            </ul>
          </div>

          <label className="mt-4 flex items-center gap-2 text-sm text-ink">
            <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} className="h-4 w-4 accent-[var(--approval)]" />
            I understand the scope of this approval.
          </label>

          <div className="mt-5 flex justify-end gap-2">
            <Dialog.Close asChild><Button size="sm" variant="ghost">Cancel</Button></Dialog.Close>
            <Button size="sm" variant="approval" disabled={!ack} onClick={() => { setOpen(false); onConfirm(); }}>
              Approve contingency
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
