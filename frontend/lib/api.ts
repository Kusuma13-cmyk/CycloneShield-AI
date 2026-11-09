/**
 * CycloneShield AI — API client
 * All frontend–backend communication goes through this module.
 * API_BASE is empty string in production (same origin), or set via env var in dev.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export interface WeatherReading {
  timestamp: string;
  station_id: string;
  station_name: string;
  latitude: number;
  longitude: number;
  pressure_hpa: number;
  wind_speed_kmh: number;
  wind_direction_deg: number;
  humidity_pct: number;
  rainfall_mm: number;
  sea_surface_temp_c: number | null;
  visibility_km: number | null;
  wave_height_m: number | null;
  data_source: string;
}

export interface TrackPoint {
  storm_id: string;
  storm_name: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  intensity_category: string;
  wind_speed_kmh: number;
  pressure_hpa: number;
  status: string;
  source: string;
}

export interface AgentResult {
  agent_name: string;
  status: "ok" | "error";
  output: Record<string, unknown>;
  llm_response_meta: Record<string, unknown>;
  duration_ms: number;
  validation_issues?: string[];
}

export interface LLMEval {
  total_latency_ms: number;
  total_tokens: number;
  total_cost_usd: number;
  providers_used: string[];
  models_used: string[];
  json_validity_score: number;
  output_completeness_score: number;
  per_agent: Record<string, { latency_ms: number; tokens: number; provider: string }>;
  note: string;
}

export interface LogEntry {
  id: number;
  timestamp: string;
  agent: string;
  event: string;
  input_summary: string;
  output_summary: string;
  status: "ok" | "error" | "skipped";
  duration_ms: number;
  error: string;
  metadata: Record<string, unknown>;
}

export interface AnalysisSession {
  session_id: string;
  start_time: string;
  end_time: string;
  status: "idle" | "running" | "awaiting_review" | "complete" | "error" | "rejected";
  provider_name: string;
  data_mode: string;
  location: string;
  total_duration_ms: number;
  weather_result: AgentResult;
  cyclone_result: AgentResult;
  impact_result: AgentResult;
  llm_eval: LLMEval;
  errors: string[];
  execution_log: LogEntry[];
  human_review_status: "pending" | "approved" | "rejected";
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
  mode: string;
  providers: { ibm_granite: boolean; openweather: boolean };
}

// ── Request helpers ───────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs = 60_000
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
    });
    clearTimeout(timer);
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error((errBody as { error?: string }).error ?? `HTTP ${res.status}`);
    }
    return res.json() as Promise<T>;
  } finally {
    clearTimeout(timer);
  }
}

// ── Public API functions ──────────────────────────────────────────────────────

export async function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/api/health");
}

export async function fetchWeather(live = false): Promise<{ readings: WeatherReading[]; count: number; source: string }> {
  return apiFetch(`/api/weather?live=${live}`);
}

export async function fetchTrack(stormId?: string): Promise<{ track: TrackPoint[]; count: number; source: string }> {
  const q = stormId ? `?storm_id=${encodeURIComponent(stormId)}` : "";
  return apiFetch(`/api/track${q}`);
}

export async function runAnalysis(opts?: {
  location?: string;
  provider_override?: string;
  use_live_weather?: boolean;
}): Promise<AnalysisSession> {
  return apiFetch<AnalysisSession>("/api/analyze", {
    method: "POST",
    body: JSON.stringify(opts ?? {}),
  }, 120_000); // 2-min timeout for full pipeline
}

export async function submitReview(params: {
  session_data: Partial<AnalysisSession>;
  decision: "approved" | "rejected";
  reviewer: string;
  notes?: string;
}): Promise<{
  human_review_status: string;
  human_reviewer: string;
  review_timestamp: string;
  status: string;
}> {
  return apiFetch("/api/review", {
    method: "POST",
    body: JSON.stringify(params),
  });
}
