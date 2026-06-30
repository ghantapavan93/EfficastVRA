"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Activity, AlertTriangle, CheckCircle2, Loader2, ShieldCheck } from "lucide-react";
import type { MissionDetail, UploadedVerificationResult } from "@/lib/types";

const TONE: Record<string, { ring: string; text: string; Icon: typeof Activity; label: string }> = {
  reopened: { ring: "border-warning/50", text: "text-warning", Icon: AlertTriangle, label: "Closure rejected" },
  escalated: { ring: "border-failure/50", text: "text-failure", Icon: AlertTriangle, label: "Escalated" },
  insufficient_evidence: { ring: "border-warning/50", text: "text-warning", Icon: AlertTriangle, label: "Not certified" },
  verified: { ring: "border-verified/50", text: "text-verified", Icon: CheckCircle2, label: "Verified" },
  monitoring: { ring: "border-agent/50", text: "text-agent", Icon: Activity, label: "Monitoring" },
  blocked: { ring: "border-warning/50", text: "text-warning", Icon: AlertTriangle, label: "Blocked" },
};

export function UploadedVerification({ id, m, onDone }: { id: string; m: MissionDetail; onDone?: () => void }) {
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<UploadedVerificationResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // Only upload-origin missions that haven't been put under contract yet can be replayed.
  if (!m.from_upload) return null;
  if (m.has_contract && !res) return null;

  const run = async () => {
    setBusy(true); setErr(null);
    try {
      const r = await fetch(`/api/intake/missions/${id}/run-verification`, {
        method: "POST", headers: { "X-VRA-User": "s.vega" },
      });
      const out: UploadedVerificationResult = await r.json();
      setRes(out);
      if (out.ran) setTimeout(() => onDone?.(), 400);
      else setErr(out.reason || "Verification could not run.");
    } catch (e) { setErr(String(e)); }
    finally { setBusy(false); }
  };

  const tone = res?.outcome ? TONE[res.outcome] ?? TONE.monitoring : null;

  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      className={`glow-agent relative overflow-hidden rounded-xl border ${tone ? tone.ring : "border-agent/40"} bg-surface-1 p-5`}
    >
      <div className="pointer-events-none absolute -right-16 -top-16 h-44 w-44 rounded-full bg-agent/10 blur-3xl" />
      {!res ? (
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="max-w-2xl">
            <div className="label mb-1 flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5 text-agent" /> The last mile</div>
            <h3 className="text-base font-semibold text-ink-hi">Replay your uploaded telemetry through the deterministic evaluator</h3>
            <p className="mt-1.5 text-sm text-ink-mut">
              {m.telemetry_rows} cycle{m.telemetry_rows === 1 ? "" : "s"} of telemetry are attached to this mission.
              Run them through the same Recovery Contract evaluator that verifies the reference mission — the
              <span className="text-ink"> engine renders the verdict, not a heuristic</span>. Nothing is fabricated; it stops at the next human gate.
            </p>
          </div>
          <button
            onClick={run} disabled={busy}
            className="glow-agent inline-flex h-10 shrink-0 items-center gap-2 rounded-[10px] bg-agent px-4 text-sm font-semibold text-black transition-transform hover:scale-[1.02] disabled:opacity-60"
          >
            {busy ? <><Loader2 className="h-4 w-4 animate-spin" /> Replaying {m.telemetry_rows} cycles…</> : <><Activity className="h-4 w-4" /> Replay through the evaluator</>}
          </button>
        </div>
      ) : (
        <div>
          <div className="flex items-center gap-2">
            {tone && <tone.Icon className={`h-4 w-4 ${tone.text}`} />}
            <span className={`text-sm font-semibold ${tone?.text ?? "text-ink-hi"}`}>{tone?.label ?? "Result"}</span>
            <span className="mono text-[11px] text-ink-faint">verdict by {res.verdict_by}</span>
          </div>
          <p className="mt-2 max-w-3xl text-sm text-ink">{res.message || res.reason}</p>
          {res.ran && (
            <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-xs text-ink-mut">
              <span><span className="label mr-1.5">Cycles replayed</span><span className="mono text-ink">{res.cycles_replayed}</span></span>
              {res.relapse_cycle != null && <span><span className="label mr-1.5">Relapse at</span><span className="mono text-warning">cycle {res.relapse_cycle}</span></span>}
              <span><span className="label mr-1.5">Stable streak</span><span className="mono text-ink">{res.stable_streak}</span></span>
              <span><span className="label mr-1.5">State</span><span className="mono text-ink">{res.state}</span></span>
            </div>
          )}
        </div>
      )}
      {err && !res && <p className="mt-3 text-xs text-failure">{err}</p>}
    </motion.section>
  );
}
