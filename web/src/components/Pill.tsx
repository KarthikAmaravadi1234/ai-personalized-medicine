import type { ReactNode } from "react";
import { cn } from "../lib/cn";

type PillColor = "green" | "amber" | "red" | "blue" | "slate" | "violet";

const COLORS: Record<PillColor, string> = {
  green: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
  amber: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
  red: "bg-rose-100 text-rose-600 dark:bg-rose-500/15 dark:text-rose-300",
  blue: "bg-indigo-100 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300",
  slate: "bg-slate-100 text-slate-600 dark:bg-slate-700/50 dark:text-slate-300",
  violet: "bg-violet-100 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300",
};

export function Pill({
  children,
  color = "slate",
  className,
}: {
  children: ReactNode;
  color?: PillColor;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold",
        COLORS[color],
        className,
      )}
    >
      {children}
    </span>
  );
}
