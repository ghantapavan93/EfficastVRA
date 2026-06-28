"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  GitCompare,
  Gauge,
  PackageX,
  ShieldAlert,
  ShieldCheck,
  Fingerprint,
  FileWarning,
} from "lucide-react";
import {
  useClosureRisk,
  useComparability,
  useDisposition,
  useLotAtRisk,
  useRecoveryDebt,
  useSensorTrust,
  useSignature,
} from "@/lib/hooks";
import { cn } from "@/lib/utils";
import type { MissionDetail } from "@/lib/types";

type Sig = "verified" | "agent" | "warning" | "failure" | "steel";
const SIG_VAR: Record<Sig, string> = {
  verified: "var(--verified)", agent: "var(--agent)", warning: "var(--warning)",
  failure: "var(--failure)", steel: "var(--text-mut)",
};
const DISP: Record<string, { sig: Sig; label: string }> = {
  VERIFIED: { sig: "verified", label: "Verified Recovery" },
  CONDITIONAL: { sig: "agent", label: "Conditional Recovery" },
  FAILED: { sig: "failure", label: "Recovery Failed" },
  INSUFFICIENT_EVIDENCE: { sig: "warning", label: "Insufficient Evidence" },
  ESCALATION_REQUIRED: { sig: "warning", label: "Escalation Required" },
  IN_PROGRESS: { sig: "agent", label: "Verifying Recovery" },
};

export function CommandCenter({ m }: { m: MissionDetail }) {
  const id = m.id;
  const { data: disp } = useDisposition(id, 3000);
  const { data: risk } = useClosureRisk(id, 4000);
  const { data: comp } = useComparability(id, 4000);
  const { data: sensor } = useSensorTrust(id, 4000);
  const { data: sig } = useSignature(id, 3000);
  const { data: debt } = useRecoveryDebt(id, 4000);
  const { data: lot } = useLotAtRisk(id, 4000);

  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const d = DISP[disp?.disposition ?? "IN_PROGRESS"] ?? DISP.IN_PROGRESS;
  const stable = disp?.stable_cycles ?? 0;
  const required = disp?.required_stable_cycles ?? 30;
  const pct = required ? Math.min(100, Math.round((stable / required) * 100)) : 0;

  return (
    <section className="space-y-5">
      <style>{`
        @keyframes ccIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
        @keyframes ccPulse{0%,100%{opacity:.35;transform:scale(1)}50%{opacity:.85;transform:scale(1.05)}}
        @keyframes ccFlow{to{stroke-dashoffset:-340}}
        @keyframes ccSweep{0%{transform:translateX(-30%)}100%{transform:translateX(160%)}}
        @keyframes ccDash{to{stroke-dashoffset:0}}
        .cc-tile{animation:ccIn .5s cubic-bezier(.22,1,.36,1) both;transition:transform .25s ease,box-shadow .25s ease}
        .cc-tile:hover{transform:translateY(-3px)}
      `}</style>

      {/* ── HERO ───────────────────────────────────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-line-strong app-canvas grid-motif p-6 sm:p-7"
           style={{ animation: "ccIn .55s ease-out both" }}>
        {/* flowing telemetry lines */}
        <svg aria-hidden className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.5]" preserveAspectRatio="none" viewBox="0 0 600 240">
          {[40, 96, 152, 208].map((y, i) => (
            <path key={y} d={`M0 ${y} C 120 ${y - 22}, 220 ${y + 24}, 340 ${y - 10} S 520 ${y + 18}, 600 ${y - 6}`}
              fill="none" stroke={SIG_VAR[d.sig]} strokeWidth="1" strokeDasharray="6 10"
              style={{ opacity: 0.25 + i * 0.04, animation: `ccFlow ${7 + i * 1.5}s linear infinite` }} />
          ))}
        </svg>
        {/* scanning sweep */}
        <div aria-hidden className="pointer-events-none absolute inset-y-0 left-0 w-1/3"
          style={{ background: `linear-gradient(90deg, transparent, ${SIG_VAR[d.sig]}14, transparent)`, animation: "ccSweep 6s ease-in-out infinite" }} />

        <div className="relative flex flex-col gap-5 sm:flex-row sm:items-center">
          <StatusRing sig={d.sig} pct={pct} can={!!disp?.can_close} />
          <div className="min-w-0">
            <div className="label">Recovery command center · live</div>
            <h2 className="mt-1 text-3xl font-semibold tracking-tight text-grad sm:text-4xl">{d.label}</h2>
            <p className="mt-1.5 max-w-xl text-sm text-ink">{disp?.meaning ?? m.next_action}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <HeroChip sig={disp?.can_close ? "verified" : "steel"}
                icon={disp?.can_close ? <ShieldCheck className="h-3.5 w-3.5" /> : <ShieldAlert className="h-3.5 w-3.5" />}>
                {disp?.can_close ? "Cleared to close" : "Not cleared to close"}
              </HeroChip>
              <HeroChip sig="agent" icon={<Activity className="h-3.5 w-3.5" />}>
                <span className="mono">{stable}/{required}</span> stable cycles
              </HeroChip>
              {m.reopened_count > 0 && (
                <HeroChip sig="warning" icon={<AlertTriangle className="h-3.5 w-3.5" />}>reopened ×{m.reopened_count}</HeroChip>
              )}
            </div>
          </div>
        </div>
        <div className="relative mt-4 border-t border-line/60 pt-3 text-[12px] text-ink-mut">
          {m.title}
        </div>
      </div>

      {/* ── SIGNAL CONSTELLATION ───────────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Tile i={0} icon={<Gauge className="h-4 w-4" />} title="Closure risk"
          sig={risk?.band === "high" ? "failure" : risk?.band === "elevated" ? "warning" : "verified"}>
          <ArcGauge value={(risk?.risk ?? 0)} sig={risk?.band === "high" ? "failure" : risk?.band === "elevated" ? "warning" : "verified"}
            label={`${risk?.risk_pct ?? 0}%`} mounted={mounted} />
          <Caption>{(risk?.band ?? "low").replace(/_/g, " ")} · false-closure</Caption>
        </Tile>

        <Tile i={1} icon={<Fingerprint className="h-4 w-4" />} title="Recovery signature"
          sig={(sig?.alignment ?? 0) >= 0.34 ? "verified" : (sig?.alignment ?? 0) <= -0.34 ? "failure" : "warning"}>
          <BigStat value={signed(sig?.alignment ?? 0)} />
          <Bar value={((sig?.alignment ?? 0) + 1) * 50}
            sig={(sig?.alignment ?? 0) >= 0.34 ? "verified" : (sig?.alignment ?? 0) <= -0.34 ? "failure" : "warning"} mounted={mounted} />
          <Caption>{(sig?.rung ?? "insufficient evidence").replace(/_/g, " ")}</Caption>
        </Tile>

        <Tile i={2} icon={<GitCompare className="h-4 w-4" />} title="Comparable conditions"
          sig={comp?.classification === "COMPARABLE" ? "verified" : comp?.classification === "NOT_COMPARABLE" ? "failure" : "warning"}>
          <BigStat value={(comp?.classification ?? "UNKNOWN").replace(/_/g, " ").toLowerCase()} small />
          <Caption>confidence ×{(comp?.confidence_multiplier ?? 1).toFixed(2)}</Caption>
        </Tile>

        <Tile i={3} icon={<ShieldCheck className="h-4 w-4" />} title="Sensor trust"
          sig={sensor?.status === "TRUSTED" ? "verified" : sensor?.status === "UNTRUSTED" ? "failure" : sensor?.status === "DEGRADED" ? "warning" : "steel"}>
          <BigStat value={(sensor?.status ?? "UNKNOWN").toLowerCase()} small />
          <Caption>{sensor?.satisfies_hard_conditions ? "may satisfy hard conditions" : "can't satisfy a hard condition"}</Caption>
        </Tile>

        <Tile i={4} icon={<Activity className="h-4 w-4" />} title="Verification window"
          sig={pct >= 100 ? "verified" : "agent"}>
          <BigStat value={`${pct}%`} />
          <Bar value={pct} sig={pct >= 100 ? "verified" : "agent"} mounted={mounted} />
          <Caption><span className="mono">{stable}/{required}</span> consecutive stable cycles</Caption>
        </Tile>

        <Tile i={5}
          icon={debt?.available && debt?.status === "ACTIVE" ? <FileWarning className="h-4 w-4" /> : <PackageX className="h-4 w-4" />}
          title={debt?.available && debt?.status === "ACTIVE" ? "Recovery debt" : "Lot-at-risk"}
          sig={debt?.available && debt?.status === "ACTIVE" ? "warning" : lot?.at_risk ? "warning" : "verified"}>
          {debt?.available && debt?.status === "ACTIVE" ? (
            <>
              <BigStat value="active waiver" small />
              <Caption>{debt?.minutes_remaining}m left · {(debt?.waived ?? []).map((w) => w.label).join(", ")}</Caption>
            </>
          ) : lot?.at_risk ? (
            <>
              <BigStat value={`${lot?.affected_lot_count ?? 0} lot(s)`} small />
              <Caption>questionable from cycle {lot?.first_questionable_cycle}</Caption>
            </>
          ) : (
            <>
              <BigStat value="clear" small />
              <Caption>no waiver · no lots at risk</Caption>
            </>
          )}
        </Tile>
      </div>
    </section>
  );
}

/* ── building blocks ─────────────────────────────────────────────────────── */
const signed = (a: number) => `${a >= 0 ? "+" : ""}${a.toFixed(2)}`;

function StatusRing({ sig, pct, can }: { sig: Sig; pct: number; can: boolean }) {
  const v = SIG_VAR[sig];
  const C = 2 * Math.PI * 34;
  return (
    <div className="relative grid h-28 w-28 shrink-0 place-items-center">
      <div aria-hidden className="absolute inset-0 rounded-full" style={{ boxShadow: `0 0 50px -6px ${v}`, animation: "ccPulse 2.6s ease-in-out infinite" }} />
      <svg width="112" height="112" viewBox="0 0 80 80" className="-rotate-90">
        <circle cx="40" cy="40" r="34" fill="none" stroke="var(--surface-3)" strokeWidth="5" />
        <circle cx="40" cy="40" r="34" fill="none" stroke={v} strokeWidth="5" strokeLinecap="round"
          strokeDasharray={C} strokeDashoffset={C * (1 - pct / 100)} style={{ transition: "stroke-dashoffset 1s cubic-bezier(.22,1,.36,1)" }} />
      </svg>
      <div className="absolute grid place-items-center">
        {can ? <ShieldCheck className="h-7 w-7" style={{ color: v }} aria-hidden />
             : <Activity className="h-7 w-7" style={{ color: v }} aria-hidden />}
      </div>
    </div>
  );
}

function HeroChip({ sig, icon, children }: { sig: Sig; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[12px]"
      style={{ borderColor: `${SIG_VAR[sig]}55`, color: "var(--text)", background: `${SIG_VAR[sig]}12` }}>
      <span style={{ color: SIG_VAR[sig] }}>{icon}</span>{children}
    </span>
  );
}

function Tile({ i, icon, title, sig, children }: { i: number; icon: React.ReactNode; title: string; sig: Sig; children: React.ReactNode }) {
  return (
    <div className="cc-tile card relative overflow-hidden p-4" style={{ animationDelay: `${80 + i * 70}ms` }}>
      <div aria-hidden className="absolute inset-x-0 top-0 h-px" style={{ background: `linear-gradient(90deg, transparent, ${SIG_VAR[sig]}, transparent)` }} />
      <div className="flex items-center gap-2">
        <span style={{ color: SIG_VAR[sig] }}>{icon}</span>
        <span className="label">{title}</span>
        <span className="ml-auto h-2 w-2 rounded-full" style={{ background: SIG_VAR[sig], boxShadow: `0 0 10px ${SIG_VAR[sig]}`, animation: "ccPulse 2.4s ease-in-out infinite" }} />
      </div>
      <div className="mt-3 space-y-2">{children}</div>
    </div>
  );
}

function BigStat({ value, small }: { value: string | number; small?: boolean }) {
  return <div className={cn("font-semibold text-ink-hi", small ? "text-lg capitalize" : "mono text-2xl")}>{value}</div>;
}
function Caption({ children }: { children: React.ReactNode }) {
  return <p className="text-[11px] capitalize text-ink-mut">{children}</p>;
}
function Bar({ value, sig, mounted }: { value: number; sig: Sig; mounted: boolean }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-3">
      <div className="h-full rounded-full" style={{ width: `${mounted ? Math.max(0, Math.min(100, value)) : 0}%`, background: SIG_VAR[sig], transition: "width 1s cubic-bezier(.22,1,.36,1)" }} />
    </div>
  );
}
function ArcGauge({ value, sig, label, mounted }: { value: number; sig: Sig; label: string; mounted: boolean }) {
  const arc = Math.PI * 32;
  const frac = Math.max(0, Math.min(1, value));
  return (
    <svg viewBox="0 0 80 46" className="w-full max-w-[150px]" role="img" aria-label={label}>
      <path d="M 8 40 A 32 32 0 0 1 72 40" fill="none" stroke="var(--surface-3)" strokeWidth="6" strokeLinecap="round" />
      <path d="M 8 40 A 32 32 0 0 1 72 40" fill="none" stroke={SIG_VAR[sig]} strokeWidth="6" strokeLinecap="round"
        strokeDasharray={arc} strokeDashoffset={mounted ? arc * (1 - frac) : arc}
        style={{ transition: "stroke-dashoffset 1.1s cubic-bezier(.22,1,.36,1)" }} />
      <text x="40" y="38" textAnchor="middle" className="mono" fill="var(--text-hi)" fontSize="15" fontWeight="600">{label}</text>
    </svg>
  );
}
