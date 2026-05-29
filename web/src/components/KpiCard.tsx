import type { LucideIcon } from "lucide-react";

export function KpiCard({
  label,
  value,
  sub,
  icon: Icon,
  gradient,
}: {
  label: string;
  value: string;
  sub?: string;
  icon: LucideIcon;
  gradient: string;
}) {
  return (
    <div
      className={`relative overflow-hidden rounded-3xl border border-white/60 p-6 shadow-soft dark:border-slate-800 ${gradient}`}
    >
      <div className="flex items-start justify-between">
        <span className="text-sm font-medium text-slate-500 dark:text-slate-300">{label}</span>
        <span className="grid h-10 w-10 place-items-center rounded-full border border-slate-300/60 text-slate-500 dark:border-slate-600 dark:text-slate-300">
          <Icon size={18} />
        </span>
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-4xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          {value}
        </span>
        {sub && <span className="text-sm text-slate-500 dark:text-slate-400">{sub}</span>}
      </div>
    </div>
  );
}
