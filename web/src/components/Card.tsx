import type { ReactNode } from "react";
import { cn } from "../lib/cn";

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "rounded-3xl border border-white/60 bg-white p-6 shadow-soft dark:border-slate-800 dark:bg-slate-900",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div>
      <h2 className="text-3xl font-extrabold tracking-tight">{title}</h2>
      {subtitle && <p className="mt-1 text-slate-500 dark:text-slate-400">{subtitle}</p>}
    </div>
  );
}
