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
  getQuota: () =>
    req<{
      currently_running: boolean;
      running_job_id: number | null;
      last_full_search_at: string | null;
      next_full_search_allowed_at: string | null;
      days_since_last: number | null;
      days_remaining: number | null;
      is_locked: boolean;
      total_grants_in_db: number;
    }>("/search/quota"),
  startSearch: (focusAreas: string[]) =>
    req<{ job_id: number; status: string }>("/search", {
      method: "POST",
      body: JSON.stringify({ focus_areas: focusAreas }),
    }),
  startTargetedSearch: (question: string) =>
    req<{ job_id: number; status: string }>("/search/targeted", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
  getRecentTargetedSearches: () =>
    req<{
      job_id: number;
      question: string;
      completed_at: string;
      days_since: number;
      days_remaining: number;
      grants_found: number;
    }[]>("/search/targeted/recent"),
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
