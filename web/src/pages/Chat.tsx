import { Bot, ChevronDown, Send, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Card, PageHeader } from "../components/Card";
import { chat, listPatients } from "../lib/api";
import type { Citation, PatientSummary, ToolCall } from "../lib/types";

interface Turn {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  toolCalls?: ToolCall[];
  guardrails?: string[];
}

export default function Chat() {
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [history, setHistory] = useState<Record<number, Turn[]>>({});
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listPatients().then((p) => {
      setPatients(p);
      if (p.length) setSelected(p[0].id);
    });
  }, []);

  const turns = selected != null ? history[selected] ?? [] : [];

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns.length, busy]);

  const send = async () => {
    if (!input.trim() || selected == null || busy) return;
    const message = input.trim();
    const pid = selected;
    setInput("");
    setHistory((h) => ({ ...h, [pid]: [...(h[pid] ?? []), { role: "user", content: message }] }));
    setBusy(true);
    try {
      const res = await chat(pid, message);
      setHistory((h) => ({
        ...h,
        [pid]: [
          ...(h[pid] ?? []),
          {
            role: "assistant",
            content: res.answer,
            citations: res.citations,
            toolCalls: res.tool_calls,
            guardrails: res.guardrail_notes,
          },
        ],
      }));
    } catch (err) {
      setHistory((h) => ({
        ...h,
        [pid]: [
          ...(h[pid] ?? []),
          { role: "assistant", content: `⚠️ ${err instanceof Error ? err.message : "Request failed."}` },
        ],
      }));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Chat" subtitle="Ask about a patient's data — grounded answers with citations." />

      {patients.length === 0 ? (
        <Card>
          <p className="py-8 text-center text-sm text-slate-400">Create a patient first.</p>
        </Card>
      ) : (
        <>
          <select
            value={selected ?? ""}
            onChange={(e) => setSelected(Number(e.target.value))}
            className="w-full max-w-sm rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium outline-none focus:border-brand-indigo dark:border-slate-700 dark:bg-slate-800"
          >
            {patients.map((p) => (
              <option key={p.id} value={p.id}>
                #{p.id} · {p.name || "Unnamed"}
              </option>
            ))}
          </select>

          <Card className="flex h-[55vh] flex-col p-0">
            <div className="flex-1 space-y-4 overflow-y-auto p-6">
              {turns.length === 0 && (
                <p className="mt-10 text-center text-sm text-slate-400">
                  Ask something like “What does my LDL mean?” or “What's my diabetes risk?”
                </p>
              )}
              {turns.map((t, i) => (
                <Message key={i} turn={t} />
              ))}
              {busy && (
                <div className="flex items-center gap-2 text-sm text-slate-400">
                  <Bot size={16} /> Thinking…
                </div>
              )}
              <div ref={endRef} />
            </div>

            <div className="flex items-center gap-2 border-t border-slate-100 p-3 dark:border-slate-800">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder="Ask about this patient's data…"
                className="flex-1 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-brand-indigo dark:border-slate-700 dark:bg-slate-800"
              />
              <button
                onClick={send}
                disabled={busy || !input.trim()}
                className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-r from-brand-indigo to-brand-violet text-white shadow-glow transition hover:-translate-y-0.5 disabled:opacity-50"
              >
                <Send size={17} />
              </button>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

function Message({ turn }: { turn: Turn }) {
  const isUser = turn.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <span
        className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${
          isUser ? "bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-200" : "bg-gradient-to-br from-brand-indigo to-brand-violet text-white"
        }`}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </span>
      <div className={`max-w-[80%] ${isUser ? "text-right" : ""}`}>
        <div
          className={`inline-block rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? "bg-brand-indigo text-white"
              : "bg-slate-50 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
          }`}
        >
          {turn.content}
        </div>
        {turn.guardrails && turn.guardrails.length > 0 && (
          <div className="mt-1 text-xs text-slate-400">🛡 {turn.guardrails.join(" · ")}</div>
        )}
        {turn.citations && turn.citations.length > 0 && (
          <Expander label={`Sources (${turn.citations.length})`}>
            {turn.citations.map((c, i) => (
              <p key={i} className="mb-1 text-xs text-slate-500 dark:text-slate-400">
                <span className="font-semibold">{c.source}</span> · {c.excerpt}
              </p>
            ))}
          </Expander>
        )}
        {turn.toolCalls && turn.toolCalls.length > 0 && (
          <Expander label={`Tool calls (${turn.toolCalls.length})`}>
            {turn.toolCalls.map((t, i) => (
              <p key={i} className="mb-1 font-mono text-xs text-slate-500 dark:text-slate-400">
                {t.tool} → {t.summary}
              </p>
            ))}
          </Expander>
        )}
      </div>
    </div>
  );
}

function Expander({ label, children }: { label: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-2 text-left">
      <button
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-1 text-xs font-semibold text-brand-indigo"
      >
        <ChevronDown size={13} className={`transition ${open ? "rotate-180" : ""}`} /> {label}
      </button>
      {open && <div className="mt-2 rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">{children}</div>}
    </div>
  );
}
