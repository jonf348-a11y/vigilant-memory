import type { Grant, SearchJob, DashboardStats, ChatResponse } from "./types";

const BASE = "/api";

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  // Stats
  getStats: () => req<DashboardStats>("/stats"),

  // Grants
  listGrants: (status?: string) =>
    req<Grant[]>(`/grants${status ? `?status=${status}` : ""}`),
  getGrant: (id: number) => req<Grant>(`/grants/${id}`),
  updateGrant: (id: number, data: Partial<Grant>) =>
    req<Grant>(`/grants/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteGrant: (id: number) =>
    req<void>(`/grants/${id}`, { method: "DELETE" }),

  // Search
  startSearch: (focusAreas: string[]) =>
    req<{ job_id: number; status: string }>("/search", {
      method: "POST",
      body: JSON.stringify({ focus_areas: focusAreas }),
    }),
  getSearchStatus: (jobId: number) => req<SearchJob>(`/search/${jobId}`),

  // Application helper
  sendChat: (grantId: number, message: string, sessionId?: number) =>
    req<ChatResponse>("/apply/chat", {
      method: "POST",
      body: JSON.stringify({ grant_id: grantId, message, session_id: sessionId }),
    }),
  getChatHistory: (sessionId: number) =>
    req<{ messages: { role: string; content: string }[] }>(`/apply/sessions/${sessionId}`),
};
