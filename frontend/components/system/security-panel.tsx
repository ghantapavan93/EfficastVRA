"use client";

import { useQuery } from "@tanstack/react-query";
import { ShieldCheck, ShieldAlert, Activity, KeyRound, Gauge } from "lucide-react";
import { Badge, SectionLabel } from "@/components/forge/primitives";
import { CountUp } from "@/components/forge/count-up";

interface SecEvent {
  kind: string;
  severity: string;
  actor: string;
  route: string;
  reason: string;
  at: string;
}
interface SecurityPosture {
  headers: { enabled: boolean; applied: string[]; content_security_policy: string; hsts: string };
  rate_limiting: { enabled: boolean; scope: string; limit: number; window_s: number; tracked_identities: number; throttled: number; note: string };
  request_guard: { max_body_bytes: number; rejected_oversized: number };
  audit_signing: { hash_chain: string; keyed_signing: string; active: boolean; live_integrity: { checked: boolean; intact?: boolean; entries?: number } };
  gateway: { single_choke_point: string; pipeline: string; prohibited_actions: string[]; action_classes: string[] };
  detection: { total_events: number; by_kind: Record<string, number>; recent: SecEvent[]; sink: string };
  control_alignment: { framework: string; control: string; implemented_by: string }[];
  control_checks: { control: string; status: string; detail?: string }[];
  honest_gaps: string[];
}

function useSecurity() {
  return useQuery({
    queryKey: ["security"],
    queryFn: async () => {
      const r = await fetch("/api/security", { cache: "no-store", headers: { "X-VRA-User": "s.vega" } });
      return r.json() as Promise<SecurityPosture>;
    },
    refetchInterval: 8000,
  });
}

const sevTone = (s: string) => (s === "critical" ? "failure" : s === "warning" ? "pending" : "steel");

export function SecurityPanel() {
  const { data } = useSecurity();
  if (!data) return null;
  const integ = data.audit_signing.live_integrity;
  const auditOk = !integ.checked || integ.intact;

  return (
    <section className="alive mt-4 rounded-xl border border-line bg-surface-1 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2" aria-hidden>
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-verified opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-verified" />
          </span>
          <SectionLabel className="mb-0">Security &amp; defense-in-depth</SectionLabel>
        </div>
        <span className="mono text-[11px] text-ink-mut">
          <CountUp value={data.detection.total_events} /> security events
        </span>
      </div>
      <p className="mt-1 mb-3 text-xs text-ink-mut">
        Edge hardening, keyed audit signing, and a classified detection stream — live and self-reported
        from their real runtime sources. Limits are prototype assumptions, env-tunable.
      </p>

      <div className="mb-3 flex flex-wrap gap-1.5">
        {data.control_alignment.map((c) => (
          <Badge key={c.framework} tone="agent">{c.framework.split(" (")[0]}</Badge>
        ))}
      </div>

      <div className="grid gap-2 sm:grid-cols-3">
        <div className="rounded-lg border border-line bg-surface-2 p-3">
          <div className="label flex items-center gap-1.5"><Activity className="h-3.5 w-3.5" /> Edge headers</div>
          <p className="mt-1 text-xs text-ink">
            {data.headers.applied.length} hardening headers · CSP <span className="mono text-evidence">default-src &apos;none&apos;</span> · frame-deny · nosniff
          </p>
        </div>
        <div className="rounded-lg border border-line bg-surface-2 p-3">
          <div className="label flex items-center gap-1.5"><Gauge className="h-3.5 w-3.5" /> Rate limiting</div>
          <p className="mt-1 text-xs text-ink">
            <span className="mono">{data.rate_limiting.limit}</span> / {data.rate_limiting.window_s}s per identity · {data.rate_limiting.throttled} throttled · body ≤ {Math.round(data.request_guard.max_body_bytes / 1024)} KiB
          </p>
        </div>
        <div className="rounded-lg border border-line bg-surface-2 p-3">
          <div className="label flex items-center gap-1.5"><KeyRound className="h-3.5 w-3.5" /> Audit integrity</div>
          <p className="mt-1 text-xs text-ink">
            SHA-256 hash chain{integ.checked ? <> · <span className={auditOk ? "text-verified" : "text-failure"}>{auditOk ? "intact" : "tampered"}</span> ({integ.entries} entries)</> : " · awaiting activity"}
            {" · "}
            <span className={data.audit_signing.active ? "text-verified" : "text-ink-mut"}>
              HMAC {data.audit_signing.active ? "signed" : "off"}
            </span>
          </p>
        </div>
      </div>

      <div className="mt-3 border-t border-line pt-3">
        <div className="label mb-2">Continuous security controls (live)</div>
        <div className="space-y-1.5">
          {data.control_checks.map((c) => (
            <div key={c.control} className="flex items-center justify-between gap-2 text-xs">
              <span className="text-ink">{c.control}</span>
              <span className="flex items-center gap-2">
                {c.detail && <span className="mono text-[11px] text-ink-mut">{c.detail}</span>}
                <Badge tone={c.status === "pass" ? "verified" : c.status === "warn" ? "pending" : "failure"}>{c.status}</Badge>
              </span>
            </div>
          ))}
        </div>
      </div>

      {data.detection.total_events > 0 && (
        <div className="mt-3 border-t border-line pt-3">
          <div className="label mb-2">Detection — recent security events</div>
          <div className="mb-2 flex flex-wrap gap-1.5">
            {Object.entries(data.detection.by_kind).map(([kind, n]) => (
              <span key={kind} className="rounded border border-line bg-surface-2 px-1.5 py-0.5 text-[11px] text-ink-mut">
                {kind.replace(/_/g, " ")} ×{n}
              </span>
            ))}
          </div>
          <div className="space-y-1">
            {data.detection.recent.slice(0, 5).map((e, i) => (
              <div key={i} className="flex items-center gap-2 text-[11px]">
                <Badge tone={sevTone(e.severity)}>{e.severity}</Badge>
                <span className="text-ink">{e.kind.replace(/_/g, " ")}</span>
                <span className="mono ml-auto truncate text-ink-mut">{e.actor}{e.route ? ` · ${e.route}` : ""}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.honest_gaps.length > 0 && (
        <p className="mt-3 text-[11px] text-ink-mut">
          <span className="text-warning">Honest gaps:</span> {data.honest_gaps.join(" · ")}
        </p>
      )}
    </section>
  );
}
