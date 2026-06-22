"use client";

import { useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Check, ChevronRight, Loader2, PlayCircle, RotateCcw, X } from "lucide-react";
import { useState } from "react";
import { api, setApiUser } from "@/lib/api";
import { useMe } from "@/lib/hooks";
import { USERS, useRole } from "@/lib/role";
import { cn } from "@/lib/utils";
import { Button } from "@/components/forge/primitives";
import { useShell } from "@/components/shell/shell-context";

const TECH = USERS.technician.username;
const SUP = USERS.supervisor.username;
const QUAL = USERS.quality_engineer.username;

interface Step {
  label: string;
  hint: string;
  run: (inc: string) => Promise<void>;
}

async function withUser<T>(username: string, fn: () => Promise<T>, restore: string): Promise<T> {
  setApiUser(username);
  try {
    return await fn();
  } finally {
    setApiUser(restore);
  }
}

const STEPS: Step[] = [
  { label: "Draft recovery contract", hint: "Agent extracts requirements → RC-1042 v1", run: async (inc) => { await api.draft(inc); } },
  {
    label: "Submit evidence & approve contract",
    hint: "Technician measures · supervisor approves",
    run: async (inc) => {
      await api.review(inc);
      const ids = await api.demoIds();
      await withUser(TECH, () => api.submitEvidence(ids.evidence["post_alignment_measurement"].id, { value_num: 3.6, unit: "mm/s" }), SUP);
      await withUser(TECH, () => api.submitEvidence(ids.evidence["technician_completion"].id, { value_text: "completed" }), SUP);
      await api.decide(ids.approvals["contract_review"].id, { decision: "approve", reason: "begin monitoring" });
    },
  },
  { label: "Begin recovery monitoring", hint: "Open verification window 1", run: async (inc) => { await api.startMonitoring(inc); } },
  { label: "Advance 16 cycles", hint: "Production appears to recover", run: async (inc) => { await api.advance(inc, 16); } },
  { label: "Cycle 17 — trigger F27 recurrence", hint: "The agent catches the false recovery", run: async (inc) => { await api.advance(inc, 1); } },
  { label: "Approve bearing contingency", hint: "Reserve BR-6205 · assign technician", run: async (inc) => { await api.approveContingency(inc); } },
  {
    label: "Complete bearing replacement",
    hint: "Technician evidence → second window",
    run: async (inc) => {
      const ids = await api.demoIds();
      await withUser(TECH, () => api.submitEvidence(ids.evidence["bearing_post_measurement"].id, { value_num: 3.1, unit: "mm/s" }), SUP);
      await withUser(TECH, () => api.submitEvidence(ids.evidence["technician_completion_2"].id, { value_text: "completed" }), SUP);
      await api.completeContingency(inc);
    },
  },
  { label: "Advance 29 stable cycles", hint: "No fault recurrence", run: async (inc) => { await api.advance(inc, 29); } },
  {
    label: "Quality release",
    hint: "Quality engineer passes first-piece & releases",
    run: async (inc) => {
      const ids = await api.demoIds();
      await withUser(QUAL, () => api.submitEvidence(ids.evidence["first_piece_quality"].id, { value_text: "pass" }), SUP);
      await withUser(QUAL, () => api.decide(ids.approvals["quality_release"].id, { decision: "approve", reason: "lots dispositioned" }), SUP);
    },
  },
  { label: "Verify recovery (cycle 30)", hint: "Publish verified recovery + knowledge candidate", run: async (inc) => { await api.advance(inc, 1); } },
];

export function DemoController() {
  const { demoOpen, setDemoOpen, agentPaused } = useShell();
  const { username } = useRole();
  const { data: me } = useMe();
  const qc = useQueryClient();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);

  if (!me?.demo_mode || !demoOpen) return null;
  const inc = "INC-2841";

  const refresh = () => qc.invalidateQueries();

  const runStep = async (i: number) => {
    if (busy || agentPaused) return;
    setBusy(true);
    try {
      setApiUser(username);
      await STEPS[i].run(inc);
      setStep(i + 1);
    } catch (e) {
      console.error("demo step failed", e);
    } finally {
      setApiUser(username);
      setBusy(false);
      refresh();
    }
  };

  const reset = async () => {
    setBusy(true);
    try {
      await api.demoReset();
      setStep(0);
    } finally {
      setBusy(false);
      refresh();
    }
  };

  return (
    <motion.aside
      initial={{ x: 360, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.26, ease: [0.16, 1, 0.3, 1] }}
      className="fixed bottom-4 right-4 z-40 w-[340px] overflow-hidden rounded-xl border border-line-strong bg-surface-2 shadow-e3"
      aria-label="Demo controller"
    >
      <div className="flex items-center justify-between border-b border-line px-3 py-2">
        <div className="flex items-center gap-2">
          <PlayCircle className="h-4 w-4 text-brand" />
          <span className="text-sm font-semibold text-ink-hi">Demo controller</span>
        </div>
        <button onClick={() => setDemoOpen(false)} aria-label="Close demo controller" className="text-ink-mut hover:text-ink">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="max-h-[44vh] overflow-y-auto p-2">
        {STEPS.map((s, i) => {
          const done = i < step;
          const current = i === step;
          return (
            <button
              key={s.label}
              disabled={busy || agentPaused || !current}
              onClick={() => runStep(i)}
              className={cn(
                "mb-1 flex w-full items-start gap-2.5 rounded-lg border px-2.5 py-2 text-left transition-colors",
                current ? "border-agent/50 bg-agent-soft" : done ? "border-line bg-surface-1" : "border-line bg-surface-1 opacity-55",
              )}
            >
              <span className={cn("mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-md text-[11px]", done ? "bg-verified-soft text-verified" : current ? "bg-agent text-white" : "bg-surface-3 text-ink-mut")}>
                {done ? <Check className="h-3 w-3" /> : busy && current ? <Loader2 className="h-3 w-3 animate-spin" /> : i + 1}
              </span>
              <span className="min-w-0">
                <span className="block text-[13px] font-medium text-ink">{s.label}</span>
                <span className="block text-[11px] text-ink-mut">{s.hint}</span>
              </span>
              {current && <ChevronRight className="ml-auto mt-1 h-4 w-4 shrink-0 text-agent" />}
            </button>
          );
        })}
      </div>

      <div className="flex items-center gap-2 border-t border-line p-2">
        <Button size="sm" variant="outline" onClick={reset} disabled={busy} className="flex-1">
          <RotateCcw className="h-3.5 w-3.5" /> Reset
        </Button>
        <Button size="sm" variant="primary" disabled={busy || agentPaused || step >= STEPS.length} onClick={() => runStep(step)} className="flex-1">
          {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Run next step"}
        </Button>
      </div>
      {agentPaused && <div className="border-t border-line bg-failure-soft px-3 py-1.5 text-[11px] text-failure">Agent side effects paused — resume to continue.</div>}
    </motion.aside>
  );
}
