import type { ReactNode } from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="app-bg flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex flex-1 flex-col">
          <div className="mx-auto w-full max-w-6xl flex-1 px-5 py-8 md:px-8">{children}</div>
          <footer className="border-t border-slate-200/70 py-5 text-center text-sm text-slate-400 dark:border-slate-800 dark:text-slate-500">
            Educational project — not for clinical use.
          </footer>
        </main>
      </div>
    </div>
  );
}
