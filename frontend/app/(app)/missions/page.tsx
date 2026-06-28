"use client";

import { useMemo } from "react";
import { useMissions } from "@/lib/hooks";
import { STATE_GROUP_LABEL } from "@/lib/state-meta";
import type { MissionSummary } from "@/lib/types";
import { ErrorState, LoadingState, Skeleton } from "@/components/forge/states";
import { MissionCard } from "@/components/mission/mission-card";
import { CountUp } from "@/components/forge/count-up";

const GROUP_ORDER = ["reopened", "requires_decision", "monitoring", "awaiting_evidence", "escalated", "verified"];
const SIG: Record<string, string> = { agent: "var(--agent)", verified: "var(--verified)", failure: "var(--failure)", brand: "var(--brand)" };

export default function MissionControlPage() {
  const { data, isLoading, isError, refetch } = useMissions(4000);

  const { primary, grouped, stats } = useMemo(() => {
    const missions = data?.missions ?? [];
    const primary = missions.find((m) => m.is_active) ?? null;
    const rest = missions.filter((m) => m.id !== primary?.id);
    const grouped: Record<string, MissionSummary[]> = {};
    for (const m of rest) (grouped[m.state_group] ??= []).push(m);
    const stats = {
      total: missions.length,
      active: missions.filter((m) => m.is_active).length,
      verified: missions.filter((m) => m.state === "VERIFIED_RECOVERY").length,
      reopened: missions.filter((m) => m.reopened_count > 0).length,
    };
    return { primary, grouped, stats };
  }, [data]);

  let order = 0; // running stagger index across all cards

  return (
    <div className="mx-auto max-w-5xl px-6 py-7">
      {/* fleet HUD header */}
      <div className="relative mb-6 overflow-hidden rounded-2xl border border-line-strong app-canvas grid-motif p-5"
           style={{ animation: "tab-in .5s ease-out both" }}>
        <div className="relative flex flex-wrap items-end justify-between gap-5">
          <div>
            <div className="label flex items-center gap-2">
              <span className="relative flex h-2 w-2" aria-hidden>
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-verified opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-verified" />
              </span>
              Mission control · live
            </div>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-grad">Recovery fleet</h1>
            <p className="mt-1 max-w-md text-sm text-ink-mut">
              Post-intervention recovery verification — prioritized by what needs a decision now.
            </p>
          </div>
          {data && (
            <div className="grid grid-cols-4 gap-2">
              <FleetStat label="Total" value={stats.total} sig="agent" />
              <FleetStat label="Active" value={stats.active} sig="agent" />
              <FleetStat label="Verified" value={stats.verified} sig="verified" />
              <FleetStat label="Reopened" value={stats.reopened} sig="failure" />
            </div>
          )}
        </div>
      </div>

      {isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      )}
      {isError && <ErrorState message="Could not reach the recovery backend." onRetry={() => refetch()} />}

      {data && (
        <div className="space-y-7">
          {primary && (
            <section aria-label="Active mission">
              <div className="label mb-2">Active mission</div>
              <MissionCard m={primary} prominent />
            </section>
          )}

          {GROUP_ORDER.filter((g) => grouped[g]?.length).map((g) => (
            <section key={g} aria-label={STATE_GROUP_LABEL[g]}>
              <div className="label mb-2">{STATE_GROUP_LABEL[g] ?? g}</div>
              <div className="space-y-2">
                {grouped[g].map((m) => (
                  <CardRise key={m.id} i={order++}>
                    <MissionCard m={m} />
                  </CardRise>
                ))}
              </div>
            </section>
          ))}

          {!primary && Object.keys(grouped).length === 0 && !isLoading && (
            <LoadingState label="Waiting for missions" />
          )}
        </div>
      )}
    </div>
  );
}

function FleetStat({ label, value, sig }: { label: string; value: number; sig: string }) {
  return (
    <div className="card relative min-w-[78px] overflow-hidden px-3 py-2">
      <div aria-hidden className="absolute inset-x-0 top-0 h-px" style={{ background: `linear-gradient(90deg, transparent, ${SIG[sig]}, transparent)` }} />
      <div className="flex items-center gap-1.5">
        <span className="h-1.5 w-1.5 rounded-full" style={{ background: SIG[sig], boxShadow: `0 0 8px ${SIG[sig]}` }} />
        <span className="label">{label}</span>
      </div>
      <div className="mono mt-0.5 text-2xl font-semibold text-ink-hi"><CountUp value={value} /></div>
    </div>
  );
}

function CardRise({ i, children }: { i: number; children: React.ReactNode }) {
  return (
    <div style={{ animation: "tab-in .45s cubic-bezier(.22,1,.36,1) both", animationDelay: `${Math.min(i * 55, 650)}ms` }}>
      {children}
    </div>
  );
}
