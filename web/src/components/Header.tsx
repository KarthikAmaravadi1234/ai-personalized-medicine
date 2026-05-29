import { Dna, Moon, Sun } from "lucide-react";
import { useTheme } from "../hooks/useTheme";
import { StatusPills } from "./StatusPills";

export function Header() {
  const { theme, toggle } = useTheme();
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200/70 bg-white/80 px-5 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/70">
      <div className="flex items-center gap-3">
        <div className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-brand-indigo to-brand-violet text-white shadow-glow">
          <Dna size={22} />
        </div>
        <div className="leading-tight">
          <div className="text-lg font-extrabold tracking-tight">MediMind AI</div>
          <div className="text-xs text-slate-500 dark:text-slate-400">Evidence-based</div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <StatusPills />
        <button
          onClick={toggle}
          aria-label="Toggle theme"
          className="grid h-9 w-9 place-items-center rounded-full border border-slate-200 text-slate-500 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
        </button>
      </div>
    </header>
  );
}
