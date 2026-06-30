"use client";

import { useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, ClipboardCheck, Clock, Loader2, Send } from "lucide-react";
import { api } from "@/lib/api";
import { useShiftHandoffPreview, useShiftHandoffs } from "@/lib/hooks";
import { StateBadge } from "@/components/forge/badges";
import { LoadingState } from "@/components/forge/states";
import type { MissionSnapshot, ShiftHandoffView } from "@/lib/types";

export default function HandoffPage() {
  const qc = useQueryClient();
  const { data: preview, isLoading } = useShiftHandoffPreview(8000);
  const { data: list } = useShiftHandoffs(8000);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);

  const record = async () => {
    setBusy(true);
    try {
      await api.createShiftHandoff({ from_shift: from, to_shift: to, notes });
      setFrom(""); setTo(""); setNotes("");
      qc.invalidateQueries({ queryKey: ["handoffs"] });
    } finally { setBusy(false); }
  };

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <header className="mb-6">
        <div className="label mb-1 flex items-center gap-1.5"><ClipboardCheck className="h-3.5 w-3.5 text-agent" /> Shift Handoff</div>
        <h1 className="text-2xl font-semibold text-ink-hi">Hand off the open missions, not a re-derivation</h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-mut">
          Recovery missions outlive a shift. Freeze where everything stands — who must act next, what&apos;s
          blocking — into a record the next shift inherits and acknowledges.
        </p>
      </header>

      {isLoading || !preview ? (
        <LoadingState label="Loading current state" />
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* live preview + create */}
          <div className="space-y-5 lg:col-span-2">
            <section className="rounded-xl border border-line bg-surface-1 p-5">
              <div className="flex items-center justify-between">
                <div className="label">To hand off now</div>
                <div className="flex gap-3 text-[11px] text-ink-mut">
                  <span className="mono">{preview.stats.open_missions} open</span>
                  {preview.stats.reopened > 0 && <span className="mono text-warning">{preview.stats.reopened} reopened</span>}
                  {preview.stats.awaiting_human > 0 && <span className="mono text-agent">{preview.stats.awaiting_human} awaiting human</span>}
                </div>
              </div>
              <p className="mt-1 text-sm text-ink">{preview.headline}</p>
              <ul className="mt-3 space-y-2">
                {preview.open_missions.map((s) => <SnapshotRow key={s.id} s={s} />)}
                {preview.open_missions.length === 0 && <li className="text-sm text-ink-mut">Nothing open — a clean handoff.</li>}
              </ul>
            </section>

            <section className="rounded-xl border border-line bg-surface-1 p-5">
              <div className="label mb-3">Record this handoff</div>
              <div className="flex flex-wrap gap-3">
                <input value={from} onChange={(e) => setFrom(e.target.value)} placeholder="From shift (e.g. A)"
                  className="h-10 w-40 rounded-[10px] border border-line bg-canvas/60 px-3 text-sm text-ink outline-none focus:border-agent/50" />
                <input value={to} onChange={(e) => setTo(e.target.value)} placeholder="To shift (e.g. B)"
                  className="h-10 w-40 rounded-[10px] border border-line bg-canvas/60 px-3 text-sm text-ink outline-none focus:border-agent/50" />
              </div>
              <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3}
                placeholder="Notes for the incoming shift (optional)…"
                className="mt-3 w-full rounded-[10px] border border-line bg-canvas/60 px-3 py-2 text-sm text-ink outline-none focus:border-agent/50" />
              <button onClick={record} disabled={busy}
                className="glow-agent mt-3 inline-flex h-10 items-center gap-2 rounded-[10px] bg-agent px-4 text-sm font-semibold text-black transition-transform hover:scale-[1.02] disabled:opacity-60">
                {busy ? <><Loader2 className="h-4 w-4 animate-spin" /> Recording…</> : <><Send className="h-4 w-4" /> Record handoff</>}
              </button>
            </section>
          </div>

          {/* recent handoffs */}
          <aside className="space-y-3">
            <div className="label">Recent handoffs</div>
            {(list?.handoffs ?? []).map((h) => <HandoffCard key={h.id} h={h} onAck={async () => {
              await api.ackShiftHandoff(h.id); qc.invalidateQueries({ queryKey: ["handoffs"] });
            }} />)}
            {(list?.handoffs ?? []).length === 0 && <p className="text-sm text-ink-mut">No handoffs recorded yet.</p>}
          </aside>
        </div>
      )}
    </div>
  );
}

function SnapshotRow({ s }: { s: MissionSnapshot }) {
  return (
    <li>
      <Link href={`/missions/${s.id}`} className="block rounded-lg border border-line bg-canvas/50 p-3 transition-colors hover:border-line-hi">
        <div className="flex flex-wrap items-center gap-2">
          <StateBadge state={s.state} />
          {s.fault_code && <span className="mono text-xs text-ink-mut">{s.fault_code}</span>}
          <span className="text-sm font-medium text-ink">{s.title}</span>
          {s.reopened_count > 0 && <span className="mono text-[11px] text-warning">reopened ×{s.reopened_count}</span>}
        </div>
        <div className="mt-1 pl-1 text-xs text-ink-mut"><span className="label mr-1.5">Next</span>{s.who_next}</div>
        {s.what_blocks && <div className="pl-1 text-xs text-ink-faint"><span className="label mr-1.5">Blocking</span>{s.what_blocks}</div>}
      </Link>
    </li>
  );
}

function HandoffCard({ h, onAck }: { h: ShiftHandoffView; onAck: () => void }) {
  return (
    <div className="rounded-xl border border-line bg-surface-1 p-4">
      <div className="flex items-center gap-2 text-sm">
        <span className="mono font-semibold text-ink-hi">{h.from_shift || "?"}</span>
        <ArrowRight className="h-3.5 w-3.5 text-ink-faint" />
        <span className="mono font-semibold text-ink-hi">{h.to_shift || "?"}</span>
        <span className="ml-auto flex items-center gap-1 text-[11px] text-ink-faint"><Clock className="h-3 w-3" />{h.created_at?.slice(0, 16).replace("T", " ")}</span>
      </div>
      <p className="mt-1.5 text-sm text-ink">{h.headline}</p>
      {h.notes && <p className="mt-1 text-xs text-ink-mut">“{h.notes}”</p>}
      <div className="mt-1 text-[11px] text-ink-faint">by {h.created_by} · {h.stats.open_missions} open mission(s)</div>
      <div className="mt-2.5">
        {h.acknowledged_by ? (
          <span className="flex items-center gap-1 text-[11px] text-verified"><CheckCircle2 className="h-3.5 w-3.5" /> acknowledged by {h.acknowledged_by}</span>
        ) : (
          <button onClick={onAck} className="inline-flex h-8 items-center gap-1.5 rounded-[10px] border border-agent/40 px-3 text-xs font-semibold text-agent transition-colors hover:bg-agent-soft">
            <CheckCircle2 className="h-3.5 w-3.5" /> Acknowledge
          </button>
        )}
      </div>
    </div>
  );
}
