"use client";

import { useRouter } from "next/navigation";
import { BellRing, Cpu } from "lucide-react";
import { useAlerts, useTriageAlert } from "@/lib/hooks";
import { Badge, Button, Chip } from "@/components/forge/primitives";
import { SeverityIndicator } from "@/components/forge/badges";
import { EmptyState, ErrorState, LoadingState } from "@/components/forge/states";
import type { MaiaAlert } from "@/lib/types";

export default function AlertsPage() {
  const { data, isLoading, isError, refetch } = useAlerts(6000);

  if (isLoading) return <LoadingState label="Loading MAIA alerts" />;
  if (isError || !data) return <div className="p-6"><ErrorState message="Alerts unavailable." onRetry={() => refetch()} /></div>;

  return (
    <div className="mx-auto max-w-3xl px-6 py-7">
      <div className="flex items-center gap-2">
        <BellRing className="h-5 w-5 text-warning" aria-hidden />
        <h1 className="text-2xl font-semibold tracking-tight text-ink-hi">MAIA Alerts</h1>
      </div>
      <p className="mt-1 text-sm text-ink-mut">
        Inbound alerts from the host MES agent. The Verified Recovery Agent triages an alert, ranks the
        likely causes, and proposes an intervention for a human to accept — it never controls a machine.
      </p>

      {data.alerts.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            title="No open alerts"
            description="When MAIA raises a fault, bottleneck, or anomaly, it appears here for the agent to triage."
          />
        </div>
      ) : (
        <ul className="mt-6 space-y-3">
          {data.alerts.map((a) => (
            <AlertCard key={a.id} alert={a} />
          ))}
        </ul>
      )}
    </div>
  );
}

function AlertCard({ alert }: { alert: MaiaAlert }) {
  const router = useRouter();
  const triage = useTriageAlert();

  const onTriage = () =>
    triage.mutate(alert.id, {
      onSuccess: (r) => router.push(`/missions/${r.incident_id}?tab=diagnosis`),
    });

  return (
    <li className="rounded-xl border border-line bg-surface-1 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="evidence">
          <Cpu className="h-3 w-3" aria-hidden /> {alert.source}
        </Badge>
        <Chip>{alert.id}</Chip>
        <Chip>{alert.kind.replace(/_/g, " ")}</Chip>
        {alert.fault_code && <Chip>{alert.fault_code}</Chip>}
        <SeverityIndicator severity={alert.severity} />
        {alert.resulted_in_incident && <Badge tone="agent">triaged → {alert.resulted_in_incident}</Badge>}
      </div>

      <p className="mt-2 text-sm text-ink">{alert.message}</p>

      <div className="mt-2 flex flex-wrap gap-1.5">
        {Object.entries(alert.signals).slice(0, 8).map(([k, v]) => (
          <Chip key={k}>
            {k.replace(/_/g, " ")}: {String(v)}
          </Chip>
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between gap-3">
        <span className="text-xs text-ink-mut">
          {alert.machine_id}
          {alert.order_id ? ` · ${alert.order_id}` : ""}
        </span>
        <Button variant="agent" onClick={onTriage} disabled={triage.isPending}>
          {triage.isPending ? "Triaging…" : "Triage with agent"}
        </Button>
      </div>
      {triage.isError && (
        <p className="mt-2 text-xs text-failure">Triage failed. Please retry.</p>
      )}
    </li>
  );
}
