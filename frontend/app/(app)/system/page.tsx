"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, Database, ShieldCheck } from "lucide-react";
import { useMe } from "@/lib/hooks";
import { Badge, SectionLabel } from "@/components/forge/primitives";
import { LoadingState } from "@/components/forge/states";

function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const r = await fetch("/health", { cache: "no-store" });
      return r.json() as Promise<{ status: string; environment: string; demo_mode: boolean; reasoning: string }>;
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

export default function SystemPage() {
  const { data: me } = useMe();
  const { data: health, isLoading } = useHealth();
  const { data: catalog } = useMachineProfiles();
  const { data: integration } = useIntegration();
  if (isLoading || !health) return <LoadingState label="Checking system health" />;

  return (
    <div className="mx-auto max-w-3xl px-6 py-7">
      <h1 className="text-2xl font-semibold tracking-tight text-ink-hi">System Health</h1>
      <p className="mt-1 text-sm text-ink-mut">Runtime status, versions, and safety posture.</p>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        <Tile icon={Activity} label="Backend" value={health.status === "ok" ? "Online" : "Degraded"} tone={health.status === "ok" ? "verified" : "failure"} />
        <Tile icon={Database} label="Reasoning provider" value={health.reasoning} tone="agent" />
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
