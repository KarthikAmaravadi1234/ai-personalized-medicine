import { Cpu, Wifi, WifiOff } from "lucide-react";
import { useHealth } from "../hooks/useHealth";
import { Pill } from "./Pill";

const LLM_LABEL: Record<string, string> = {
  openai: "AI: OpenAI",
  local_fallback: "AI: Local fallback",
  local: "AI: Local",
};

export function StatusPills() {
  const { health, offline } = useHealth();

  if (offline || !health) {
    return (
      <div className="flex items-center gap-2">
        <Pill color="red">
          <WifiOff size={13} /> API offline
        </Pill>
        <Pill color="slate">
          <Cpu size={13} /> AI: —
        </Pill>
      </div>
    );
  }

  const apiColor = health.status === "healthy" ? "green" : "amber";
  const llmColor =
    health.llm_mode === "openai" ? "blue" : health.llm_mode === "local_fallback" ? "amber" : "slate";

  return (
    <div className="flex items-center gap-2">
      <Pill color={apiColor}>
        <Wifi size={13} /> API {health.status}
      </Pill>
      <Pill color={llmColor}>
        <Cpu size={13} /> {LLM_LABEL[health.llm_mode] ?? "AI: Unknown"}
      </Pill>
    </div>
  );
}
