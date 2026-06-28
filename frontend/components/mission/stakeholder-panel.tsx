"use client";

import { MessageSquare, Users } from "lucide-react";
import { useMaiaMessages, useStakeholderView } from "@/lib/hooks";
import { Badge, Chip } from "@/components/forge/primitives";
import type { Tone } from "@/lib/state-meta";

const SEV: Record<string, Tone> = { INFO: "steel", WARNING: "warning", CRITICAL: "failure" };

export function StakeholderPanel({ incidentId }: { incidentId: string }) {
  const { data: view } = useStakeholderView();
  const { data: maia } = useMaiaMessages(incidentId, 4000);
  if (!view) return null;

  return (
    <section className="space-y-4">
      {/* role-specific view */}
      <div className="rounded-xl border border-line bg-surface-1 p-5">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-agent" aria-hidden />
          <h3 className="text-sm font-semibold text-ink-hi">Your view — {view.label ?? view.persona}</h3>
          <span className="text-[12px] text-ink-mut">role-specific · advisory</span>
        </div>
        {view.focus && <p className="mt-2 text-sm text-ink">{view.focus}</p>}
        <div className="mt-3 space-y-2 text-sm">
          <Row label="Relevant views">{(view.tabs ?? []).map((t) => <Chip key={t}>{t.replace(/-/g, " ")}</Chip>)}</Row>
          <Row label="You can do">{(view.can_act ?? []).length ? (view.can_act ?? []).map((a) => <Chip key={a}>{a}</Chip>) : <span className="text-ink-mut">—</span>}</Row>
          <Row label="You can approve">{(view.can_approve ?? []).length ? (view.can_approve ?? []).map((a) => <Chip key={a}>{a.replace(/_/g, " ")}</Chip>) : <span className="text-ink-mut">—</span>}</Row>
        </div>
        <p className="mt-3 text-[11px] text-ink-mut">
          Presentation only — the Agent Action Gateway still enforces what each role may actually do.
        </p>
      </div>

      {/* applicable MAIA / WhatsApp message(s) */}
      <div className="rounded-xl border border-line bg-surface-1 p-5">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-agent" aria-hidden />
          <h3 className="text-sm font-semibold text-ink-hi">MAIA message</h3>
          <span className="text-[12px] text-ink-mut">communication surface only — deep-links, never tool execution</span>
        </div>
        <div className="mt-3 space-y-2">
          {(maia?.messages ?? []).map((m, i) => (
            <div key={i} className="rounded-lg border border-line bg-surface-2 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium text-ink">{m.title}</span>
                <Badge tone={SEV[m.severity] ?? "steel"}>{m.severity.toLowerCase()}</Badge>
              </div>
              <p className="mt-1 text-sm text-ink-mut">{m.body}</p>
              {m.actions.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {m.actions.map((a, j) => (
                    <a key={j} href={a.deep_link} className="inline-flex items-center rounded-[8px] border border-line-strong px-2 py-1 text-[12px] text-ink hover:bg-surface-3">
                      {a.label} <span className="mono ml-1.5 text-[10px] text-ink-mut">{a.deep_link}</span>
                    </a>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-baseline gap-2">
      <span className="label w-28 shrink-0">{label}</span>
      <span className="flex flex-wrap gap-1.5">{children}</span>
    </div>
  );
}
