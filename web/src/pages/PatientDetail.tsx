import { Activity, HeartPulse } from "lucide-react";
import { useEffect, useState } from "react";
import { Card, PageHeader } from "../components/Card";
import { RiskGauge } from "../components/RiskGauge";
import { getPatient, getRisk, listPatients } from "../lib/api";
import type { PatientDetail as Detail, PatientSummary, RiskResult } from "../lib/types";

const FLAG_COLOR: Record<string, string> = {
  high: "text-rose-600 bg-rose-50 dark:bg-rose-500/10 dark:text-rose-300",
  low: "text-amber-600 bg-amber-50 dark:bg-amber-500/10 dark:text-amber-300",
  normal: "text-emerald-600 bg-emerald-50 dark:bg-emerald-500/10 dark:text-emerald-300",
};

export default function PatientDetail() {
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [risk, setRisk] = useState<RiskResult | null>(null);
  const [riskLoading, setRiskLoading] = useState(false);

  useEffect(() => {
    listPatients().then((p) => {
      setPatients(p);
      if (p.length) setSelected(p[0].id);
    });
  }, []);

  useEffect(() => {
    if (selected == null) return;
    setRisk(null);
    setDetail(null);
    getPatient(selected).then(setDetail);
  }, [selected]);

  const computeRisk = async () => {
    if (selected == null) return;
    setRiskLoading(true);
    setRisk(await getRisk(selected));
    setRiskLoading(false);
  };

  if (!patients.length) {
    return (
      <div className="space-y-6">
        <PageHeader title="Patient detail" />
        <Card>
          <p className="py-8 text-center text-sm text-slate-400">No patients yet. Upload some first.</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Patient detail" subtitle="Demographics, labs, vitals, and an ML risk estimate." />

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

      {detail && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Tile label="Name" value={detail.name || "—"} />
            <Tile label="Age" value={detail.age != null ? String(detail.age) : "—"} />
            <Tile label="Sex" value={detail.sex || "—"} />
            <Tile label="BMI" value={bmi(detail)} />
          </div>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <Card>
              <div className="mb-3 flex items-center gap-2">
                <Activity size={18} className="text-brand-violet" />
                <h3 className="font-bold">Labs</h3>
              </div>
              {detail.labs.length ? (
                <div className="space-y-2">
                  {detail.labs.map((lab, i) => (
                    <div key={i} className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800/60">
                      <span className="font-medium">{lab.test_name}</span>
                      <span className="flex items-center gap-2">
                        <span className="tabular-nums">{lab.value}{lab.unit}</span>
                        {lab.flag && (
                          <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${FLAG_COLOR[lab.flag] ?? FLAG_COLOR.normal}`}>
                            {lab.flag}
                          </span>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-400">No labs recorded.</p>
              )}
            </Card>

            <Card>
              <div className="mb-3 flex items-center gap-2">
                <HeartPulse size={18} className="text-brand-violet" />
                <h3 className="font-bold">Vitals</h3>
              </div>
              {detail.vitals.length ? (
                (() => {
                  const v = detail.vitals[detail.vitals.length - 1];
                  return (
                    <div className="grid grid-cols-2 gap-3">
                      <Vital label="Blood pressure" value={`${v.systolic_bp ?? "—"}/${v.diastolic_bp ?? "—"}`} unit="mmHg" />
                      <Vital label="Heart rate" value={`${v.heart_rate ?? "—"}`} unit="bpm" />
                      <Vital label="Sleep" value={`${v.sleep_hours ?? "—"}`} unit="h" />
                    </div>
                  );
                })()
              ) : (
                <p className="text-sm text-slate-400">No vitals recorded.</p>
              )}
            </Card>
          </div>

          <Card>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="font-bold">Diabetes risk</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  A statistical estimate from an educational model — not a diagnosis.
                </p>
              </div>
              <button
                onClick={computeRisk}
                disabled={riskLoading}
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-brand-indigo to-brand-violet px-4 py-2 text-sm font-semibold text-white shadow-glow transition hover:-translate-y-0.5 disabled:opacity-50"
              >
                {riskLoading ? "Computing…" : "Compute risk"}
              </button>
            </div>

            {risk && (
              <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-[auto,1fr] md:items-center">
                <RiskGauge probability={risk.probability} level={risk.risk_level} />
                <div>
                  <p className="mb-3 text-xs uppercase tracking-wide text-slate-400">
                    Top contributing features · {risk.condition} · {risk.model_source}
                  </p>
                  <ContributionBars risk={risk} />
                </div>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}

function ContributionBars({ risk }: { risk: RiskResult }) {
  const max = Math.max(...risk.contributions.map((c) => Math.abs(c.contribution)), 0.0001);
  return (
    <div className="space-y-2.5">
      {risk.contributions.map((c) => (
        <div key={c.feature}>
          <div className="mb-1 flex justify-between text-sm">
            <span className="font-medium">{c.feature}</span>
            <span className="tabular-nums text-slate-400">{c.value}</span>
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
            <div
              className="h-full rounded-full bg-gradient-to-r from-brand-indigo to-brand-violet"
              style={{ width: `${(Math.abs(c.contribution) / max) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <Card className="p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-1 truncate text-xl font-extrabold capitalize">{value}</div>
    </Card>
  );
}

function Vital({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div className="rounded-xl bg-slate-50 px-3 py-2.5 dark:bg-slate-800/60">
      <div className="text-xs text-slate-500 dark:text-slate-400">{label}</div>
      <div className="text-lg font-bold">
        {value} <span className="text-xs font-normal text-slate-400">{unit}</span>
      </div>
    </div>
  );
}

function bmi(d: Detail): string {
  if (!d.height_cm || !d.weight_kg) return "—";
  const m = d.height_cm / 100;
  return (d.weight_kg / (m * m)).toFixed(1);
}
