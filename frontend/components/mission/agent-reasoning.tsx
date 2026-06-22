"use client";

import { useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  Flag,
  GitBranch,
  PencilRuler,
  Radar,
  ScanSearch,
  Waypoints,
} from "lucide-react";
import { useReasoning } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { TONE_CLASS, type Tone } from "@/lib/state-meta";
import { Badge, Chip } from "@/components/forge/primitives";
import { AgentActivityIndicator } from "@/components/forge/badges";
import { EmptyState, ErrorState, LoadingState } from "@/components/forge/states";
import type { ReasoningNode, ReasoningStep, ReasoningView } from "@/lib/types";

const NODE_META: Record<ReasoningNode, { icon: React.ComponentType<{ className?: string }>; tone: Tone }> = {
  perceive: { icon: Radar, tone: "evidence" },
  retrieve: { icon: BookOpen, tone: "evidence" },
  hypothesize: { icon: GitBranch, tone: "agent" },
  draft: { icon: PencilRuler, tone: "agent" },
  self_critique: { icon: ScanSearch, tone: "approval" },
  decide: { icon: Flag, tone: "agent" },
  observe: { icon: Waypoints, tone: "pending" },
  reflect: { icon: AlertTriangle, tone: "failure" },
};

function confidenceTone(c: number): Tone {
  if (c >= 0.95) return "verified";
  if (c >= 0.45) return "agent";
  if (c >= 0.15) return "warning";
  return "failure";
}

function stepTone(step: ReasoningStep): Tone {
  if (step.node === "decide" && (step.confidence ?? 0) >= 0.95) return "verified";
  return NODE_META[step.node]?.tone ?? "steel";
}

export function AgentReasoning({ incidentId }: { incidentId: string }) {
  const { data, isLoading, isError, refetch } = useReasoning(incidentId, 3000);
  if (isLoading) return <LoadingState label="Loading agent reasoning" />;
  if (isError || !data) return <ErrorState message="Agent reasoning unavailable." onRetry={() => refetch()} />;
  if (data.steps.length === 0)
    return (
      <EmptyState
        title="No reasoning yet"
        description="The agent records its reasoning once a Recovery Contract is drafted."
      />
    );

  return (
    <div className="space-y-5">
      <Header data={data} />
      <ConfidenceTrajectory steps={data.steps} />
      <ol className="relative space-y-2" role="list" aria-label="Agent reasoning steps">
        {data.steps.map((s, i) => (
          <ReasoningRow key={s.seq} step={s} last={i === data.steps.length - 1} />
        ))}
      </ol>
      <p className="rounded-lg border border-line bg-surface-1 px-3 py-2 text-xs text-ink-mut">
        <span className="text-ink">The agent proposes; it never decides or acts on its own.</span>{" "}
        {data.note}
      </p>
    </div>
  );
}

function Header({ data }: { data: ReasoningView }) {
  const live = data.confidence != null && data.confidence < 0.95 && data.confidence > 0.05;
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-surface-1 p-4">
      <div>
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-ink-hi">Agent reasoning</h2>
          <AgentActivityIndicator label={live ? "monitoring" : "trace recorded"} active={live} />
        </div>
        <p className="mt-1 text-xs text-ink-mut">
          Bounded neuro-symbolic plan-executor · perceive → retrieve → hypothesize → draft →
          self-critique → decide.
        </p>
      </div>
      <div className="flex items-center gap-2">
        <Chip>{data.step_count} steps</Chip>
        {data.provider && <Chip>{data.provider}</Chip>}
        {data.confidence != null && (
          <Badge tone={confidenceTone(data.confidence)}>
            recovery confidence {Math.round(data.confidence * 100)}%
          </Badge>
        )}
      </div>
    </div>
  );
}

/** A small, accessible sparkline of the agent's calibrated recovery confidence over the trace. */
function ConfidenceTrajectory({ steps }: { steps: ReasoningStep[] }) {
  const pts = steps.filter((s) => s.confidence != null) as (ReasoningStep & { confidence: number })[];
  if (pts.length < 2) return null;

  const W = 720;
  const H = 120;
  const padX = 14;
  const padY = 16;
  const n = pts.length;
  const x = (i: number) => padX + (i * (W - 2 * padX)) / (n - 1);
  const y = (c: number) => padY + (1 - c) * (H - 2 * padY);
  const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.confidence).toFixed(1)}`).join(" ");
  const area = `${line} L${x(n - 1).toFixed(1)},${(H - padY).toFixed(1)} L${x(0).toFixed(1)},${(H - padY).toFixed(1)} Z`;

  const summary = pts.map((p) => `${p.node_label} ${Math.round(p.confidence * 100)}%`).join(", ");

  return (
    <figure className="rounded-lg border border-line bg-surface-1 p-4">
      <figcaption className="label mb-2 flex items-center justify-between">
        <span>Recovery-confidence trajectory</span>
        <span className="mono text-[11px] text-ink-mut">0–100% · cautious by design</span>
      </figcaption>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full"
        role="img"
        aria-label={`Agent recovery confidence across reasoning steps: ${summary}.`}
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="conf-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--agent)" stopOpacity="0.22" />
            <stop offset="100%" stopColor="var(--agent)" stopOpacity="0" />
          </linearGradient>
        </defs>
        {/* gridlines at 25/50/75% */}
        {[0.25, 0.5, 0.75].map((g) => (
          <line
            key={g}
            x1={padX}
            x2={W - padX}
            y1={y(g)}
            y2={y(g)}
            stroke="var(--line)"
            strokeDasharray="3 5"
            strokeWidth="1"
          />
        ))}
        <path d={area} fill="url(#conf-fill)" />
        <path d={line} fill="none" stroke="var(--agent)" strokeWidth="2" strokeLinejoin="round" />
        {pts.map((p, i) => {
          const tone = confidenceTone(p.confidence);
          const stroke =
            tone === "verified" ? "var(--verified)" : tone === "failure" ? "var(--failure)" : "var(--agent)";
          return (
            <g key={p.seq}>
              <circle cx={x(i)} cy={y(p.confidence)} r={p.node === "reflect" ? 5 : 3.5} fill="var(--surface-1)" stroke={stroke} strokeWidth="2" />
              {(p.node === "reflect" || (p.node === "decide" && p.confidence >= 0.95)) && (
                <text x={x(i)} y={y(p.confidence) - 10} textAnchor="middle" className="mono" fontSize="10" fill={stroke}>
                  {Math.round(p.confidence * 100)}%
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </figure>
  );
}

function ReasoningRow({ step, last }: { step: ReasoningStep; last: boolean }) {
  const [open, setOpen] = useState(false);
  const meta = NODE_META[step.node] ?? { icon: Flag, tone: "steel" as Tone };
  const tone = stepTone(step);
  const t = TONE_CLASS[tone];
  const Icon = meta.icon;
  const hasDetail =
    step.citations.length > 0 ||
    Object.keys(step.outputs || {}).length > 0 ||
    Object.keys(step.inputs || {}).length > 0;

  return (
    <li className="relative pl-9">
      {/* connector rail */}
      {!last && <span className="absolute left-[15px] top-8 bottom-[-8px] w-px bg-line" aria-hidden />}
      <span
        className={cn("absolute left-1 top-1.5 grid h-7 w-7 place-items-center rounded-full border", t.bg, t.border)}
        aria-hidden
      >
        <Icon className={cn("h-3.5 w-3.5", t.text)} />
      </span>

      <div className="rounded-lg border border-line bg-surface-1 transition-colors hover:border-line-strong">
        <button
          type="button"
          onClick={() => hasDetail && setOpen((v) => !v)}
          aria-expanded={hasDetail ? open : undefined}
          className={cn(
            "flex w-full items-start gap-3 px-3 py-2.5 text-left",
            hasDetail ? "cursor-pointer" : "cursor-default",
          )}
        >
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className={cn("text-[11px] font-semibold uppercase tracking-wide", t.text)}>
                {step.node_label}
              </span>
              {step.revision > 0 && <Chip>revision {step.revision}</Chip>}
              {step.confidence != null && (
                <Badge tone={confidenceTone(step.confidence)}>{Math.round(step.confidence * 100)}%</Badge>
              )}
            </div>
            <div className="mt-1 text-sm font-medium text-ink">{step.title}</div>
            <p className="mt-0.5 text-xs leading-relaxed text-ink-mut">{step.rationale}</p>
          </div>
          {hasDetail && (
            <ChevronRight
              className={cn("mt-1 h-4 w-4 shrink-0 text-ink-mut transition-transform", open && "rotate-90")}
              aria-hidden
            />
          )}
        </button>

        {open && hasDetail && (
          <div className="animate-fade-up space-y-3 border-t border-line px-3 py-3">
            {step.citations.length > 0 && (
              <div>
                <div className="label mb-1.5">Sources cited</div>
                <div className="space-y-1.5">
                  {step.citations.map((c, i) => (
                    <div key={i} className="rounded-md border border-line bg-surface-2 p-2 text-xs">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <Chip>{c.document_id}</Chip>
                        {c.section && <span className="text-ink-mut">§ {c.section}</span>}
                        {c.revision && <Chip>rev {c.revision}</Chip>}
                        {c.approval_status && (
                          <Badge tone={c.approval_status === "APPROVED" ? "verified" : "warning"}>
                            {c.approval_status.toLowerCase()}
                          </Badge>
                        )}
                      </div>
                      {c.excerpt && <p className="mt-1 text-ink-mut">“{c.excerpt}”</p>}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {Object.keys(step.outputs || {}).length > 0 && (
              <KeyValues title="Outputs" data={step.outputs} />
            )}
            {Object.keys(step.inputs || {}).length > 0 && (
              <KeyValues title="Inputs" data={step.inputs} />
            )}
            <div className="flex flex-wrap items-center gap-2 pt-0.5">
              {step.model_version && <Chip>{step.model_version}</Chip>}
              {step.prompt_version && <Chip>prompt {step.prompt_version}</Chip>}
            </div>
          </div>
        )}
      </div>
    </li>
  );
}

function KeyValues({ title, data }: { title: string; data: Record<string, unknown> }) {
  return (
    <div>
      <div className="label mb-1.5">{title}</div>
      <pre className="mono overflow-x-auto rounded-md border border-line bg-surface-2 p-2 text-[11px] leading-relaxed text-ink-mut">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}
