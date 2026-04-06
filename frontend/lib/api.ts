// lib/api.ts — typed REST client for the TikTok Live AI Bot backend

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const SELLER_ID = process.env.NEXT_PUBLIC_SELLER_ID ?? "";

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

// Analytics
export interface AnalyticsData {
  total_sessions: number;
  total_comments: number;
  total_replies: number;
  reply_rate: number;
  intent_breakdown: Record<string, number>;
  unanswered_count: number;
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

function qs(params: Record<string, string | number>): string {
  const p = new URLSearchParams(
    Object.entries(params).map(([k, v]) => [k, String(v)]),
  );
  return `?${p.toString()}`;
}

// ── API surface ──────────────────────────────────────────────────────────────

export const api = {
  knowledge: {
    list(params: { page?: number; limit?: number } = {}): Promise<KnowledgeList> {
      const { page = 1, limit = 20 } = params;
      return request(`/api/v1/knowledge/${qs({ seller_id: SELLER_ID, page, limit })}`, {
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
        body: JSON.stringify({ seller_id: SELLER_ID, ...body }),
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

    upload(file: File): Promise<UploadResult> {
      const form = new FormData();
      form.append("file", file);
      return request(
        `/api/v1/knowledge/upload${qs({ seller_id: SELLER_ID })}`,
        {
          method: "POST",
          body: form,
        },
      );
    },
  },

  sessions: {
    start(): Promise<SessionState> {
      return request("/api/v1/sessions/start", {
        method: "POST",
        body: JSON.stringify({ seller_id: SELLER_ID }),
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
  },

  settings: {
    get(): Promise<BotSettings> {
      return request(`/api/v1/settings/${qs({ seller_id: SELLER_ID })}`, {
        method: "GET",
      });
    },

    update(body: BotSettingsUpdate): Promise<BotSettings> {
      return request(`/api/v1/settings/${qs({ seller_id: SELLER_ID })}`, {
        method: "PUT",
        body: JSON.stringify(body),
      });
    },

    testReply(comment: string): Promise<TestReplyResult> {
      return request("/api/v1/settings/test-reply", {
        method: "POST",
        body: JSON.stringify({ seller_id: SELLER_ID, comment }),
      });
    },
  },

  analytics: {
    get(): Promise<AnalyticsData> {
      return request(`/api/v1/analytics/${qs({ seller_id: SELLER_ID })}`, {
        method: "GET",
      });
    },
  },
};
