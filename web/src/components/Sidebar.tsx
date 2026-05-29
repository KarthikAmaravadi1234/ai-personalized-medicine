import { BookOpen, LayoutDashboard, MessageSquare, Stethoscope, Users } from "lucide-react";
import { NavLink } from "react-router-dom";
import { cn } from "../lib/cn";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/patients", label: "Patients", icon: Users },
  { to: "/patient", label: "Patient detail", icon: Stethoscope },
  { to: "/chat", label: "Chat", icon: MessageSquare },
  { to: "/knowledge", label: "Knowledge", icon: BookOpen },
];

export function Sidebar() {
  return (
    <aside className="hidden w-60 shrink-0 border-r border-slate-200/70 bg-white/50 px-3 py-5 backdrop-blur md:block dark:border-slate-800 dark:bg-slate-900/40">
      <nav className="space-y-1">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-semibold transition",
                isActive
                  ? "bg-gradient-to-r from-brand-indigo to-brand-violet text-white shadow-glow"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
              )
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-8 rounded-2xl border border-slate-200/70 bg-white/70 p-4 text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900/50 dark:text-slate-400">
        <p className="font-semibold text-slate-700 dark:text-slate-200">Grounded by design</p>
        <p className="mt-1 leading-relaxed">
          Every answer cites its sources and passes safety guardrails.
        </p>
      </div>
    </aside>
  );
}
