export interface Health {
  status: "healthy" | "degraded";
  database: string;
  llm_mode: "openai" | "local_fallback" | "local";
  openai: {
    available: boolean;
    cooldown_remaining_s: number;
    last_reason: string;
  };
}

export interface PatientSummary {
  id: number;
  external_id?: string | null;
  name?: string | null;
  sex?: string | null;
  age?: number | null;
}

export interface LabResult {
  test_name: string;
  value: number;
  unit?: string | null;
  flag?: string | null;
}

export interface Vital {
  systolic_bp?: number | null;
  diastolic_bp?: number | null;
  heart_rate?: number | null;
  sleep_hours?: number | null;
}

export interface PatientDetail extends PatientSummary {
  height_cm?: number | null;
  weight_kg?: number | null;
  labs: LabResult[];
  vitals: Vital[];
}

export interface FeatureContribution {
  feature: string;
  value: number;
  contribution: number;
}

export interface RiskResult {
  patient_id: number;
  condition: string;
  probability: number;
  risk_level: "low" | "moderate" | "high" | string;
  model_source: string;
  imputed_features: string[];
  contributions: FeatureContribution[];
}

export interface Citation {
  source: string;
  chunk_index: number;
  excerpt: string;
  score: number;
}

export interface ToolCall {
  tool: string;
  args: Record<string, unknown>;
  summary: string;
}

export interface ChatResponse {
  patient_id: number;
  answer: string;
  citations: Citation[];
  tool_calls: ToolCall[];
  guardrail_notes: string[];
}

export interface SearchHit {
  source: string;
  chunk_index: number;
  score: number;
  text: string;
}

export interface AskResponse {
  query: string;
  answer: string;
  citations: Citation[];
}

export interface UploadResult {
  created: number;
  errors: unknown[];
}
