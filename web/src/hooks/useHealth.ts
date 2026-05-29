import { useEffect, useState } from "react";
import { getHealth } from "../lib/api";
import type { Health } from "../lib/types";

export function useHealth(pollMs = 15_000) {
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const tick = async () => {
      const h = await getHealth();
      if (active) {
        setHealth(h);
        setLoading(false);
      }
    };
    tick();
    const id = setInterval(tick, pollMs);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [pollMs]);

  return { health, loading, offline: !loading && health === null };
}
