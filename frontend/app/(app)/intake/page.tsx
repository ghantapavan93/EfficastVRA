"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, ArrowRight, BrainCircuit, CheckCircle2, FileUp, FlaskConical, HelpCircle, Loader2, MinusCircle, Rocket, Upload } from "lucide-react";
import { Badge, SectionLabel } from "@/components/forge/primitives";
import type { Tone } from "@/lib/state-meta";

interface ColMap { column: string; target_event: string | null; target_field: string | null; confidence: number; kind: string; samples: string[]; missing_pct: number; note: string }
interface Dim { name: string; status: string; detail: string }
interface Readiness { score: number; verdict: string; ready: string[]; warnings: string[]; blocked: string[]; dimensions: Dim[] }
interface Entry { at: string | null; label: string; kind: string; detail: string }
interface Reconstruction { summary: string; entries: Entry[]; fault_count: number; false_closure_detected: boolean }
interface Analysis { filename: string; format: string; row_count: number; column_count: number; mapped_count: number; mappings: ColMap[]; readiness: Readiness; reconstruction: Reconstruction; basis: string }

const KIND_META: Record<string, { tone: Tone; label: string }> = {
  observed: { tone: "evidence", label: "Observed" },
  derived: { tone: "agent", label: "Derived" },
  human: { tone: "brand", label: "Human" },
  ai_interpretation: { tone: "approval", label: "AI interpretation" },
  missing: { tone: "failure", label: "Missing" },
  contradiction: { tone: "warning", label: "Contradiction" },
};

interface Profile { id: string; name: string; source_filename: string; mapped_columns: number }

async function analyze(filename: string, content: string, profileId: string): Promise<Analysis> {
  const r = await fetch("/api/intake/analyze", {
    method: "POST", headers: { "Content-Type": "application/json", "X-VRA-User": "s.vega" },
    body: JSON.stringify({ filename, content, profile_id: profileId || undefined }),
  });
  return r.json();
}

export default function IntakePage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [creating, setCreating] = useState(false);
  const [data, setData] = useState<Analysis | null>(null);
  const [src, setSrc] = useState<{ filename: string; content: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [profileId, setProfileId] = useState<string>("");

  useEffect(() => {
    fetch("/api/intake/profiles", { headers: { "X-VRA-User": "s.vega" } })
      .then((r) => r.json()).then((d) => setProfiles(d.profiles ?? [])).catch(() => {});
  }, [data]);

  const run = async (filename: string, content: string) => {
    setBusy(true); setErr(null); setSrc({ filename, content });
    try { setData(await analyze(filename, content, profileId)); }
    catch (e) { setErr(String(e)); }
    finally { setBusy(false); }
  };

  const createMission = async () => {
    if (!src) return;
    setCreating(true); setErr(null);
    try {
      const r = await fetch("/api/intake/create-mission", {
        method: "POST", headers: { "Content-Type": "application/json", "X-VRA-User": "s.vega" },
        body: JSON.stringify({ ...src, profile_id: profileId || undefined }),
      });
      const out = await r.json();
      if (out.created && out.incident_id) router.push(`/missions/${out.incident_id}`);
      else { setErr(out.reason || "Could not create the mission."); setCreating(false); }
    } catch (e) { setErr(String(e)); setCreating(false); }
  };

  const onFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => run(file.name, String(reader.result || ""));
    reader.readAsText(file);
  };

  const useSample = async () => {
    setBusy(true); setErr(null);
    try {
      const s = await (await fetch("/api/intake/sample", { headers: { "X-VRA-User": "s.vega" } })).json();
      await run(s.filename, s.content);
    } catch (e) { setErr(String(e)); setBusy(false); }
  };

  return (
    <div className="tab-in mx-auto max-w-5xl px-6 py-8">
      <div className="flex items-center gap-2">
        <FileUp className="h-5 w-5 text-agent" aria-hidden />
        <h1 className="text-2xl font-semibold tracking-tight text-ink-hi">Create a Recovery Mission</h1>
      </div>
      <p className="mt-1 max-w-2xl text-sm text-ink-mut">
        Bring your plant data. Verified Recovery detects the schema, proposes a mapping onto the recovery
        contract, reports data readiness, and reconstructs the incident — <span className="text-ink">you</span> confirm
        the mapping; the deterministic layer decides the verdict.
      </p>

      {/* source */}
      <section className="alive mt-6 rounded-2xl border border-line-strong bg-surface-1 p-5">
        <SectionLabel className="mb-3">Connect a source</SectionLabel>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="group flex cursor-pointer flex-col items-start gap-2 rounded-xl border border-dashed border-line-strong bg-surface-2 p-4 transition-colors hover:border-agent">
            <span className="grid h-10 w-10 place-items-center rounded-lg border border-line bg-surface-1"><Upload className="h-4 w-4 text-agent" /></span>
            <span className="text-sm font-medium text-ink">Upload plant data</span>
            <span className="text-[11px] text-ink-mut">CSV · JSON · JSONL — telemetry, events, cycles, quality, approvals…</span>
            <input type="file" accept=".csv,.json,.jsonl,.txt" className="hidden" onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
          </label>
          <button onClick={useSample} className="group flex flex-col items-start gap-2 rounded-xl border border-line-strong bg-surface-2 p-4 text-left transition-colors hover:border-agent">
            <span className="grid h-10 w-10 place-items-center rounded-lg border border-line bg-surface-1"><FlaskConical className="h-4 w-4 text-verified" /></span>
            <span className="text-sm font-medium text-ink">Use the Northstar export</span>
            <span className="text-[11px] text-ink-mut">A deliberately messy real-shaped export — try the flow instantly.</span>
          </button>
        </div>
        {profiles.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-4">
            <span className="label">Reuse a saved mapping</span>
            <select value={profileId} onChange={(e) => setProfileId(e.target.value)}
              className="h-9 rounded-[10px] border border-line bg-surface-2 px-3 text-xs text-ink outline-none focus:border-agent/50">
              <option value="">Propose a fresh mapping</option>
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>{p.name} · {p.mapped_columns} cols ({p.source_filename})</option>
              ))}
            </select>
            {profileId && <span className="text-[11px] text-verified">a confirmed mapping will be reused</span>}
          </div>
        )}
        {busy && <div className="mt-4 flex items-center gap-2 text-sm text-ink-mut"><Loader2 className="h-4 w-4 animate-spin" /> Analyzing — detecting schema, proposing mapping…</div>}
        {err && <div className="mt-4 text-sm text-failure">Could not analyze: {err}</div>}
      </section>

      {data && (
        <>
          {/* summary banner */}
          <section className={`mt-4 rounded-xl border p-4 ${data.reconstruction.false_closure_detected ? "border-failure/40 bg-failure-soft" : "border-line bg-surface-1"}`}>
            <div className="flex items-start gap-3">
              {data.reconstruction.false_closure_detected ? <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-failure" /> : <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-verified" />}
              <div>
                <p className="text-sm text-ink">{data.reconstruction.summary}</p>
                <p className="mt-1 text-[11px] text-ink-mut">
                  {data.filename} · {data.format.toUpperCase()} · {data.row_count} rows · {data.mapped_count}/{data.column_count} columns mapped
                </p>
              </div>
            </div>
          </section>

          <div className="mt-4 grid gap-4 lg:grid-cols-[1.3fr_1fr]">
            {/* mapping studio */}
            <section className="alive rounded-2xl border border-line bg-surface-1 p-5">
              <SectionLabel className="mb-1">Mapping Studio</SectionLabel>
              <p className="mb-3 text-[11px] text-ink-mut">The AI proposes; confirm each column before a mission is created.</p>
              <div className="space-y-1.5">
                {data.mappings.map((m) => (
                  <div key={m.column} className="flex items-center gap-2 rounded-lg border border-line bg-surface-2 px-3 py-2 text-xs">
                    <span className="mono w-32 shrink-0 truncate text-ink" title={m.column}>{m.column}</span>
                    <ArrowRight className="h-3 w-3 shrink-0 text-ink-faint" />
                    {m.target_field ? (
                      <span className="mono flex-1 truncate text-agent">{m.target_event}.{m.target_field}</span>
                    ) : (
                      <span className="flex-1 text-ink-mut">unmapped</span>
                    )}
                    <span className="hidden shrink-0 text-[10px] text-ink-faint sm:inline">{m.samples.slice(0, 2).join(", ")}</span>
                    <ConfidenceChip c={m.confidence} />
                  </div>
                ))}
              </div>
            </section>

            {/* readiness */}
            <section className="alive rounded-2xl border border-line bg-surface-1 p-5">
              <SectionLabel className="mb-3">Data Readiness</SectionLabel>
              <div className="flex items-center gap-4">
                <ReadinessRing score={data.readiness.score} verdict={data.readiness.verdict} />
                <div className="flex-1 space-y-1">
                  {data.readiness.dimensions.map((d) => (
                    <div key={d.name} className="flex items-center gap-1.5 text-[11px]">
                      {d.status === "pass" ? <CheckCircle2 className="h-3 w-3 text-verified" /> : d.status === "warn" ? <AlertTriangle className="h-3 w-3 text-warning" /> : <MinusCircle className="h-3 w-3 text-failure" />}
                      <span className="text-ink-mut">{d.name}</span>
                    </div>
                  ))}
                </div>
              </div>
              {data.readiness.blocked.length > 0 && (
                <div className="mt-3 rounded-lg border border-failure/40 bg-failure-soft p-2 text-[11px] text-failure">
                  <div className="mb-1 font-semibold uppercase tracking-wide">Blocked</div>
                  {data.readiness.blocked.map((b, i) => <div key={i}>✕ {b}</div>)}
                </div>
              )}
              {data.readiness.warnings.length > 0 && (
                <div className="mt-2 space-y-0.5 text-[11px] text-warning">
                  {data.readiness.warnings.map((w, i) => <div key={i}>! {w}</div>)}
                </div>
              )}
            </section>
          </div>

          {/* reconstruction */}
          <section className="alive mt-4 rounded-2xl border border-line bg-surface-1 p-5">
            <div className="flex items-center gap-2">
              <BrainCircuit className="h-4 w-4 text-agent" aria-hidden />
              <SectionLabel className="mb-0">Incident Reconstruction</SectionLabel>
              <span className="text-[11px] text-ink-mut">provenance-tagged · advisory</span>
            </div>
            <ol className="mt-4 space-y-2">
              {data.reconstruction.entries.map((e, i) => {
                const meta = KIND_META[e.kind] ?? { tone: "steel" as Tone, label: e.kind };
                return (
                  <li key={i} className="rounded-lg border border-line bg-surface-2 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={meta.tone}>{meta.label}</Badge>
                      {e.at && <span className="mono text-[11px] text-ink-mut">{new Date(e.at).toLocaleString(undefined, { hour: "2-digit", minute: "2-digit", month: "short", day: "numeric" })}</span>}
                      <span className="text-sm text-ink">{e.label}</span>
                    </div>
                    {e.detail && <p className="mt-1 text-[11px] text-ink-mut">{e.detail}</p>}
                  </li>
                );
              })}
            </ol>

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
              <p className="max-w-md text-[11px] text-ink-mut">{data.basis}</p>
              <button onClick={createMission} disabled={creating}
                className="glow-agent inline-flex h-10 items-center gap-2 rounded-[10px] bg-agent px-4 text-sm font-semibold text-black transition-transform hover:scale-[1.02] disabled:opacity-60">
                {creating ? <><Loader2 className="h-4 w-4 animate-spin" /> Creating mission…</> : <><Rocket className="h-4 w-4" /> Create recovery mission</>}
              </button>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function ConfidenceChip({ c }: { c: number }) {
  if (c <= 0) return <span className="flex items-center gap-1 text-[10px] text-ink-faint"><HelpCircle className="h-3 w-3" /> —</span>;
  const tone = c >= 0.8 ? "text-verified" : c >= 0.5 ? "text-agent" : "text-warning";
  return <span className={`mono shrink-0 text-[10px] ${tone}`}>{Math.round(c * 100)}%</span>;
}

function ReadinessRing({ score, verdict }: { score: number; verdict: string }) {
  const R = 26, C = 2 * Math.PI * R;
  const col = verdict === "blocked" ? "var(--failure)" : verdict === "ready" ? "var(--verified)" : "var(--warning)";
  return (
    <svg viewBox="0 0 72 72" className="h-20 w-20 shrink-0" role="img" aria-label={`Data readiness ${score}%`}>
      <circle cx="36" cy="36" r={R} fill="none" stroke="var(--line)" strokeWidth="6" />
      <circle cx="36" cy="36" r={R} fill="none" stroke={col} strokeWidth="6" strokeLinecap="round"
        strokeDasharray={C} strokeDashoffset={C * (1 - score / 100)} transform="rotate(-90 36 36)" style={{ transition: "stroke-dashoffset 1s ease" }} />
      <text x="36" y="34" textAnchor="middle" className="mono" fontSize="16" fontWeight="700" fill="var(--ink-hi)">{score}</text>
      <text x="36" y="48" textAnchor="middle" fontSize="8" fill="var(--ink-mut)" letterSpacing="1">{verdict.toUpperCase()}</text>
    </svg>
  );
}
