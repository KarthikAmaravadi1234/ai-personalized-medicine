import { mockAsk, mockChat, mockDetail, mockPatients, mockRisk, mockSearch } from "./mock";
import type {
  AskResponse,
  ChatResponse,
  Health,
  PatientDetail,
  PatientSummary,
  RiskResult,
  SearchHit,
  UploadResult,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE_URL as string) || "http://localhost:8000";
const USE_MOCK = (import.meta.env.VITE_USE_MOCK as string) === "true";
const TIMEOUT_MS = 30_000;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const resp = await fetch(`${BASE}${path}`, { ...init, signal: controller.signal });
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
    return (await resp.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

/** Health reflects real backend reachability — never mocked. */
export async function getHealth(): Promise<Health | null> {
  try {
    return await request<Health>("/health");
  } catch {
    return null;
  }
}

export async function listPatients(limit = 200): Promise<PatientSummary[]> {
  try {
    return await request<PatientSummary[]>(`/patients?limit=${limit}`);
  } catch (err) {
    if (USE_MOCK) return mockPatients;
    return [];
  }
}

export async function getPatient(id: number): Promise<PatientDetail | null> {
  try {
    return await request<PatientDetail>(`/patients/${id}`);
  } catch {
    if (USE_MOCK) return mockDetail;
    return null;
  }
}

export async function getRisk(id: number): Promise<RiskResult | null> {
  try {
    return await request<RiskResult>(`/patients/${id}/risk`);
  } catch {
    if (USE_MOCK) return mockRisk;
    return null;
  }
}

export async function uploadCsv(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadResult>("/patients/upload", { method: "POST", body: form });
}

export async function uploadPdf(file: File): Promise<PatientDetail> {
  const form = new FormData();
  form.append("file", file);
  return request<PatientDetail>("/patients/upload/pdf", { method: "POST", body: form });
}

export async function chat(patientId: number, message: string): Promise<ChatResponse> {
  try {
    return await request<ChatResponse>("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patient_id: patientId, message }),
    });
  } catch (err) {
    if (USE_MOCK) return { ...mockChat, patient_id: patientId };
    throw err;
  }
}

export async function knowledgeSearch(q: string, topK = 5): Promise<SearchHit[]> {
  try {
    return await request<SearchHit[]>(`/knowledge/search?q=${encodeURIComponent(q)}&top_k=${topK}`);
  } catch {
    if (USE_MOCK) return mockSearch;
    return [];
  }
}

export async function knowledgeAsk(q: string, topK = 3): Promise<AskResponse> {
  try {
    return await request<AskResponse>(`/knowledge/ask?q=${encodeURIComponent(q)}&top_k=${topK}`);
  } catch (err) {
    if (USE_MOCK) return { ...mockAsk, query: q };
    throw err;
  }
}

export const apiMeta = { baseUrl: BASE, useMock: USE_MOCK };
