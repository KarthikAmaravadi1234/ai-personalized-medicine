import { CheckCircle2, FileSpreadsheet, FileText, Search, Upload, XCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Card, PageHeader } from "../components/Card";
import { listPatients, uploadCsv, uploadPdf } from "../lib/api";
import type { PatientSummary } from "../lib/types";

type Notice = { kind: "success" | "error"; text: string } | null;

export default function Patients() {
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");

  const refresh = () => {
    setLoading(true);
    listPatients().then((p) => {
      setPatients(p);
      setLoading(false);
    });
  };
  useEffect(refresh, []);

  const filtered = patients.filter((p) =>
    `${p.id} ${p.name ?? ""} ${p.sex ?? ""}`.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <div className="space-y-6">
      <PageHeader title="Patients" subtitle="Upload patient data and browse the cohort." />

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        <UploadCard
          title="Upload patient CSV"
          hint="A CSV with patient demographics, labs, and vitals."
          accept=".csv"
          icon={FileSpreadsheet}
          onUpload={async (file) => {
            const res = await uploadCsv(file);
            refresh();
            return `Created ${res.created} patient(s)${res.errors.length ? `, ${res.errors.length} row error(s)` : ""}.`;
          }}
        />
        <UploadCard
          title="Upload PDF lab report"
          hint="A lab report PDF; recognized values become a new patient."
          accept=".pdf"
          icon={FileText}
          onUpload={async (file) => {
            const res = await uploadPdf(file);
            refresh();
            return `Created patient #${res.id}.`;
          }}
        />
      </div>

      <Card>
        <div className="mb-4 flex items-center justify-between gap-3">
          <h3 className="text-lg font-bold">Cohort</h3>
          <div className="relative">
            <Search size={15} className="absolute left-3 top-2.5 text-slate-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search…"
              className="w-48 rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-brand-indigo dark:border-slate-700 dark:bg-slate-800"
            />
          </div>
        </div>

        {loading ? (
          <p className="py-8 text-center text-sm text-slate-400">Loading…</p>
        ) : filtered.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-400">No patients found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
                  <th className="pb-2 font-semibold">ID</th>
                  <th className="pb-2 font-semibold">External ID</th>
                  <th className="pb-2 font-semibold">Name</th>
                  <th className="pb-2 font-semibold">Sex</th>
                  <th className="pb-2 font-semibold">Age</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((p) => (
                  <tr key={p.id} className="border-t border-slate-100 dark:border-slate-800">
                    <td className="py-2.5 font-medium text-slate-400">#{p.id}</td>
                    <td className="py-2.5 text-slate-500 dark:text-slate-400">{p.external_id || "—"}</td>
                    <td className="py-2.5 font-semibold">{p.name || "Unnamed"}</td>
                    <td className="py-2.5 capitalize text-slate-500 dark:text-slate-400">{p.sex || "—"}</td>
                    <td className="py-2.5 text-slate-500 dark:text-slate-400">{p.age ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

function UploadCard({
  title,
  hint,
  accept,
  icon: Icon,
  onUpload,
}: {
  title: string;
  hint: string;
  accept: string;
  icon: typeof Upload;
  onUpload: (file: File) => Promise<string>;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handle = async () => {
    if (!file) return;
    setBusy(true);
    setNotice(null);
    try {
      const msg = await onUpload(file);
      setNotice({ kind: "success", text: msg });
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
    } catch (err) {
      setNotice({ kind: "error", text: err instanceof Error ? err.message : "Upload failed." });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <div className="flex items-center gap-3">
        <span className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-brand-indigo to-brand-violet text-white shadow-glow">
          <Icon size={20} />
        </span>
        <div>
          <h3 className="font-bold">{title}</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">{hint}</p>
        </div>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        className="mt-4 block w-full text-sm text-slate-500 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-slate-700 hover:file:bg-slate-200 dark:file:bg-slate-800 dark:file:text-slate-200"
      />

      <button
        disabled={!file || busy}
        onClick={handle}
        className="mt-4 inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-brand-indigo to-brand-violet px-4 py-2 text-sm font-semibold text-white shadow-glow transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <Upload size={15} /> {busy ? "Uploading…" : "Upload"}
      </button>

      {notice && (
        <div
          className={`mt-3 flex items-start gap-2 rounded-xl px-3 py-2 text-sm ${
            notice.kind === "success"
              ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300"
              : "bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-300"
          }`}
        >
          {notice.kind === "success" ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
          <span>{notice.text}</span>
        </div>
      )}
    </Card>
  );
}
