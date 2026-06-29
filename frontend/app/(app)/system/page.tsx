"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, Database, ShieldCheck } from "lucide-react";
import { useMe } from "@/lib/hooks";
import { Badge, SectionLabel } from "@/components/forge/primitives";
import { LoadingState } from "@/components/forge/states";
import { CalibrationPanel } from "@/components/system/calibration-panel";
import { SecurityPanel } from "@/components/system/security-panel";
import { ShadowScorecard } from "@/components/system/shadow-scorecard";

function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const r = await fetch("/health", { cache: "no-store" });
      return r.json() as Promise<{
        status: string; environment: string; demo_mode: boolean; reasoning: string;
        db?: boolean; outbox?: { pending: number; published: number; failed: number };
      }>;
    },
    refetchInterval: 5000,
  });
}

interface MachineProfile {
  equipment_class: string;
  label: string;
  machine_models: string[];
  summary: string;
  required_stable_cycles: number;
  fault_codes: string[];
  condition_count: number;
}

function useMachineProfiles() {
  return useQuery({
    queryKey: ["machine-profiles"],
    queryFn: async () => {
      const r = await fetch("/api/machine-profiles", { cache: "no-store", headers: { "X-VRA-User": "s.vega" } });
      return r.json() as Promise<{ profiles: MachineProfile[] }>;
    },
  });
}

interface Connector {
  key: string;
  label: string;
  protocol: string;
  direction: string;
  feeds: string;
  description: string;
}

interface Integration {
  isa95_levels: string[];
  example: { machine: string; isa95_path: string[]; uns_topics: string[]; sparkplug_topic: string };
  connectors: Connector[];
}

function useIntegration() {
  return useQuery({
    queryKey: ["integration"],
    queryFn: async () => {
      const r = await fetch("/api/integration", { cache: "no-store", headers: { "X-VRA-User": "s.vega" } });
      return r.json() as Promise<Integration>;
    },
  });
}

interface Governance {
  control_alignment?: { framework: string }[];
  security?: { prohibited_actions?: unknown[] };
  auditability?: { live_integrity?: { checked: boolean; intact: boolean; entries: number } };
  control_checks?: { control: string; status: string; detail?: string }[];
  honest_gaps?: string[];
}

function useGovernance() {
  return useQuery({
    queryKey: ["governance"],
    queryFn: async () => {
      const r = await fetch("/api/governance", { cache: "no-store", headers: { "X-VRA-User": "s.vega" } });
      return r.json() as Promise<Governance>;
    },
    refetchInterval: 8000,
  });
}

interface Metrics {
  uptime_seconds: number;
  requests_total: number;
  errors_total: number;
  error_rate: number;
  latency_ms: { p50: number; p95: number; p99: number };
  missions: { active: number; verified: number; reopened_total: number };
}

function useMetrics() {
  return useQuery({
    queryKey: ["metrics"],
    queryFn: async () => {
      const r = await fetch("/api/metrics", { cache: "no-store", headers: { "X-VRA-User": "s.vega" } });
      return r.json() as Promise<Metrics>;
    },
    refetchInterval: 5000,
  });
}

export default function SystemPage() {
  const { data: me } = useMe();
  const { data: health, isLoading } = useHealth();
  const { data: catalog } = useMachineProfiles();
  const { data: integration } = useIntegration();
  const { data: gov } = useGovernance();
  const { data: metrics } = useMetrics();
  if (isLoading || !health) return <LoadingState label="Checking system health" />;

  return (
    <div className="tab-in mx-auto max-w-3xl px-6 py-7">
      <h1 className="text-2xl font-semibold tracking-tight text-ink-hi">System Health</h1>
      <p className="mt-1 text-sm text-ink-mut">Runtime status, versions, and safety posture.</p>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        <Tile icon={Activity} label="Backend" value={health.status === "ok" ? "Online" : "Degraded"} tone={health.status === "ok" ? "verified" : "failure"} />
        <Tile icon={Database} label="Reasoning provider" value={health.reasoning} tone="agent" />
        {health.outbox && (
          <Tile
            icon={Activity}
            label="Event outbox"
            value={`${health.outbox.published} published · ${health.outbox.pending} pending${health.outbox.failed ? ` · ${health.outbox.failed} failed` : ""}`}
            tone={health.outbox.failed ? "failure" : health.outbox.pending ? "pending" : "verified"}
          />
        )}
        <Tile icon={ShieldCheck} label="Environment" value={health.environment} tone="brand" />
        <Tile icon={ShieldCheck} label="Demo mode" value={health.demo_mode ? "enabled" : "disabled"} tone={health.demo_mode ? "pending" : "steel"} />
      </div>

      <section className="mt-6 rounded-xl border border-line bg-surface-1 p-4">
        <SectionLabel className="mb-2">Identity</SectionLabel>
        <div className="grid grid-cols-2 gap-y-2 text-sm">
          <span className="text-ink-mut">Acting as</span><span className="mono text-ink">{me?.username} · {me?.role}</span>
          <span className="text-ink-mut">Plant</span><span className="mono text-ink">{me?.plant_id}</span>
          <span className="text-ink-mut">Tenant</span><span className="mono text-ink">{me?.tenant_id}</span>
        </div>
      </section>

      {catalog?.profiles && (
        <section className="mt-4 rounded-xl border border-line bg-surface-1 p-4">
          <SectionLabel className="mb-1">Supported machine classes</SectionLabel>
          <p className="mb-3 text-xs text-ink-mut">
            The Recovery Contract is machine-agnostic — each class is declared as data, verified by the
            same deterministic engine. Adding a machine is a profile, not code.
          </p>
          <div className="grid gap-2 sm:grid-cols-3">
            {catalog.profiles.map((p) => (
              <div key={p.equipment_class} className="rounded-lg border border-line bg-surface-2 p-3">
                <div className="text-sm font-medium text-ink">{p.label}</div>
                <div className="mono mt-0.5 text-[11px] text-ink-mut">{p.machine_models.join(" · ")}</div>
                <p className="mt-1.5 text-xs text-ink-mut">{p.summary}</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <Badge tone="agent">{p.condition_count} conditions</Badge>
                  <Badge tone="steel">{p.required_stable_cycles} stable cycles</Badge>
                  {p.fault_codes.map((f) => <Badge key={f} tone="warning">{f}</Badge>)}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <CalibrationPanel />

      {gov && (
        <section className="mt-4 rounded-xl border border-line bg-surface-1 p-4">
          <SectionLabel className="mb-1">Governance &amp; compliance</SectionLabel>
          <p className="mb-3 text-xs text-ink-mut">
            Security, logging, and auditability are first-class — shown live and mapped to enterprise
            control frameworks.
          </p>
          <div className="mb-3 flex flex-wrap gap-1.5">
            {gov.control_alignment?.map((c: { framework: string }) => (
              <Badge key={c.framework} tone="agent">{c.framework.split(" (")[0]}</Badge>
            ))}
          </div>
          <div className="grid gap-2 sm:grid-cols-3">
            <div className="rounded-lg border border-line bg-surface-2 p-3">
              <div className="label">Security</div>
              <p className="mt-1 text-xs text-ink">RBAC (server-authoritative) · {gov.security?.prohibited_actions?.length} prohibited actions · gateway choke point</p>
            </div>
            <div className="rounded-lg border border-line bg-surface-2 p-3">
              <div className="label">Logging</div>
              <p className="mt-1 text-xs text-ink">Structured JSON · correlation IDs · per-request access log</p>
            </div>
            <div className="rounded-lg border border-line bg-surface-2 p-3">
              <div className="label">Auditability</div>
              <p className="mt-1 text-xs text-ink">
                Tamper-evident hash chain ·{" "}
                {gov.auditability?.live_integrity?.checked && (gov.auditability.live_integrity.entries ?? 0) > 0 ? (
                  <span className={gov.auditability.live_integrity.intact ? "text-verified" : "text-failure"}>
                    {gov.auditability.live_integrity.intact ? "verified ✓" : "tampering detected"} ({gov.auditability.live_integrity.entries} entries)
                  </span>
                ) : "awaiting activity"}
              </p>
            </div>
          </div>
          {gov.control_checks && gov.control_checks.length > 0 && (
            <div className="mt-3 border-t border-line pt-3">
              <div className="label mb-2">Continuous control checks (live oversight)</div>
              <div className="space-y-1.5">
                {gov.control_checks.map((c) => (
                  <div key={c.control} className="flex items-center justify-between gap-2 text-xs">
                    <span className="text-ink">{c.control}</span>
                    <span className="flex items-center gap-2">
                      {c.detail && <span className="mono text-[11px] text-ink-mut">{c.detail}</span>}
                      <Badge tone={c.status === "pass" ? "verified" : c.status === "warn" ? "pending" : "failure"}>
                        {c.status}
                      </Badge>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {gov.honest_gaps && gov.honest_gaps.length > 0 && (
            <p className="mt-3 text-[11px] text-ink-mut">
              <span className="text-warning">Honest gaps:</span> {gov.honest_gaps.join(" · ")}
            </p>
          )}
        </section>
      )}

      <SecurityPanel />

      <ShadowScorecard />

      {metrics && (
        <section className="mt-4 rounded-xl border border-line bg-surface-1 p-4">
          <SectionLabel className="mb-1">Operations &amp; SLOs</SectionLabel>
          <p className="mb-3 text-xs text-ink-mut">
            Live service-level indicators an SRE watches. Ownership, on-call, and uptime targets are in
            docs/OPERATIONS.md; the system-incident runbook is in docs/INCIDENT_RESPONSE.md.
          </p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Stat label="Uptime" value={`${Math.round(metrics.uptime_seconds)}s`} />
            <Stat label="Requests" value={String(metrics.requests_total)} />
            <Stat label="Error rate" value={`${(metrics.error_rate * 100).toFixed(2)}%`} tone={metrics.error_rate > 0.005 ? "failure" : "verified"} />
            <Stat label="Latency p95" value={`${metrics.latency_ms.p95} ms`} tone={metrics.latency_ms.p95 > 300 ? "warning" : "verified"} />
            <Stat label="Active missions" value={String(metrics.missions.active)} />
            <Stat label="Verified" value={String(metrics.missions.verified)} />
            <Stat label="Reopened (total)" value={String(metrics.missions.reopened_total)} />
            <Stat label="Latency p50" value={`${metrics.latency_ms.p50} ms`} />
          </div>
        </section>
      )}

      {integration && (
        <section className="mt-4 rounded-xl border border-line bg-surface-1 p-4">
          <SectionLabel className="mb-1">Integration &amp; data fabric</SectionLabel>
          <p className="mb-3 text-xs text-ink-mut">
            The agent sits above the MES / Unified Namespace. Plant data reaches it through typed
            connectors — documented seams, not live connections in this synthetic prototype.
          </p>
          {integration.example?.isa95_path && (
            <div className="mb-3 rounded-lg border border-line bg-surface-2 p-3">
              <div className="label mb-1">ISA-95 path · {integration.example.machine}</div>
              <div className="mono text-[12px] text-ink">{integration.example.isa95_path.join(" / ")}</div>
              <div className="label mb-1 mt-2">Unified Namespace topic</div>
              <div className="mono break-all text-[12px] text-evidence">{integration.example.uns_topics?.[0]}</div>
              <div className="label mb-1 mt-2">MQTT Sparkplug B (Parris)</div>
              <div className="mono break-all text-[12px] text-ink-mut">{integration.example.sparkplug_topic}</div>
            </div>
          )}
          <div className="space-y-1.5">
            {integration.connectors.map((c) => (
              <div key={c.key} className="flex flex-wrap items-center gap-2 rounded-md border border-line bg-surface-2 px-3 py-2">
                <span className="text-sm font-medium text-ink">{c.label}</span>
                <Badge tone="steel">{c.protocol}</Badge>
                <Badge tone={c.direction === "inbound" ? "evidence" : c.direction === "outbound" ? "agent" : "approval"}>{c.direction}</Badge>
                <span className="mono ml-auto text-[11px] text-ink-mut">→ {c.feeds}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="mt-4 rounded-xl border border-verified/30 bg-verified-soft p-4">
        <SectionLabel className="mb-2 text-verified">Operational-technology safety</SectionLabel>
        <ul className="space-y-1 text-sm text-ink">
          <li>No route, tool, or mock can start, stop, restart, or reconfigure a machine.</li>
          <li>PLC/set-point changes, alarm/interlock bypass, and lockout-tagout confirmation are PROHIBITED.</li>
          <li>Quality release and incident closure require a human of the correct role — never the model.</li>
          <li>Every write action passes the Agent Action Gateway and is recorded in the audit trail.</li>
        </ul>
      </section>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "verified" | "failure" | "warning" }) {
  const color =
    tone === "failure" ? "text-failure" : tone === "warning" ? "text-warning" : tone === "verified" ? "text-verified" : "text-ink-hi";
  return (
    <div className="rounded-md border border-line bg-surface-2 p-2.5">
      <div className="label">{label}</div>
      <div className={`mono mt-1 text-sm ${color}`}>{value}</div>
    </div>
  );
}

function Tile({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  tone: "verified" | "failure" | "agent" | "brand" | "pending" | "steel";
}) {
  return (
    <div className="rounded-xl border border-line bg-surface-1 p-4">
      <div className="label flex items-center gap-1.5"><Icon className="h-3.5 w-3.5" /> {label}</div>
      <div className="mt-2 flex items-center justify-between">
        <span className="text-sm text-ink-hi capitalize">{value}</span>
        <Badge tone={tone}>●</Badge>
      </div>
    </div>
  );
}
