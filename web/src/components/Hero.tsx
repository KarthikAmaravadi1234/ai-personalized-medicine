import { ArrowRight, Brain, Database, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";

const FEATURES = [
  { icon: Database, label: "RAG knowledge base" },
  { icon: Brain, label: "ML risk scoring" },
  { icon: ShieldCheck, label: "Guardrailed AI agent" },
];

export function Hero() {
  const navigate = useNavigate();
  return (
    <section className="relative overflow-hidden rounded-3xl border border-white/60 bg-gradient-to-br from-indigo-50 via-white to-cyan-50 p-8 shadow-soft md:p-10 dark:border-slate-800 dark:from-slate-900 dark:via-slate-900 dark:to-slate-900">
      <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-brand-violet/10 blur-2xl" />
      <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
        <span className="h-2 w-2 rounded-full bg-emerald-500" /> Welcome back, clinician
      </span>

      <h1 className="mt-5 max-w-3xl text-4xl font-extrabold leading-tight tracking-tight md:text-5xl">
        Personalized medicine, <span className="text-gradient">grounded in evidence.</span>
      </h1>
      <p className="mt-4 max-w-2xl text-base leading-relaxed text-slate-500 dark:text-slate-400">
        Turn labs, vitals, and a curated clinical knowledge base into source-cited insights —
        powered by RAG, ML risk scoring, and a guardrailed AI agent.
      </p>

      <div className="mt-6 flex flex-wrap gap-2">
        {FEATURES.map(({ icon: Icon, label }) => (
          <span
            key={label}
            className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3.5 py-1.5 text-sm font-medium text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
          >
            <Icon size={15} className="text-brand-violet" /> {label}
          </span>
        ))}
      </div>

      <div className="mt-7 flex flex-wrap gap-3">
        <button
          onClick={() => navigate("/patients")}
          className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-brand-indigo to-brand-violet px-5 py-2.5 font-semibold text-white shadow-glow transition hover:-translate-y-0.5"
        >
          Upload patients <ArrowRight size={17} />
        </button>
        <button
          onClick={() => navigate("/chat")}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          Ask the AI agent
        </button>
      </div>
    </section>
  );
}
