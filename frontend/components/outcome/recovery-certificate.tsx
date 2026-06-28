"use client";

import { Check, Clock, Printer, RotateCcw, ShieldCheck, X } from "lucide-react";
import { useCertificate } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Badge, Chip } from "@/components/forge/primitives";
import type { Tone } from "@/lib/state-meta";
import type { CertApproval, CertCondition } from "@/lib/types";

const STATUS: Record<string, { tone: Tone; label: string; line: string }> = {
  certified: { tone: "verified", label: "Certified", line: "Verified Recovery" },
  not_certified: { tone: "warning", label: "Not certified", line: "Recovery NOT certified — conditions not comparable" },
  reopened: { tone: "failure", label: "Reopened", line: "Reopened — recovery not certified" },
  pending: { tone: "steel", label: "Pending", line: "Certification pending" },
};

const fmtDate = (iso?: string) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
};

export function RecoveryCertificate({ incidentId }: { incidentId: string }) {
  const { data } = useCertificate(incidentId, 4000);
  if (!data) return null;
  if (!data.available) {
    return (
      <section className="rounded-xl border border-line bg-surface-1 p-6 text-sm text-ink-mut">
        No certificate yet — a Recovery Contract must exist before recovery can be certified.
      </section>
    );
  }
  const st = STATUS[data.status ?? "pending"] ?? STATUS.pending;
  const certified = data.status === "certified";

  return (
    <section
      id="recovery-cert"
      className="alive relative overflow-hidden rounded-2xl border border-line-strong bg-surface-1 p-6 sm:p-8"
      style={{ animation: "certIn .5s ease-out both" }}
    >
      <style>{`
        @keyframes certIn{from{opacity:0;transform:translateY(8px) scale(.99)}to{opacity:1;transform:none}}
        @keyframes sealIn{from{opacity:0;transform:scale(.6) rotate(-12deg)}to{opacity:1;transform:none}}
        @media print{
          body *{visibility:hidden !important}
          #recovery-cert,#recovery-cert *{visibility:visible !important}
          #recovery-cert{position:absolute;left:0;top:0;width:100%;border:none}
          .noprint{display:none !important}
        }
      `}</style>
      {/* subtle ornamental frame */}
      <div aria-hidden className="pointer-events-none absolute inset-2 rounded-xl border border-line opacity-60" />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.05]"
        style={{ background: "radial-gradient(50% 45% at 50% 0%, var(--agent), transparent 70%)" }}
      />

      {/* header */}
      <div className="relative flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <Seal tone={st.tone} certified={certified} />
          <div>
            <div className="label tracking-[0.18em]">Return‑to‑Service Certificate</div>
            <h2 className="mt-0.5 text-xl font-semibold tracking-tight text-ink-hi sm:text-2xl">{st.line}</h2>
            <div className="mono mt-0.5 text-[11px] text-ink-mut">{data.certificate_id}</div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge tone={st.tone}>
            {certified ? <ShieldCheck className="h-3 w-3" aria-hidden /> : data.status === "reopened" ? <RotateCcw className="h-3 w-3" aria-hidden /> : <Clock className="h-3 w-3" aria-hidden />}
            {st.label}
          </Badge>
          <button
            onClick={() => window.print()}
            className="noprint inline-flex items-center gap-1.5 rounded-[10px] border border-line-strong px-2.5 py-1 text-[12px] text-ink-mut hover:bg-surface-2 hover:text-ink"
          >
            <Printer className="h-3.5 w-3.5" aria-hidden /> Print / Export
          </button>
        </div>
      </div>

      {/* subject */}
      <div className="relative mt-5 grid gap-x-8 gap-y-2 border-t border-line pt-4 text-sm sm:grid-cols-2">
        <Field label="Machine">{data.subject?.machine}{data.subject?.machine_code ? ` · ${data.subject.machine_code}` : ""}</Field>
        <Field label="Model / Plant">{[data.subject?.machine_model, data.subject?.plant_id].filter(Boolean).join(" · ") || "—"}</Field>
        <Field label="Order">{data.subject?.order_id ?? "—"}</Field>
        <Field label="Originating fault">{data.subject?.fault_code ?? "—"}</Field>
        <Field label="Contract">{data.subject?.contract_no} · v{data.subject?.contract_version}</Field>
        <Field label="Stable cycles">{data.stable_cycles}/{data.required_stable_cycles}{data.reopened_count ? ` · reopened ×${data.reopened_count}` : ""}</Field>
      </div>

      {/* conditions */}
      <div className="relative mt-5 border-t border-line pt-4">
        <div className="label mb-2">Deterministic conditions evaluated</div>
        <div className="grid gap-1.5 sm:grid-cols-2">
          {(data.conditions ?? []).map((c: CertCondition) => (
            <div key={c.key} className="flex items-center gap-2 text-xs">
              <CondIcon status={c.status} />
              <span className="text-ink">{c.label || c.key}</span>
              <span className="mono ml-auto text-[10px] text-ink-mut">{c.status.toLowerCase()}</span>
            </div>
          ))}
        </div>
      </div>

      {/* evidence + intervention-consistency */}
      <div className="relative mt-5 grid gap-3 border-t border-line pt-4 sm:grid-cols-2">
        <div className="rounded-lg border border-line bg-surface-2 p-3">
          <div className="label">Evidence (trust‑weighted)</div>
          <p className="mt-1 text-xs text-ink">
            {data.evidence_summary?.count ?? 0} items · mean trust{" "}
            <span className="mono">{data.evidence_summary?.mean_trust ?? "—"}</span> · weakest{" "}
            <span className="mono">{data.evidence_summary?.min_trust ?? "—"}</span>
          </p>
        </div>
        <div className="rounded-lg border border-line bg-surface-2 p-3">
          <div className="label">Intervention‑consistency (advisory)</div>
          <p className="mt-1 flex items-center gap-2 text-xs text-ink">
            <Chip>{(data.signature?.rung ?? "—").replace(/_/g, " ")}</Chip>
            <span className="mono">alignment {data.signature?.alignment?.toFixed?.(2) ?? "—"}</span>
          </p>
        </div>
      </div>

      {/* signatures (human approvals) */}
      <div className="relative mt-5 border-t border-line pt-4">
        <div className="label mb-2">Human authorizations (signatures)</div>
        {data.approvals && data.approvals.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {data.approvals.map((a: CertApproval, i) => (
              <div key={i} className="rounded-lg border border-line bg-surface-2 px-3 py-2">
                <div className="font-[450] text-ink" style={{ fontVariationSettings: '"slnt" -6' }}>
                  {a.decided_by || "—"}
                </div>
                <div className="mt-0.5 flex items-center justify-between text-[11px] text-ink-mut">
                  <span className="uppercase tracking-wide">{a.decided_role} · {a.decision}</span>
                  <span className="mono">{fmtDate(a.at ?? undefined)}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-ink-mut">Awaiting required human approval(s).</p>
        )}
      </div>

      {/* tamper-evident seal */}
      <div className="relative mt-5 border-t border-line pt-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={data.audit?.intact ? "verified" : "failure"}>
            {data.audit?.intact ? "audit chain intact" : "audit chain BROKEN"} · {data.audit?.entries ?? 0} entries
          </Badge>
          {data.trustworthy ? (
            <Badge tone="verified"><ShieldCheck className="h-3 w-3" aria-hidden /> trustworthy closure</Badge>
          ) : (
            <Badge tone="steel">trust not established</Badge>
          )}
        </div>
        <div className="mt-2 grid gap-1 text-[11px] text-ink-mut">
          <div>Audit seal (chain head): <span className="mono break-all text-ink">{data.audit?.head_hash || "—"}</span></div>
          <div>Certificate hash: <span className="mono break-all text-ink">{data.certificate_hash || "—"}</span></div>
        </div>
      </div>

      {/* footer */}
      <div className="relative mt-5 flex flex-wrap items-end justify-between gap-2 border-t border-line pt-4 text-[11px] text-ink-mut">
        <div>
          <div>Issued {fmtDate(data.issued_at)}</div>
          <div className="mt-0.5 max-w-md">{data.issuer}</div>
        </div>
        <div className="max-w-xs text-right">{data.basis}</div>
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

function CondIcon({ status }: { status: string }) {
  if (status === "PASSED") return <Check className="h-3.5 w-3.5 shrink-0 text-verified" aria-hidden />;
  if (status === "VIOLATED") return <X className="h-3.5 w-3.5 shrink-0 text-failure" aria-hidden />;
  return <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-ink-mut" aria-hidden />;
}

function Seal({ tone, certified }: { tone: Tone; certified: boolean }) {
  const stroke = tone === "verified" ? "var(--verified)" : tone === "failure" ? "var(--failure)" : "var(--ink-mut)";
  return (
    <svg width="56" height="56" viewBox="0 0 56 56" aria-hidden style={{ animation: "sealIn .6s ease-out both" }}>
      <circle cx="28" cy="28" r="25" fill="none" stroke={stroke} strokeWidth="1.5" opacity="0.5" />
      <circle cx="28" cy="28" r="20" fill="none" stroke={stroke} strokeWidth="2" />
      {certified ? (
        <path d="M19 28.5 L25.5 35 L38 21" fill="none" stroke={stroke} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      ) : (
        <circle cx="28" cy="28" r="3" fill={stroke} />
      )}
      {/* ring ticks for an embossed-seal feel */}
      {Array.from({ length: 24 }).map((_, i) => {
        const a = (i / 24) * Math.PI * 2;
        return (
          <line
            key={i}
            x1={28 + Math.cos(a) * 23}
            y1={28 + Math.sin(a) * 23}
            x2={28 + Math.cos(a) * 25}
            y2={28 + Math.sin(a) * 25}
            stroke={stroke}
            strokeWidth="0.75"
            opacity="0.45"
          />
        );
      })}
    </svg>
  );
}
