"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Bot, Loader2, Send, Sparkles, User } from "lucide-react";
import { api } from "@/lib/api";
import { useMe } from "@/lib/hooks";
import type { AskResult } from "@/lib/types";

type Msg = { who: "you" | "agent"; text: string; res?: AskResult };

const STARTERS = ["What's blocking closure?", "Can we close it now?", "Did it relapse?", "What do I do next?"];

export function MissionQA({ incidentId }: { incidentId: string }) {
  const { data: me } = useMe();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  const send = async (q: string) => {
    const question = q.trim();
    if (!question || busy) return;
    setInput("");
    setMsgs((m) => [...m, { who: "you", text: question }]);
    setBusy(true);
    try {
      const res = await api.ask(incidentId, { question, role: me?.role });
      setMsgs((m) => [...m, { who: "agent", text: res.answer, res }]);
    } catch {
      setMsgs((m) => [...m, { who: "agent", text: "I couldn't reach the deterministic facts to answer that. Try again." }]);
    } finally { setBusy(false); }
  };

  const last = [...msgs].reverse().find((m) => m.who === "agent");
  const chips = last?.res?.suggestions ?? STARTERS;

  return (
    <section className="flex h-[70vh] flex-col rounded-xl border border-line bg-surface-1">
      <div className="flex items-center gap-2 border-b border-line px-5 py-3">
        <span className="grid h-8 w-8 place-items-center rounded-[10px] bg-agent-soft text-agent"><Bot className="h-4 w-4" /></span>
        <div>
          <div className="text-sm font-semibold text-ink-hi">Ask the agent</div>
          <div className="text-[11px] text-ink-mut">Advisory · grounded in the deterministic facts, cited · the agent explains, the evaluator decides</div>
        </div>
        {me?.role && <span className="label ml-auto">as {me.role.replace("_", " ")}</span>}
      </div>

      {/* transcript */}
      <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
        {msgs.length === 0 && (
          <div className="grid h-full place-items-center text-center">
            <div>
              <Sparkles className="mx-auto mb-2 h-6 w-6 text-agent" />
              <p className="text-sm text-ink-mut">Ask anything about this mission — what&apos;s blocking it, whether it can close, why it reopened.</p>
              <p className="mt-1 text-[11px] text-ink-faint">Every answer is traceable to the spine, the disposition gate, and the evaluator.</p>
            </div>
          </div>
        )}
        {msgs.map((m, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
            className={`flex gap-2.5 ${m.who === "you" ? "flex-row-reverse" : ""}`}>
            <span className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full ${m.who === "you" ? "bg-surface-3 text-ink-mut" : "bg-agent-soft text-agent"}`}>
              {m.who === "you" ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
            </span>
            <div className={`max-w-[80%] ${m.who === "you" ? "text-right" : ""}`}>
              <div className={`inline-block rounded-xl px-3.5 py-2.5 text-sm ${m.who === "you" ? "bg-agent text-black" : "border border-line bg-canvas/60 text-ink"}`}>
                {m.text}
              </div>
              {m.res && m.res.citations.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {m.res.citations.map((c) => (
                    <Link key={c.path} href={c.path}
                      className="inline-flex items-center gap-1 rounded-pill border border-line bg-surface-2 px-2 py-0.5 text-[11px] text-ink-mut transition-colors hover:border-agent/50 hover:text-agent">
                      {c.surface} <ArrowRight className="h-3 w-3" />
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        ))}
        {busy && (
          <div className="flex items-center gap-2 text-xs text-ink-mut"><Loader2 className="h-3.5 w-3.5 animate-spin" /> consulting the deterministic facts…</div>
        )}
        <div ref={endRef} />
      </div>

      {/* suggestion chips */}
      <div className="flex flex-wrap gap-1.5 border-t border-line px-5 pt-3">
        {chips.map((c) => (
          <button key={c} onClick={() => send(c)} disabled={busy}
            className="rounded-pill border border-line px-2.5 py-1 text-[11px] text-ink-mut transition-colors hover:border-agent/50 hover:text-agent disabled:opacity-50">
            {c}
          </button>
        ))}
      </div>

      {/* input */}
      <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex items-center gap-2 px-5 py-3">
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about this mission…"
          className="h-10 flex-1 rounded-[10px] border border-line bg-canvas/60 px-3 text-sm text-ink outline-none placeholder:text-ink-faint focus:border-agent/50" />
        <button type="submit" disabled={busy || !input.trim()}
          className="grid h-10 w-10 place-items-center rounded-[10px] bg-agent text-black transition-transform hover:scale-[1.03] disabled:opacity-50">
          <Send className="h-4 w-4" />
        </button>
      </form>
    </section>
  );
}
