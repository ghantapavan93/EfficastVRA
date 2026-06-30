"use client";

import { AlertTriangle, CheckCircle2, Gavel, MinusCircle, ShieldCheck, XCircle } from "lucide-react";
import { useReleaseMatrix } from "@/lib/hooks";
import { Badge } from "@/components/forge/primitives";
import type { Tone } from "@/lib/state-meta";
import type { ReleaseDomain } from "@/lib/types";

const TONE: Record<string, Tone> = {
  pass: "verified", blocked: "failure", insufficient: "warning", monitoring: "steel", warn: "pending",
};

function DomainIcon({ status }: { status: string }) {
  if (status === "pass") return <CheckCircle2 className="h-4 w-4 text-verified" aria-hidden />;
  if (status === "blocked") return <XCircle className="h-4 w-4 text-failure" aria-hidden />;
  if (status === "insufficient" || status === "warn") return <AlertTriangle className="h-4 w-4 text-warning" aria-hidden />;
  return <MinusCircle className="h-4 w-4 text-ink-mut" aria-hidden />;
}

export function DecisionRoom({ incidentId }: { incidentId: string }) {
  const { data } = useReleaseMatrix(incidentId, 4000);
  if (!data) return null;
  if (!data.available) {
    return <section className="rounded-xl border border-line bg-surface-1 p-6 text-sm text-ink-mut">{data.reason ?? "The Decision Room opens once a Recovery Contract exists."}</section>;
  }
  const authorized = data.outcome === "VERIFIED";

  return (
    <section className="space-y-4">
      <div className="alive rounded-2xl border border-line-strong bg-surface-1 p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Gavel className="h-4 w-4 text-agent" aria-hidden />
            <h3 className="text-sm font-semibold text-ink-hi">Decision Room</h3>
            <span className="text-[12px] text-ink-mut">release decision · advisory</span>
          </div>
          <Badge tone={authorized ? "verified" : data.outcome === "FAILED" ? "failure" : "warning"}>
            {authorized ? <ShieldCheck className="h-3 w-3" aria-hidden /> : <AlertTriangle className="h-3 w-3" aria-hidden />}
            {(data.outcome ?? "").replace(/_/g, " ")}
          </Badge>
        </div>
        <p className="mt-2 text-sm text-ink">{data.headline}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-[12px]">
          <Badge tone={data.can_close ? "verified" : "steel"}>{data.can_close ? "release authorized" : "release blocked"}</Badge>
          {data.blocking_count != null && data.blocking_count > 0 && <Badge tone="failure">{data.blocking_count} blocking</Badge>}
          {data.effective_confidence != null && <span className="mono text-ink-mut">effective confidence {Math.round((data.effective_confidence ?? 0) * 100)}%</span>}
        </div>
      </div>

      <div className="rounded-2xl border border-line bg-surface-1 p-5">
        <div className="label mb-2">Release domains — every domain must pass</div>
        <div className="space-y-1">
          {(data.domains ?? []).map((d: ReleaseDomain) => (
            <div key={d.domain} className="flex items-start gap-3 border-t border-line/60 py-2 first:border-t-0">
              <DomainIcon status={d.status} />
              <span className="w-32 shrink-0 text-sm text-ink">{d.domain}</span>
              <Badge tone={TONE[d.status] ?? "steel"}>{d.result}</Badge>
              <span className="ml-auto max-w-[46%] text-right text-[12px] text-ink-mut">
                {d.status === "pass" ? d.detail : d.blocking_issue}
              </span>
            </div>
          ))}
        </div>
      </div>

      {data.reasons && data.reasons.length > 0 && (
        <div className="rounded-xl border border-line bg-surface-1 p-4">
          <div className="label mb-1.5">Why this outcome</div>
          <ul className="space-y-1 text-[12px] text-ink-mut">
            {data.reasons.map((r, i) => <li key={i}>· {r}</li>)}
          </ul>
        </div>
      )}
      {data.basis && <p className="px-1 text-[11px] text-ink-mut">{data.basis}</p>}
    </section>
  );
}
