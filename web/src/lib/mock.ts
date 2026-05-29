import type { PatientDetail, PatientSummary, RiskResult } from "./types";

export const mockPatients: PatientSummary[] = [
  { id: 1, external_id: "P-1001", name: "Ava Thompson", sex: "female", age: 34 },
  { id: 2, external_id: "P-1002", name: "Marcus Reed", sex: "male", age: 58 },
  { id: 3, external_id: "P-1003", name: "Priya Nair", sex: "female", age: 45 },
  { id: 4, external_id: "P-1004", name: "Diego Alvarez", sex: "male", age: 62 },
  { id: 5, external_id: "P-1005", name: "Sofia Rossi", sex: "female", age: 29 },
  { id: 6, external_id: "P-1006", name: "James Okafor", sex: "male", age: 51 },
  { id: 7, external_id: "P-1007", name: "Lena Müller", sex: "female", age: 71 },
];

export const mockDetail: PatientDetail = {
  id: 2,
  external_id: "P-1002",
  name: "Marcus Reed",
  sex: "male",
  age: 58,
  height_cm: 178,
  weight_kg: 96,
  labs: [
    { test_name: "LDL Cholesterol", value: 168, unit: "mg/dL", flag: "high" },
    { test_name: "HDL Cholesterol", value: 38, unit: "mg/dL", flag: "low" },
    { test_name: "Triglycerides", value: 210, unit: "mg/dL", flag: "high" },
    { test_name: "HbA1c", value: 6.9, unit: "%", flag: "high" },
    { test_name: "Fasting Glucose", value: 118, unit: "mg/dL", flag: "high" },
  ],
  vitals: [
    { systolic_bp: 142, diastolic_bp: 91, heart_rate: 78, sleep_hours: 6.1 },
  ],
};

export const mockRisk: RiskResult = {
  patient_id: 2,
  condition: "type_2_diabetes",
  probability: 0.62,
  risk_level: "high",
  model_source: "logistic_regression_v1",
  imputed_features: [],
  contributions: [
    { feature: "HbA1c", value: 6.9, contribution: 0.31 },
    { feature: "BMI", value: 30.3, contribution: 0.18 },
    { feature: "Fasting Glucose", value: 118, contribution: 0.12 },
  ],
};

export const mockHealth = {
  status: "healthy" as const,
  database: "connected",
  llm_mode: "local" as const,
  openai: { available: true, cooldown_remaining_s: 0, last_reason: "" },
};

import type { AskResponse, ChatResponse, SearchHit } from "./types";

export const mockChat: ChatResponse = {
  patient_id: 2,
  answer:
    "Your recent labs show an elevated LDL cholesterol (168 mg/dL) and a borderline HbA1c (6.9%), " +
    "which together suggest increased cardiometabolic risk. Lifestyle changes and follow-up testing " +
    "are commonly recommended. This is educational information, not a diagnosis.",
  citations: [
    { source: "ldl_cholesterol.md", chunk_index: 0, excerpt: "LDL above 160 mg/dL is considered high…", score: 0.82 },
    { source: "hba1c.md", chunk_index: 1, excerpt: "An HbA1c of 5.7–6.4% indicates prediabetes…", score: 0.78 },
  ],
  tool_calls: [
    { tool: "get_patient_labs", args: { patient_id: 2 }, summary: "5 lab results" },
    { tool: "search_knowledge", args: { query: "LDL cholesterol; HbA1c" }, summary: "3 hits" },
  ],
  guardrail_notes: ["Added educational disclaimer."],
};

export const mockSearch: SearchHit[] = [
  { source: "ldl_cholesterol.md", chunk_index: 0, score: 0.82, text: "LDL cholesterol carries cholesterol to tissues; high levels raise cardiovascular risk." },
  { source: "hdl_cholesterol.md", chunk_index: 0, score: 0.61, text: "HDL helps remove cholesterol from the bloodstream; higher levels are protective." },
];

export const mockAsk: AskResponse = {
  query: "What does elevated LDL mean?",
  answer:
    "Elevated LDL cholesterol means more cholesterol is being carried to your arteries, which raises " +
    "the risk of plaque buildup and cardiovascular disease over time.",
  citations: [
    { source: "ldl_cholesterol.md", chunk_index: 0, excerpt: "LDL above 160 mg/dL is considered high…", score: 0.82 },
  ],
};
