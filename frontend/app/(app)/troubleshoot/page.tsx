"use client";

import { useState } from "react";
import { AlertTriangle, BookOpen, GitBranch, History, Lightbulb, Radar, Search, Wrench } from "lucide-react";
import { useTroubleshoot } from "@/lib/hooks";
import { Badge, Button, Chip } from "@/components/forge/primitives";
import { EmptyState, ErrorState, LoadingState } from "@/components/forge/states";
import type { TroubleshootResult } from "@/lib/types";

const MODELS = ["CDX-220", "IMX-90", "IMX-160", "HPU-50"];

export default function TroubleshootPage() {
  const [fault, setFault] = useState("F27");
  const [model, setModel] = useState("CDX-220");
  const [text, setText] = useState("");
  const [params, setParams] = useState<{ fault_code?: string; machine_model?: string; q?: string }>({
    fault_code: "F27",
    machine_model: "CDX-220",
  });
  const { data, isLoading, isError, refetch, isFetching } = useTroubleshoot(params);

  const find = () =>
    setParams({ fault_code: fault.trim() || undefined, machine_model: model.trim() || undefined, q: text.trim() || undefined });

  return (
    <div className="mx-auto max-w-3xl px-6 py-7">
      <div className="flex items-center gap-2">
        <Wrench className="h-5 w-5 text-agent" aria-hidden />
        <h1 className="text-2xl font-semibold tracking-tight text-ink-hi">Troubleshoot</h1>
      </div>
      <p className="mt-1 text-sm text-ink-mut">
        Find the fix fast — grounded in approved procedures, what actually worked before, and the
        signals to check. Every line is sourced and approval-checked. Not a chatbot.
      </p>

      {/* search */}
      <div className="mt-5 grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
        <label className="block">
          <span className="label">Fault code</span>
          <input
            value={fault}
            onChange={(e) => setFault(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && find()}
            placeholder="e.g. F27"
            className="mono mt-1 w-full rounded-lg border border-line bg-surface-1 px-3 py-2 text-sm text-ink outline-none focus:border-agent"
          />
        </label>
        <label className="block">
          <span className="label">Machine model</span>
          <input
            value={model}
            onChange={(e) => setModel(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && find()}
            list="models"
            placeholder="e.g. CDX-220"
            className="mono mt-1 w-full rounded-lg border border-line bg-surface-1 px-3 py-2 text-sm text-ink outline-none focus:border-agent"
          />
          <datalist id="models">{MODELS.map((m) => <option key={m} value={m} />)}</datalist>
        </label>
        <div className="flex items-end">
          <Button variant="agent" onClick={find} className="w-full sm:w-auto">
            <Search className="h-4 w-4" aria-hidden /> Find
          </Button>
        </div>
      </div>
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && find()}
        placeholder="Optional: describe the symptom (e.g. 'vibration rising, short stops')"
        className="mt-2 w-full rounded-lg border border-line bg-surface-1 px-3 py-2 text-sm text-ink outline-none focus:border-agent"
      />

      <div className="mt-6">
        {isLoading || isFetching ? (
          <LoadingState label="Finding the grounded answer" />
        ) : isError ? (
          <ErrorState message="Lookup failed." onRetry={() => refetch()} />
        ) : !data ? (
          <EmptyState title="Enter a fault or machine" description="Get the approved procedure, likely causes, history, and signals — without hunting through manuals." icon={Search} />
        ) : (
          <Result data={data} />
        )}
      </div>
    </div>
  );
}

function Result({ data }: { data: TroubleshootResult }) {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-line bg-surface-1 p-4">
        <div className="flex flex-wrap items-center gap-2">
          {data.query.fault_code && <Chip>{data.query.fault_code}</Chip>}
          {data.machine?.label && <Badge tone="agent">{data.machine.label}</Badge>}
          {data.machine?.equipment_class && <Chip>{data.machine.equipment_class.replace(/_/g, " ")}</Chip>}
        </div>
        <p className="mt-2 text-sm text-ink">{data.summary}</p>
      </div>

      {data.early_warning && (
        <div className="rounded-xl border border-warning/40 bg-warning-soft p-4">
          <div className="label mb-1 flex items-center gap-1.5 text-warning"><Radar className="h-3.5 w-3.5" aria-hidden /> Early warning</div>
          <p className="text-sm text-ink">{data.early_warning}</p>
        </div>
      )}

      <Section icon={GitBranch} title="Likely causes (ranked)">
        <ol className="space-y-2">
          {data.likely_causes.map((c, i) => (
            <li key={i} className="rounded-lg border border-line bg-surface-2 p-3">
              <div className="flex items-start justify-between gap-2">
                <span className="text-sm text-ink">{c.cause}</span>
                <Chip>{c.likelihood}</Chip>
              </div>
              {c.basis && <p className="mt-1 text-xs text-ink-mut">{c.basis}</p>}
            </li>
          ))}
        </ol>
      </Section>

      <Section icon={BookOpen} title="Approved procedure">
        {data.approved_procedures.length === 0 ? (
          <p className="text-xs text-ink-mut">No approved procedure matched.</p>
        ) : (
          <div className="space-y-2">
            {data.approved_procedures.map((p, i) => (
              <div key={i} className="rounded-lg border border-line bg-surface-2 p-3 text-xs">
                <div className="flex flex-wrap items-center gap-1.5">
                  <Chip>{p.document_id}</Chip>
                  {p.section && <span className="text-ink-mut">§ {p.section}</span>}
                  {p.revision && <Chip>rev {p.revision}</Chip>}
                  <Badge tone="verified">{(p.approval_status || "").toLowerCase()}</Badge>
                </div>
                {p.excerpt && <p className="mt-1.5 text-ink">“{p.excerpt}”</p>}
              </div>
            ))}
          </div>
        )}
      </Section>

      {data.signals_to_check.length > 0 && (
        <Section icon={Radar} title="Signals to check">
          <div className="grid gap-1.5 sm:grid-cols-2">
            {data.signals_to_check.map((s) => (
              <div key={s.key} className="flex items-center justify-between rounded-md border border-line bg-surface-2 px-3 py-1.5 text-xs">
                <span className="text-ink">{s.label}</span>
                <span className="mono text-ink-mut">{s.op.replace(/_/g, " ")} {s.threshold ?? ""} {s.unit}</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      <Section icon={History} title="What worked before">
        {data.history.length === 0 ? (
          <p className="text-xs text-ink-mut">No comparable past incident on record.</p>
        ) : (
          <div className="space-y-2">
            {data.history.map((h) => (
              <div key={h.incident_id} className="rounded-lg border border-line bg-surface-2 p-3 text-xs">
                <div className="flex items-center gap-1.5">
                  <Chip>{h.incident_id}</Chip>
                  {h.outcome && <Badge tone="verified">{h.outcome.toLowerCase()}</Badge>}
                </div>
                <p className="mt-1.5 text-ink">{h.summary}</p>
              </div>
            ))}
          </div>
        )}
      </Section>

      {data.knowledge.length > 0 && (
        <Section icon={Lightbulb} title="Captured lessons">
          <div className="space-y-2">
            {data.knowledge.map((k, i) => (
              <div key={i} className="rounded-lg border border-line bg-surface-2 p-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-ink">{k.title}</span>
                  {k.pending_review && <Badge tone="pending">candidate · pending review</Badge>}
                </div>
                <p className="mt-1 text-ink-mut">{k.lesson}</p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {data.cautions.length > 0 && (
        <Section icon={AlertTriangle} title="Cautions — not authoritative">
          <div className="space-y-2">
            {data.cautions.map((c, i) => (
              <div key={i} className="rounded-lg border border-warning/40 bg-warning-soft p-3 text-xs">
                <div className="flex flex-wrap items-center gap-1.5">
                  <Chip>{c.document_id}</Chip>
                  {c.approval_status && <Badge tone="warning">{c.approval_status.toLowerCase()}</Badge>}
                  {c.reason && <span className="text-warning">{c.reason}</span>}
                </div>
                {c.excerpt && <p className="mt-1 text-ink-mut">“{c.excerpt}”</p>}
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}

function Section({ icon: Icon, title, children }: { icon: React.ComponentType<{ className?: string }>; title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-line bg-surface-1 p-4">
      <div className="label mb-2 flex items-center gap-1.5"><Icon className="h-3.5 w-3.5 text-ink-mut" aria-hidden /> {title}</div>
      {children}
    </section>
  );
}
