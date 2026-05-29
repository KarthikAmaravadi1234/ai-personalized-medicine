import { Cake, Cpu, Scale, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Hero } from "../components/Hero";
import { KpiCard } from "../components/KpiCard";
import { useHealth } from "../hooks/useHealth";
import { listPatients } from "../lib/api";
import type { PatientSummary } from "../lib/types";

const LLM_LABEL: Record<string, string> = {
  openai: "OpenAI",
  local_fallback: "Local (fallback)",
  local: "Local",
};

export default function Dashboard() {
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const { health, offline } = useHealth();

  useEffect(() => {
    listPatients().then((p) => {
      setPatients(p);
      setLoading(false);
    });
  }, []);

  const total = patients.length;
  const ages = patients.map((p) => p.age).filter((a): a is number => typeof a === "number");
  const avgAge = ages.length ? Math.round(ages.reduce((a, b) => a + b, 0) / ages.length) : 0;
  const males = patients.filter((p) => (p.sex || "").toLowerCase() === "male").length;
  const females = patients.filter((p) => (p.sex || "").toLowerCase() === "female").length;
  const aiEngine = offline || !health ? "—" : LLM_LABEL[health.llm_mode] ?? "Unknown";

  return (
    <div className="space-y-8">
      <h2 className="text-3xl font-extrabold tracking-tight">Dashboard</h2>

      <Hero />

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Total patients"
          value={loading ? "…" : String(total)}
          icon={Users}
          gradient="bg-gradient-to-br from-indigo-50 to-violet-50 dark:from-slate-900 dark:to-slate-800"
        />
        <KpiCard
          label="Average age"
          value={avgAge ? String(avgAge) : "0"}
          sub="yrs"
          icon={Cake}
          gradient="bg-gradient-to-br from-violet-50 to-fuchsia-50 dark:from-slate-900 dark:to-slate-800"
        />
        <KpiCard
          label="Cohort split"
          value={`${males} / ${females}`}
          sub="male / female"
          icon={Scale}
          gradient="bg-gradient-to-br from-cyan-50 to-teal-50 dark:from-slate-900 dark:to-slate-800"
        />
        <KpiCard
          label="AI engine"
          value={aiEngine}
          icon={Cpu}
          gradient="bg-gradient-to-br from-pink-50 to-rose-50 dark:from-slate-900 dark:to-slate-800"
        />
      </div>

      <RecentPatients patients={patients} loading={loading} />
    </div>
  );
}

function RecentPatients({ patients, loading }: { patients: PatientSummary[]; loading: boolean }) {
  const recent = [...patients].slice(-8).reverse();
  return (
    <div className="rounded-3xl border border-white/60 bg-white p-6 shadow-soft dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold">Recent patients</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">Latest 8 records in the cohort</p>
        </div>
        <Link
          to="/patients"
          className="text-sm font-semibold text-brand-indigo transition hover:opacity-80"
        >
          View all →
        </Link>
      </div>

      <div className="mt-4 border-t border-slate-100 pt-4 dark:border-slate-800">
        {loading ? (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-10 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
            ))}
          </div>
        ) : recent.length === 0 ? (
          <div className="py-10 text-center">
            <p className="text-base font-bold">No data yet</p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Once your backend is reachable, patients will appear here.
            </p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="pb-2 font-semibold">ID</th>
                <th className="pb-2 font-semibold">Name</th>
                <th className="pb-2 font-semibold">Sex</th>
                <th className="pb-2 font-semibold">Age</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((p) => (
                <tr key={p.id} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="py-2.5 font-medium text-slate-400">#{p.id}</td>
                  <td className="py-2.5 font-semibold">{p.name || "Unnamed"}</td>
                  <td className="py-2.5 capitalize text-slate-500 dark:text-slate-400">{p.sex || "—"}</td>
                  <td className="py-2.5 text-slate-500 dark:text-slate-400">{p.age ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
