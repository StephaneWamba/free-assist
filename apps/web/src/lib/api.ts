import type { AnalysisResult } from "@/types/assistant"

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    keepalive: true,
    ...init,
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail ?? "API error")
  }
  return res.json() as Promise<T>
}

// ─── Types ──────────────────────────────────────────────────────────────────

export interface ModelInfo {
  id: string
  name: string
  type: "classifier" | "llm" | "embeddings"
  base_model: string
  hf_id: string | null
  task: string
  language: string
  params_m: number | null
  description: string
  status: "active" | "loading" | "not_loaded" | "standby"
  device: string | null
}

export interface ModelsResponse {
  ml_mode: "local" | "openai" | "none"
  device: string
  models: ModelInfo[]
}

export interface KBDoc {
  id: string
  title: string
  category: string
  category_label: string
  filename: string
  preview: string
  word_count: number
}

export interface KBDocFull extends KBDoc {
  content: string
}

export interface EvalScores {
  pertinence: number
  empathie: number
  exactitude: number
  actionnable: number
  justification: string
  overall: number
}

export interface KBListResponse {
  total: number
  categories: { id: string; label: string }[]
  docs: KBDoc[]
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface DashboardKPIs {
  total_tickets: number
  resolution_rate: number
  median_latency_ms: number
  avg_latency_ms: number
  avg_confidence: number
}

export interface RecentTicket {
  id: number
  intent: string
  confidence: number
  processing_ms: number
  text_preview: string
  created_at: string
}

export interface IntentBucket {
  intent: string
  count: number
  pct: number
}

export interface DriftPoint {
  date: string
  [intent: string]: number | string
}

export interface MonitoringAlert {
  level: "warning" | "info" | "ok"
  message: string
  intent: string | null
}

export interface MLflowExperiment {
  experiment_id: string
  name: string
  lifecycle_stage: string
}

export interface MLflowRun {
  info: {
    run_id: string
    run_name: string
    status: string
    start_time: number
    end_time: number
  }
  data: {
    metrics: Record<string, number>
    params: Record<string, string>
  }
}

// ─── API client ───────────────────────────────────────────────────────────────

export const api = {
  assistant: {
    analyze: (text: string, conversationId?: string): Promise<AnalysisResult> =>
      request("/api/v1/assistant/analyze", {
        method: "POST",
        body: JSON.stringify({ text, conversation_id: conversationId }),
      }),
  },

  stats: {
    kpis: (): Promise<DashboardKPIs> =>
      request("/api/v1/stats/kpis"),
    recent: (limit = 10): Promise<RecentTicket[]> =>
      request(`/api/v1/stats/recent?limit=${limit}`),
    intentDistribution: (): Promise<IntentBucket[]> =>
      request("/api/v1/stats/intent-distribution"),
  },

  monitoring: {
    alerts: (): Promise<MonitoringAlert[]> =>
      request("/api/v1/monitoring/alerts"),
    drift: (topIntents = 3): Promise<DriftPoint[]> =>
      request(`/api/v1/monitoring/drift?top_intents=${topIntents}`),
  },

  experiments: {
    list: (): Promise<{ experiments: MLflowExperiment[] }> =>
      request("/api/v1/experiments"),
    runs: (experimentId: string): Promise<{ runs: MLflowRun[] }> =>
      request(`/api/v1/experiments/${experimentId}/runs`),
    metrics: (runId: string, metricKey: string): Promise<{ metrics: unknown[] }> =>
      request(`/api/v1/experiments/runs/${runId}/metrics?metric_key=${metricKey}`),
  },

  models: {
    list: (): Promise<ModelsResponse> => request("/api/v1/models"),
  },

  knowledgeBase: {
    list: (category?: string, q?: string): Promise<KBListResponse> => {
      const params = new URLSearchParams()
      if (category) params.set("category", category)
      if (q) params.set("q", q)
      const qs = params.toString()
      return request(`/api/v1/knowledge-base${qs ? `?${qs}` : ""}`)
    },
    get: (id: string): Promise<KBDocFull> => request(`/api/v1/knowledge-base/${id}`),
    upload: async (file: File, category: string): Promise<{ success: boolean; doc: KBDoc }> => {
      const form = new FormData()
      form.append("file", file)
      form.append("category", category)
      const res = await fetch(`${API_BASE}/api/v1/knowledge-base/upload`, {
        method: "POST",
        body: form,
        keepalive: true,
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail ?? "Upload error")
      }
      return res.json()
    },
    delete: (id: string): Promise<{ success: boolean }> =>
      request(`/api/v1/knowledge-base/${id}`, { method: "DELETE" }),
  },

  evaluation: {
    judge: (text: string, intent: string, response: string): Promise<EvalScores> =>
      request("/api/v1/evaluation/judge", {
        method: "POST",
        body: JSON.stringify({ text, intent, response }),
      }),
  },

  health: (): Promise<{ status: string; ml_mode: string; classifier_loaded: boolean; rag_loaded: boolean; openai_status: "ok" | "no_key" | "error"; openai_model: string | null }> =>
    request("/api/v1/health"),
}
