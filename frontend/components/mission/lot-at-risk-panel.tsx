"use client";

import { CheckCircle2, PackageX } from "lucide-react";
import { useLotAtRisk } from "@/lib/hooks";
import { Badge, Chip } from "@/components/forge/primitives";

const fmt = (iso?: string | null) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }); }
  catch { return iso; }
};

export function LotAtRiskPanel({ incidentId }: { incidentId: string }) {
  const { data } = useLotAtRisk(incidentId, 4000);
  if (!data || !data.available) return null;

  if (!data.at_risk) {
    return (
      <section className="rounded-xl border border-line bg-surface-1 p-5">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-verified" aria-hidden />
          <h3 className="text-sm font-semibold text-ink-hi">Lot-at-risk</h3>
          <Badge tone="verified">None at risk</Badge>
        </div>
        <p className="mt-2 text-sm text-ink-mut">{data.summary}</p>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div className="rounded-xl border border-line bg-surface-1 p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <PackageX className="h-4 w-4 text-agent" aria-hidden />
            <h3 className="text-sm font-semibold text-ink-hi">Lot-at-risk</h3>
            <span className="text-[12px] text-ink-mut">product-quality · advisory</span>
          </div>
          <Badge tone="warning">Lots at risk</Badge>
        </div>

        <div className="mt-3 grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
          <Field label="Last known-good cycle">{data.last_good_cycle ?? "—"}</Field>
          <Field label="First questionable cycle">{data.first_questionable_cycle ?? "—"} ({data.fault_code})</Field>
          <Field label="Affected from">{fmt(data.affected_window?.from)}</Field>
          <Field label="Affected to">{fmt(data.affected_window?.to)}</Field>
          <Field label="Affected lots">{data.affected_lot_count ?? 0}</Field>
          <Field label="Dispositions">{(data.current_dispositions ?? []).join(", ") || "—"}</Field>
        </div>

        {data.affected_lots && data.affected_lots.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {data.affected_lots.map((l) => <Chip key={l.id}>{l.id} · {l.disposition}</Chip>)}
          </div>
        )}

        <div className="mt-3 rounded-lg border border-warning/40 bg-warning-soft p-3 text-sm text-ink">
          {data.required_quality_action}
        </div>
        {data.affected_quantity_note && <p className="mt-2 text-[11px] text-ink-mut">{data.affected_quantity_note}</p>}
        {data.basis && <p className="mt-1 text-[11px] text-ink-mut">{data.basis}</p>}
      </div>
    </section>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-line/60 pb-1">
      <span className="label">{label}</span>
      <span className="text-right text-ink">{children}</span>
    </div>
  );
}
