// lib/api.ts — typed REST client for the TikTok Live AI Bot backend

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Types (mirror backend Pydantic schemas) ──────────────────────────────────

export type KnowledgeCategory = "product" | "policy" | "faq";

export interface KnowledgeChunk {
  id: string;
  seller_id: string;
  content: string;
  category: KnowledgeCategory;
  metadata: Record<string, unknown>;
  needs_reembed: boolean;
}

export interface KnowledgeList {
  items: KnowledgeChunk[];
  total: number;
  page: number;
  limit: number;
}

export interface UploadResult {
  created: number;
  skipped: number;
  errors: string[];
}

export interface PreviewRow {
  row: number;
  content: string;
  category: string;
  is_valid: boolean;
  warning: string | null;
}

export interface CsvPreview {
  total_rows: number;
  valid_rows: number;
  preview: PreviewRow[];
  warnings: string[];
}

export type SessionStatus = "active" | "ended" | "paused";

export interface Session {
  id: string;
  seller_id: string;
  tiktok_room_id?: number;
  status: SessionStatus;
  started_at: string;
  ended_at?: string;
}

export interface SessionState {
  connected: boolean;
  session: Session | null;
}

export interface BotSettings {
  tone: string;
  blacklist_keywords: string[];
  reply_delay_min: number;
  reply_delay_max: number;
  user_cooldown_seconds: number;
  max_replies_per_session: number;
  auto_reply_enabled: boolean;
}

export interface BotSettingsUpdate {
  tone?: string;
  blacklist_keywords?: string[];
  reply_delay_min?: number;
  reply_delay_max?: number;
  user_cooldown_seconds?: number;
  max_replies_per_session?: number;
  auto_reply_enabled?: boolean;
}

export interface TestReplyResult {
  reply: string;
  intent: string;
  chunks_used: string[];
}

// Gift tracking
export interface GiftLogEntry {
  id: string;
  session_id: string;
  user_unique_id: string;
  gift_name: string;
  diamond_count: number;
  repeat_count: number;
  total_diamonds: number;
  estimated_usd: number;
  thank_reply: string | null;
  created_at: string;
}

export interface TopGifter {
  user: string;
  total_diamonds: number;
  gift_count: number;
}

export interface GiftBreakdown {
  gift_name: string;
  count: number;
  total_diamonds: number;
}

export interface GiftStats {
  total_gifts: number;
  total_diamonds: number;
  estimated_usd: number;
  top_gifters: TopGifter[];
  gift_breakdown: GiftBreakdown[];
}

// Analytics
export interface AnalyticsData {
  total_sessions: number;
  total_comments: number;
  total_replies: number;
  reply_rate: number;
  intent_breakdown: Record<string, number>;
  sentiment_breakdown: Record<string, number>;
  unanswered_count: number;
  gift_stats: GiftStats | null;
}

// Message log
export interface MessageLog {
  id: string;
  session_id: string;
  user_unique_id: string;
  comment: string;
  reply: string | null;
  intent: string;
  chunks_used: string[];
  created_at: string;
}

// Auth - updated for multi-tenant
export interface AuthSeller {
  id: string;
  username: string;
  name: string;
  tiktok_unique_id: string;
}

// ── Error type ───────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Core fetch wrapper ───────────────────────────────────────────────────────

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_URL}${path}`;
  // Don't set Content-Type for FormData — browser sets it with boundary automatically
  const isFormData = options.body instanceof FormData;
  const res = await fetch(url, {
    credentials: "include",
    headers: isFormData
      ? (options.headers ?? {})
      : { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body.detail ?? body.message ?? message;
    } catch {
      // ignore parse error
    }
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

function qs(params: Record<string, string | number | undefined>): string {
  const filtered = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== "",
  );
  if (filtered.length === 0) return "";
  const p = new URLSearchParams(filtered.map(([k, v]) => [k, String(v)]));
  return `?${p.toString()}`;
}

// ── API surface ──────────────────────────────────────────────────────────────

export const api = {
  knowledge: {
    list(params: { page?: number; limit?: number } = {}): Promise<KnowledgeList> {
      const { page = 1, limit = 20 } = params;
      return request(`/api/v1/knowledge/${qs({ page, limit })}`, {
        method: "GET",
      });
    },

    create(body: {
      content: string;
      category: KnowledgeCategory;
      metadata: Record<string, unknown>;
    }): Promise<KnowledgeChunk> {
      return request("/api/v1/knowledge/", {
        method: "POST",
        body: JSON.stringify(body),
      });
    },

    update(
      id: string,
      body: {
        content?: string;
        category?: KnowledgeCategory;
        metadata?: Record<string, unknown>;
      },
    ): Promise<KnowledgeChunk> {
      return request(`/api/v1/knowledge/${id}`, {
        method: "PUT",
        body: JSON.stringify(body),
      });
    },

    delete(id: string): Promise<void> {
      return request(`/api/v1/knowledge/${id}`, { method: "DELETE" });
    },

    preview(file: File): Promise<CsvPreview> {
      const form = new FormData();
      form.append("file", file);
      return request("/api/v1/knowledge/preview", { method: "POST", body: form });
    },

    upload(file: File): Promise<UploadResult> {
      const form = new FormData();
      form.append("file", file);
      return request("/api/v1/knowledge/upload", {
        method: "POST",
        body: form,
      });
    },
  },

  sessions: {
    start(): Promise<SessionState> {
      return request("/api/v1/sessions/start", {
        method: "POST",
      });
    },

    stop(): Promise<{ message: string }> {
      return request("/api/v1/sessions/stop", { method: "POST" });
    },

    status(): Promise<SessionState> {
      return request("/api/v1/sessions/status", { method: "GET" });
    },

    history(params: { page?: number; limit?: number } = {}): Promise<Session[]> {
      const { page = 1, limit = 20 } = params;
      return request(
        `/api/v1/sessions/history${qs({ page, limit })}`,
        { method: "GET" },
      );
    },

    messages(sessionId: string, params: { page?: number; limit?: number } = {}): Promise<MessageLog[]> {
      const { page = 1, limit = 50 } = params;
      return request(
        `/api/v1/sessions/${sessionId}/messages${qs({ page, limit })}`,
        { method: "GET" },
      );
    },

    gifts(sessionId: string, params: { page?: number; limit?: number } = {}): Promise<GiftLogEntry[]> {
      const { page = 1, limit = 50 } = params;
      return request(
        `/api/v1/sessions/${sessionId}/gifts${qs({ page, limit })}`,
        { method: "GET" },
      );
    },
  },

  settings: {
    get(): Promise<BotSettings> {
      return request("/api/v1/settings/", { method: "GET" });
    },

    update(body: BotSettingsUpdate): Promise<BotSettings> {
      return request("/api/v1/settings/", {
        method: "PUT",
        body: JSON.stringify(body),
      });
    },

    testReply(comment: string): Promise<TestReplyResult> {
      return request("/api/v1/settings/test-reply", {
        method: "POST",
        body: JSON.stringify({ comment }),
      });
    },
  },

  analytics: {
    get(params: { start_date?: string; end_date?: string } = {}): Promise<AnalyticsData> {
      return request(`/api/v1/analytics/${qs(params)}`, {
        method: "GET",
      });
    },
  },

  auth: {
    login(username: string, password: string): Promise<AuthSeller> {
      return request("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
    },

    logout(): Promise<{ message: string }> {
      return request("/api/v1/auth/logout", { method: "POST" });
    },

    me(): Promise<AuthSeller> {
      return request("/api/v1/auth/me", { method: "GET" });
    },
  },
};
