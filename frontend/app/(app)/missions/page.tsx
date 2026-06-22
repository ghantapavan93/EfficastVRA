"use client";

import { useMemo } from "react";
import { useMissions } from "@/lib/hooks";
import { STATE_GROUP_LABEL } from "@/lib/state-meta";
import type { MissionSummary } from "@/lib/types";
import { ErrorState, LoadingState, Skeleton } from "@/components/forge/states";
import { MissionCard } from "@/components/mission/mission-card";

const GROUP_ORDER = ["reopened", "requires_decision", "monitoring", "awaiting_evidence", "escalated", "verified"];

export default function MissionControlPage() {
  const { data, isLoading, isError, refetch } = useMissions(4000);

  const { primary, grouped } = useMemo(() => {
    const missions = data?.missions ?? [];
    const primary = missions.find((m) => m.is_active) ?? null;
    const rest = missions.filter((m) => m.id !== primary?.id);
    const grouped: Record<string, MissionSummary[]> = {};
    for (const m of rest) (grouped[m.state_group] ??= []).push(m);
    return { primary, grouped };
  }, [data]);

  return (
    <div className="mx-auto max-w-5xl px-6 py-7">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink-hi">Mission Control</h1>
          <p className="mt-1 text-sm text-ink-mut">
            Post-intervention recovery verification — prioritized by what needs a decision now.
          </p>
        </div>
        {data && (
          <div className="mono text-xs text-ink-mut">
            {data.missions.filter((m) => m.is_active).length} active · {data.missions.length} total
          </div>
        )}
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
                  <MissionCard key={m.id} m={m} />
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
