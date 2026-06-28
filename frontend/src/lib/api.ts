import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 30_000,
});

export type TaskStatus = "pending" | "running" | "succeeded" | "failed";

export interface UsageInfo {
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  cost_usd: number;
}

export interface TaskRecord {
  id: string;
  prompt: string;
  status: TaskStatus;
  agent?: string;
  result_text: string | null;
  result_path: string | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
  params?: Record<string, unknown> | null;
  usage?: UsageInfo | null;
}

export interface MonthlyUsage {
  month: string;
  total_cost_usd: number;
  budget_usd: number;
  budget_remaining_usd: number;
  total_input_tokens: number;
  total_output_tokens: number;
  request_count: number;
}

export type PlanType = "software_roadmap" | "research_plan" | "prd";

export interface CreateTaskPayload {
  prompt: string;
}

export interface CreateResearchPayload {
  prompt: string;
  urls: string[];
}

export interface CreatePlanPayload {
  prompt: string;
  plan_type: PlanType;
  urls?: string[];
  images?: File[];
  texts?: File[];
}

export interface TaskAccepted {
  task_id: string;
  job_id?: string;
  status: TaskStatus;
  plan_type?: PlanType;
}

export const apiClient = {
  health: () => api.get<{ status: string }>("/health").then((r) => r.data),

  listTasks: (limit = 50) =>
    api.get<TaskRecord[]>("/tasks", { params: { limit } }).then((r) => r.data),

  getTask: (id: string) =>
    api.get<TaskRecord>(`/tasks/${id}`).then((r) => r.data),

  createTask: (payload: CreateTaskPayload) =>
    api.post<TaskRecord>("/tasks", payload).then((r) => r.data),

  getResearch: (id: string) =>
    api.get<TaskRecord>(`/research/${id}`).then((r) => r.data),

  createResearch: (payload: CreateResearchPayload) =>
    api.post<TaskAccepted>("/research", payload).then((r) => r.data),

  getPlan: (id: string) =>
    api.get<TaskRecord>(`/plan/${id}`).then((r) => r.data),

  createPlan: (payload: CreatePlanPayload) => {
    const form = new FormData();
    form.append("prompt", payload.prompt);
    form.append("plan_type", payload.plan_type);
    form.append("urls", JSON.stringify(payload.urls ?? []));
    for (const img of payload.images ?? []) {
      form.append("images", img, img.name);
    }
    for (const txt of payload.texts ?? []) {
      form.append("texts", txt, txt.name);
    }
    return api
      .post<TaskAccepted>("/plan", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },

  uploadUrl: (taskId: string, filename: string) =>
    `/api/plan/${taskId}/uploads/${encodeURIComponent(filename)}`,

  usage: () =>
    api.get<MonthlyUsage>("/usage/current-month").then((r) => r.data),
};
