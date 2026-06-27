"use client";

import { AlertTriangle, CheckCircle2, Fingerprint, ShieldQuestion } from "lucide-react";
import { useSignature } from "@/lib/hooks";
import { Badge, Chip, ProgressBar } from "@/components/forge/primitives";
import type { SignatureSignal } from "@/lib/types";
import type { Tone } from "@/lib/state-meta";

const RUNG: Record<string, { label: string; tone: Tone; blurb: string }> = {
  strongly_consistent: {
    label: "Strongly consistent",
    tone: "verified",
    blurb:
      "The trajectory moved the way this intervention should have caused it to, the recovery held, and no latent contradiction was found.",
  },
  consistent_with_intervention: {
    label: "Consistent with intervention",
    tone: "agent",
    blurb:
      "The expected signals moved the expected way, but sustained persistence or a clean precursor isn't fully established yet.",
  },
  recovery_observed: {
    label: "Recovery observed only",
    tone: "warning",
    blurb:
      "Headline metrics improved, but the signature doesn't align — attribution to this intervention is weak (could be suppression, changed conditions, or noise).",
  },
  insufficient_evidence: {
    label: "Insufficient evidence",
    tone: "steel",
    blurb: "Not enough cycles yet to judge whether the recovery is consistent with the intervention.",
  },
};

const humanize = (s: string) =>
  s === "bearing_precursor" ? "degradation precursor" : s.replace(/_/g, " ");

function agreementTone(a: number | null | undefined): Tone {
  if (a == null) return "steel";
  if (a >= 0.34) return "verified";
  if (a <= -0.34) return "failure";
  return "warning";
}

const toPct = (a: number) => Math.round((a + 1) * 50); // [-1, 1] → [0, 100]
const signed = (a: number) => `${a >= 0 ? "+" : ""}${a.toFixed(2)}`;

export function RecoverySignaturePanel({ incidentId }: { incidentId: string }) {
  const { data } = useSignature(incidentId, 3000);
  if (!data || !data.available) return null;
  const rung = RUNG[data.rung ?? "insufficient_evidence"] ?? RUNG.insufficient_evidence;
  const alignment = data.alignment ?? 0;

  return (
    <section className="rounded-xl border border-line bg-surface-1 p-4" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Fingerprint className="h-4 w-4 text-agent" aria-hidden />
          <h3 className="text-sm font-semibold text-ink-hi">Recovery signature</h3>
          <span className="text-[12px] text-ink-mut">intervention-consistency · advisory</span>
        </div>
        <Badge tone={rung.tone}>
          {rung.tone === "verified" ? (
            <CheckCircle2 className="h-3 w-3" aria-hidden />
          ) : rung.tone === "warning" ? (
            <AlertTriangle className="h-3 w-3" aria-hidden />
          ) : (
            <ShieldQuestion className="h-3 w-3" aria-hidden />
          )}
          {rung.label}
        </Badge>
      </div>

      <p className="mt-2 text-sm text-ink">{rung.blurb}</p>

      <div className="mt-3 rounded-lg border border-line bg-surface-2 p-3">
        <div className="flex items-baseline justify-between">
          <span className="label">Signature alignment</span>
          <span className="mono text-lg text-ink-hi">{signed(alignment)}</span>
        </div>
        <div className="mt-2">
          <ProgressBar value={toPct(alignment)} tone={agreementTone(alignment)} />
        </div>
        <p className="mt-1 text-[11px] text-ink-mut">
          −1 (contradicts) → +1 (matches the expected response). Derived from the contract&apos;s own
          conditions; weighted so fault non-recurrence and the precursor outrank headline metrics.
        </p>
        {data.conditions_matched && (
          <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-line pt-2 text-[11px] text-ink-mut">
            <span className="label">Comparable conditions</span>
            <Chip>{data.conditions_matched.replace(/_/g, " ").toLowerCase()}</Chip>
            {typeof data.effective_confidence === "number" && (
              <span className="mono">effective conf {data.effective_confidence.toFixed(2)}</span>
            )}
            {data.confounding_dimensions && data.confounding_dimensions.length > 0 && (
              <span>confounders: {data.confounding_dimensions.join(", ")}</span>
            )}
            <span className="ml-auto">ceiling caps the rung — never raises it (rule {data.rule_version || "ccr-1.0"})</span>
          </div>
        )}
      </div>

      {data.signals && data.signals.length > 0 && (
        <div className="mt-3 space-y-2 border-t border-line pt-3">
          <div className="label">Expected vs. actual (per signal)</div>
          {data.signals.map((s: SignatureSignal) => (
            <div key={s.signal} className="text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className="flex flex-wrap items-center gap-1.5 text-ink">
                  {humanize(s.signal)}
                  <Chip>{s.direction.replace(/_/g, " ")}</Chip>
                  {s.derived_precursor && <Chip>precursor</Chip>}
                </span>
                <span className="mono text-ink-mut">{s.agreement == null ? "—" : signed(s.agreement)}</span>
              </div>
              <div className="mt-1">
                <ProgressBar
                  value={s.agreement == null ? 0 : toPct(s.agreement)}
                  tone={agreementTone(s.agreement)}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {data.caveats && data.caveats.length > 0 && (
        <div className="mt-3 space-y-1.5 border-t border-line pt-3">
          <div className="label">Honesty caps</div>
          {data.caveats.map((c, i) => (
            <p key={i} className="flex gap-1.5 text-[11px] text-ink-mut">
              <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-ink-mut" aria-hidden /> {c}
            </p>
          ))}
        </div>
      )}

      {data.basis && <p className="mt-3 text-[11px] text-ink-mut">{data.basis}</p>}
    </section>
  );
}
