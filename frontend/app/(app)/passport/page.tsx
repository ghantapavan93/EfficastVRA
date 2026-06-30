"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, BookMarked, CheckCircle2, FileUp, RefreshCw, ShieldCheck } from "lucide-react";
import { useAssets, usePassport } from "@/lib/hooks";
import { StateBadge } from "@/components/forge/badges";
import { Chip } from "@/components/forge/primitives";
import { ErrorState, LoadingState } from "@/components/forge/states";
import type { PassportEntry } from "@/lib/types";

export default function PassportPage() {
  const { data: assetData, isLoading } = useAssets(15000);
  const [sel, setSel] = useState<string | null>(null);
  const assets = assetData?.assets ?? [];

  useEffect(() => {
    const first = assetData?.assets?.[0]?.id;
    if (!sel && first) setSel(first);
  }, [assetData, sel]);

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <header className="mb-6">
        <div className="label mb-1 flex items-center gap-1.5"><BookMarked className="h-3.5 w-3.5 text-agent" /> Recovery Passport</div>
        <h1 className="text-2xl font-semibold text-ink-hi">An asset&apos;s verified-recovery history</h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-mut">
          Every incident is a moment; the Passport is the asset&apos;s memory — how often recovery actually held,
          and how many times a closed work order would have been wrong.
        </p>
      </header>

      {isLoading ? (
        <LoadingState label="Loading assets" />
      ) : (
        <>
          {/* asset picker */}
          <div className="mb-6 flex gap-3 overflow-x-auto pb-2">
            {assets.map((a) => (
              <button key={a.id} onClick={() => setSel(a.id)}
                className={`shrink-0 rounded-xl border px-4 py-3 text-left transition-colors ${sel === a.id ? "border-agent/60 bg-agent-soft" : "border-line bg-surface-1 hover:border-line-hi"}`}>
                <div className="mono text-sm font-semibold text-ink-hi">{a.code}</div>
                <div className="max-w-[12rem] truncate text-xs text-ink-mut">{a.name}</div>
                <div className="mt-1.5 flex items-center gap-2 text-[11px]">
                  <span className="text-ink-mut">{a.mission_count} mission{a.mission_count === 1 ? "" : "s"}</span>
                  {a.false_closures_caught > 0 && (
                    <span className="flex items-center gap-1 text-warning"><AlertTriangle className="h-3 w-3" /> {a.false_closures_caught}</span>
                  )}
                </div>
              </button>
            ))}
          </div>

          {sel && <Passport machineId={sel} />}
        </>
      )}
    </div>
  );
}

function Passport({ machineId }: { machineId: string }) {
  const { data: p, isLoading, isError, refetch } = usePassport(machineId, 15000);
  if (isLoading) return <LoadingState label="Loading passport" />;
  if (isError || !p?.available) return <ErrorState message="Could not load this asset's passport." onRetry={() => refetch()} />;

  const s = p.stats;
  return (
    <div className="space-y-5">
      {/* machine header */}
      <section className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-surface-1 p-5">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="mono text-lg font-semibold text-ink-hi">{p.machine.code}</h2>
            <Chip>{p.machine.state.toLowerCase()}</Chip>
          </div>
          <p className="text-sm text-ink-mut">{p.machine.name} · {p.machine.machine_model || "—"} {p.machine.manufacturer ? `· ${p.machine.manufacturer}` : ""}</p>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-ink-faint"><RefreshCw className="h-3 w-3" /> live</div>
      </section>

      {/* stats */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Big label="False closures caught" value={s.false_closures_caught} tone="warning" icon={ShieldCheck}
          hint="times a closed work order would have been wrong" />
        <Big label="Verified rate" value={`${s.verified_rate}%`} tone="verified" icon={CheckCircle2}
          hint={`${s.verified} of ${s.total_missions} missions`} />
        <Big label="Reopens (total)" value={s.reopens_total} tone="default"
          hint={`${s.reopened_missions} mission(s) reopened`} />
        <Big label="Mean time to outcome" value={s.mean_time_to_outcome_hours != null ? `${s.mean_time_to_outcome_hours}h` : "—"} tone="default"
          hint={`${s.active_missions} active now`} />
      </div>

      {/* history */}
      <section className="rounded-xl border border-line bg-surface-1 p-5">
        <div className="label mb-3">Recovery history · {p.entries.length} mission{p.entries.length === 1 ? "" : "s"}</div>
        <ol className="space-y-2">
          {p.entries.map((e) => <HistoryRow key={e.id} e={e} />)}
          {p.entries.length === 0 && <li className="text-sm text-ink-mut">No recovery missions recorded for this asset yet.</li>}
        </ol>
        <p className="mono mt-4 text-[11px] text-ink-faint">{p.basis}</p>
      </section>
    </div>
  );
}

function HistoryRow({ e }: { e: PassportEntry }) {
  return (
    <li>
      <Link href={`/missions/${e.id}`}
        className="block rounded-lg border border-line bg-canvas/50 p-3 transition-colors hover:border-line-hi">
        <div className="flex flex-wrap items-center gap-2">
          <StateBadge state={e.state} />
          {e.fault_code && <span className="mono text-xs text-ink-mut">{e.fault_code}</span>}
          <span className="text-sm font-medium text-ink">{e.title}</span>
          {e.from_upload && <Chip><FileUp className="mr-1 inline h-3 w-3" />uploaded</Chip>}
          {e.false_closure_caught && (
            <span className="flex items-center gap-1 rounded-pill bg-warning/15 px-2 py-0.5 text-[11px] text-warning">
              <AlertTriangle className="h-3 w-3" /> false closure caught
            </span>
          )}
          {e.reopened_count > 0 && <span className="mono text-[11px] text-ink-mut">reopened ×{e.reopened_count}</span>}
        </div>
        {e.outcome_summary && <p className="mt-1 pl-1 text-xs text-ink-mut">{e.outcome_summary}</p>}
        <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5 pl-1 text-[11px] text-ink-faint">
          {e.opened_at && <span>opened {e.opened_at.slice(0, 10)}</span>}
          {e.closed_at && <span>closed {e.closed_at.slice(0, 10)}</span>}
          {e.duration_hours != null && <span className="mono">{e.duration_hours}h to outcome</span>}
        </div>
      </Link>
    </li>
  );
}

function Big({ label, value, tone, hint, icon: Icon }: {
  label: string; value: string | number; tone: "warning" | "verified" | "default"; hint?: string;
  icon?: typeof ShieldCheck;
}) {
  const color = tone === "warning" ? "text-warning" : tone === "verified" ? "text-verified" : "text-ink-hi";
  return (
    <div className="rounded-xl border border-line bg-surface-1 p-4">
      <div className="label mb-1 flex items-center gap-1.5">{Icon && <Icon className="h-3.5 w-3.5" />}{label}</div>
      <div className={`mono text-3xl font-semibold ${color}`}>{value}</div>
      {hint && <div className="mt-1 text-[11px] text-ink-faint">{hint}</div>}
    </div>
  );
}
