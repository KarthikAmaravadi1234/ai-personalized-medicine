const LEVEL_COLOR: Record<string, string> = {
  high: "#e11d48",
  moderate: "#d97706",
  low: "#059669",
};

/** Semicircular gauge showing a 0–100% probability, colored by risk level. */
export function RiskGauge({ probability, level }: { probability: number; level: string }) {
  const pct = Math.max(0, Math.min(1, probability));
  const color = LEVEL_COLOR[level.toLowerCase()] ?? "#6366f1";

  const R = 80;
  const CX = 100;
  const CY = 100;
  const circumference = Math.PI * R; // half circle
  const dash = circumference * pct;

  return (
    <div className="relative flex flex-col items-center">
      <svg viewBox="0 0 200 110" className="w-56">
        <path
          d={`M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}`}
          fill="none"
          stroke="currentColor"
          className="text-slate-200 dark:text-slate-700"
          strokeWidth="14"
          strokeLinecap="round"
        />
        <path
          d={`M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}`}
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference}`}
        />
      </svg>
      <div className="-mt-10 text-center">
        <div className="text-4xl font-extrabold" style={{ color }}>
          {Math.round(pct * 100)}%
        </div>
        <div
          className="mt-1 inline-block rounded-full px-3 py-0.5 text-xs font-bold uppercase tracking-wide"
          style={{ color, backgroundColor: `${color}1a` }}
        >
          {level} risk
        </div>
      </div>
    </div>
  );
}
