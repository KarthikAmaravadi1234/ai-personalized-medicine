import { Search, Sparkles } from "lucide-react";
import { useState } from "react";
import { Card, PageHeader } from "../components/Card";
import { Pill } from "../components/Pill";
import { knowledgeAsk, knowledgeSearch } from "../lib/api";
import type { AskResponse, SearchHit } from "../lib/types";

type Mode = "ask" | "search";

export default function Knowledge() {
  const [query, setQuery] = useState("What does elevated LDL mean?");
  const [mode, setMode] = useState<Mode>("ask");
  const [busy, setBusy] = useState(false);
  const [ask, setAsk] = useState<AskResponse | null>(null);
  const [hits, setHits] = useState<SearchHit[] | null>(null);

  const go = async () => {
    if (!query.trim()) return;
    setBusy(true);
    setAsk(null);
    setHits(null);
    try {
      if (mode === "ask") setAsk(await knowledgeAsk(query));
      else setHits(await knowledgeSearch(query));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Knowledge" subtitle="Ask questions or semantically search the clinical library." />

      <Card>
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[240px]">
            <Search size={16} className="absolute left-3 top-3 text-slate-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && go()}
              placeholder="Search or ask a question…"
              className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-9 pr-3 text-sm outline-none focus:border-brand-indigo dark:border-slate-700 dark:bg-slate-800"
            />
          </div>

          <div className="flex rounded-xl border border-slate-200 p-1 dark:border-slate-700">
            {(["ask", "search"] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`rounded-lg px-4 py-1.5 text-sm font-semibold capitalize transition ${
                  mode === m
                    ? "bg-gradient-to-r from-brand-indigo to-brand-violet text-white"
                    : "text-slate-500 dark:text-slate-400"
                }`}
              >
                {m}
              </button>
            ))}
          </div>

          <button
            onClick={go}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-brand-indigo to-brand-violet px-5 py-2.5 text-sm font-semibold text-white shadow-glow transition hover:-translate-y-0.5 disabled:opacity-50"
          >
            <Sparkles size={15} /> {busy ? "…" : "Go"}
          </button>
        </div>
      </Card>

      {ask && (
        <Card>
          <p className="leading-relaxed">{ask.answer}</p>
          {ask.citations.length > 0 && (
            <div className="mt-4 border-t border-slate-100 pt-4 dark:border-slate-800">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Citations</p>
              {ask.citations.map((c, i) => (
                <p key={i} className="mb-1 text-sm text-slate-500 dark:text-slate-400">
                  <span className="font-semibold text-slate-700 dark:text-slate-200">{c.source}</span> · {c.excerpt}
                </p>
              ))}
            </div>
          )}
        </Card>
      )}

      {hits && (
        <div className="space-y-3">
          {hits.length === 0 && <p className="text-sm text-slate-400">No results.</p>}
          {hits.map((h, i) => (
            <Card key={i}>
              <div className="mb-2 flex items-center gap-2">
                <span className="font-bold">{h.source}</span>
                <Pill color="blue">score {h.score}</Pill>
              </div>
              <p className="text-sm text-slate-500 dark:text-slate-400">{h.text}</p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
