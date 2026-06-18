export type GrantStatus =
  | "discovered"
  | "reviewing"
  | "applied"
  | "awarded"
  | "rejected"
  | "not_eligible";

export interface Grant {
  id: number;
  title: string;
  funder: string;
  description: string;
  url: string | null;
  deadline: string | null;
  max_amount: number | null;
  min_amount: number | null;
  focus_areas: string[];
  status: GrantStatus;
  eligibility_notes: string | null;
  application_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface SearchJob {
  job_id: number;
  status: "pending" | "running" | "complete" | "failed";
  grants_found: number;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface DashboardStats {
  total_grants: number;
  by_status: Record<string, number>;
  total_potential_value: number;
  recent_searches: {
    job_id: number;
    status: string;
    grants_found: number;
    created_at: string;
  }[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  session_id: number;
  reply: string;
  message_count: number;
}
