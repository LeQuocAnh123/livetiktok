# Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Next.js 14 dashboard with three pages — Knowledge Base management, Live Monitor (realtime WebSocket), and Bot Settings — backed by the REST + WebSocket API from Plans 1 & 2.

**Architecture:** Next.js 14 App Router with TypeScript and Tailwind CSS. A typed REST client (`lib/api.ts`) wraps all backend endpoints; a singleton WebSocket client (`lib/ws.ts`) handles the realtime channel. Each page is a thin Server/Client component shell over focused `components/` sub-trees. Single-seller v1: seller ID read from `NEXT_PUBLIC_SELLER_ID` env var.

**Tech Stack:** Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, Vitest (unit tests for lib/), Playwright (E2E for the 3 pages)

**Spec:** `docs/superpowers/specs/2026-04-06-tiktok-live-ai-bot-design.md` sections 3, 6, 7, 8

**Depends on:** Plan 1 + Plan 2 backend (all routes live at `http://localhost:8000`)

---

## File Map

```
frontend/
├── app/
│   ├── layout.tsx                    # CREATE — Root layout: sidebar nav + font
│   ├── page.tsx                      # CREATE — Redirect to /monitor
│   ├── knowledge/
│   │   └── page.tsx                  # CREATE — Knowledge Base page
│   ├── monitor/
│   │   └── page.tsx                  # CREATE — Live Monitor page
│   └── settings/
│       └── page.tsx                  # CREATE — Settings page
├── components/
│   ├── nav/
│   │   └── Sidebar.tsx               # CREATE — Left nav: Knowledge / Monitor / Settings links
│   ├── knowledge/
│   │   ├── ChunkTable.tsx            # CREATE — Paginated table of knowledge chunks
│   │   ├── ChunkDialog.tsx           # CREATE — Create/edit chunk form dialog
│   │   └── CsvUpload.tsx             # CREATE — File upload button + result toast
│   ├── monitor/
│   │   ├── SessionControl.tsx        # CREATE — Start/Stop button + session status badge
│   │   ├── CommentFeed.tsx           # CREATE — Scrolling realtime comment list
│   │   └── BotControls.tsx           # CREATE — Pause/Resume toggle + manual reply form
│   └── settings/
│       ├── SettingsForm.tsx          # CREATE — Bot settings form (all fields)
│       └── TestReply.tsx             # CREATE — Test-reply input + preview panel
├── lib/
│   ├── api.ts                        # CREATE — Typed REST client for all backend endpoints
│   └── ws.ts                         # CREATE — WebSocket singleton + typed message union
├── hooks/
│   ├── useWebSocket.ts               # CREATE — React hook: connect/disconnect + event dispatch
│   └── useSession.ts                 # CREATE — Session status state derived from WS + REST
├── tests/
│   ├── unit/
│   │   ├── api.test.ts               # CREATE — Vitest unit tests for lib/api.ts
│   │   └── ws.test.ts                # CREATE — Vitest unit tests for lib/ws.ts
│   └── e2e/
│       ├── knowledge.spec.ts         # CREATE — Playwright: CRUD flow
│       ├── monitor.spec.ts           # CREATE — Playwright: start/stop session flow
│       └── settings.spec.ts          # CREATE — Playwright: update settings + test-reply
├── package.json                      # CREATE (from scaffold)
├── next.config.ts                    # CREATE — API proxy rewrite
├── tailwind.config.ts                # CREATE (from scaffold)
├── tsconfig.json                     # CREATE (from scaffold)
├── vitest.config.ts                  # CREATE — Vitest config pointing at tests/unit/
├── playwright.config.ts              # CREATE — Playwright targeting http://localhost:3000
├── .env.example                      # CREATE — NEXT_PUBLIC_API_URL, NEXT_PUBLIC_WS_URL, NEXT_PUBLIC_SELLER_ID
└── Dockerfile                        # CREATE — Multi-stage production build
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `frontend/` directory tree (Next.js 14 with TypeScript + Tailwind)
- Create: `frontend/.env.example`
- Create: `frontend/next.config.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/playwright.config.ts`

- [ ] **Step 1: Scaffold Next.js 14 project**

Run from the repo root:

```bash
cd /home/quocanh/live-tiktok/livetiktok
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir=no \
  --import-alias="@/*" \
  --no-git
```

When prompted: accept all defaults. This creates `frontend/` with App Router, TypeScript, Tailwind, ESLint.

- [ ] **Step 2: Install shadcn/ui**

```bash
cd frontend
npx shadcn@latest init
```

When prompted:
- Style: **Default**
- Base color: **Slate**
- CSS variables: **yes**

Then add the components needed across all pages in one command:

```bash
npx shadcn@latest add button input textarea select badge dialog table card tabs toast label separator
```

- [ ] **Step 3: Install test and utility dependencies**

```bash
npm install --save-dev vitest @vitejs/plugin-react @testing-library/react @testing-library/jest-dom jsdom
npm install --save-dev @playwright/test
npm install sonner  # toast notifications (Sonner — integrates with shadcn)
npm install lucide-react  # icons (already included by shadcn but make explicit)
```

- [ ] **Step 4: Create `frontend/vitest.config.ts`**

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/unit/setup.ts"],
    include: ["tests/unit/**/*.test.ts"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
```

- [ ] **Step 5: Create `frontend/tests/unit/setup.ts`**

```typescript
import "@testing-library/jest-dom";
```

- [ ] **Step 6: Create `frontend/playwright.config.ts`**

```typescript
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  retries: 0,
  reporter: "html",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: true,
  },
});
```

- [ ] **Step 7: Create `frontend/.env.example`**

```bash
# Backend REST API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Backend WebSocket
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Single-seller v1: ID of the Seller record in the backend DB
NEXT_PUBLIC_SELLER_ID=your-seller-id-here

# WebSocket authentication token (must match WS_MONITOR_TOKEN in backend .env)
# Leave empty in development if WS_MONITOR_TOKEN is not set in backend
NEXT_PUBLIC_WS_TOKEN=
```

Copy to `.env.local`:
```bash
cp .env.example .env.local
```

- [ ] **Step 8: Create `frontend/next.config.ts`**

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Proxy /api/* to backend in dev — avoids CORS issues
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
```

- [ ] **Step 9: Verify scaffold runs**

```bash
npm run dev
```

Expected: Next.js dev server starts on http://localhost:3000 with no errors.

- [ ] **Step 10: Commit**

```bash
cd /home/quocanh/live-tiktok/livetiktok
git add frontend/
git commit -m "feat: scaffold Next.js 14 + shadcn/ui + vitest + playwright"
```

---

## Task 2: REST API Client (`lib/api.ts`)

**Files:**
- Create: `frontend/lib/api.ts`
- Create: `frontend/tests/unit/api.test.ts`

These types mirror the backend Pydantic schemas exactly.

- [ ] **Step 1: Write failing tests first**

Create `frontend/tests/unit/api.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock global fetch
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// api.ts reads env vars at call time — stub them
vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
vi.stubEnv("NEXT_PUBLIC_SELLER_ID", "seller-001");

// Re-import after stubbing
const { api } = await import("@/lib/api");

function mockResponse(body: unknown, status = 200) {
  mockFetch.mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe("api.knowledge.list", () => {
  it("calls GET /api/v1/knowledge/ with seller_id", async () => {
    mockResponse({ items: [], total: 0, page: 1, limit: 20 });
    const result = await api.knowledge.list({ page: 1, limit: 20 });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/knowledge/"),
      expect.objectContaining({ method: "GET" })
    );
    expect(result.total).toBe(0);
  });
});

describe("api.knowledge.create", () => {
  it("calls POST /api/v1/knowledge/ with body", async () => {
    mockResponse({ id: "chunk-1", seller_id: "seller-001", content: "test", category: "faq", metadata: {}, needs_reembed: true });
    const result = await api.knowledge.create({ content: "test", category: "faq", metadata: {} });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/knowledge/"),
      expect.objectContaining({ method: "POST" })
    );
    expect(result.id).toBe("chunk-1");
  });
});

describe("api.knowledge.update", () => {
  it("calls PUT /api/v1/knowledge/{id}", async () => {
    mockResponse({ id: "chunk-1", seller_id: "seller-001", content: "updated", category: "faq", metadata: {}, needs_reembed: true });
    const result = await api.knowledge.update("chunk-1", { content: "updated" });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/knowledge/chunk-1"),
      expect.objectContaining({ method: "PUT" })
    );
    expect(result.content).toBe("updated");
  });
});

describe("api.knowledge.delete", () => {
  it("calls DELETE /api/v1/knowledge/{id}", async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, status: 204, json: async () => null });
    await api.knowledge.delete("chunk-1");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/knowledge/chunk-1"),
      expect.objectContaining({ method: "DELETE" })
    );
  });
});

describe("api.sessions.start", () => {
  it("calls POST /api/v1/sessions/start with seller_id", async () => {
    mockResponse({ connected: true, session: { id: "s1", seller_id: "seller-001", status: "active", started_at: new Date().toISOString() } });
    const result = await api.sessions.start();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/sessions/start"),
      expect.objectContaining({ method: "POST" })
    );
    expect(result.connected).toBe(true);
  });
});

describe("api.sessions.status", () => {
  it("calls GET /api/v1/sessions/status", async () => {
    mockResponse({ connected: false, session: null });
    const result = await api.sessions.status();
    expect(result.connected).toBe(false);
  });
});

describe("api.settings.get", () => {
  it("calls GET /api/v1/settings/ with seller_id", async () => {
    mockResponse({
      tone: "friendly",
      blacklist_keywords: [],
      reply_delay_min: 5,
      reply_delay_max: 15,
      user_cooldown_seconds: 60,
      max_replies_per_session: 500,
      auto_reply_enabled: true,
    });
    const result = await api.settings.get();
    expect(result.tone).toBe("friendly");
  });
});

describe("api.settings.testReply", () => {
  it("calls POST /api/v1/settings/test-reply", async () => {
    mockResponse({ reply: "Dạ còn ạ!", intent: "product_inquiry", chunks_used: ["c1"] });
    const result = await api.settings.testReply("Còn hàng không?");
    expect(result.reply).toBe("Dạ còn ạ!");
  });
});

describe("api error handling", () => {
  it("throws ApiError with status and message on 4xx", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Not found" }),
    });
    await expect(api.settings.get()).rejects.toMatchObject({ status: 404, message: "Not found" });
  });
});
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd frontend && npx vitest run tests/unit/api.test.ts 2>&1 | head -20
```

Expected: `Error: Cannot find module '@/lib/api'`

- [ ] **Step 3: Create `frontend/lib/api.ts`**

```typescript
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
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
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

    create(body: { content: string; category: KnowledgeCategory; metadata: Record<string, unknown> }): Promise<KnowledgeChunk> {
      return request("/api/v1/knowledge/", {
        method: "POST",
        body: JSON.stringify({ seller_id: SELLER_ID, ...body }),
      });
    },

    update(id: string, body: { content?: string; category?: KnowledgeCategory; metadata?: Record<string, unknown> }): Promise<KnowledgeChunk> {
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
      // Don't set Content-Type — browser sets it with boundary for multipart
      return request(`/api/v1/knowledge/upload${qs({ seller_id: SELLER_ID })}`, {
        method: "POST",
        headers: {},
        body: form,
      });
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
      return request(`/api/v1/sessions/history${qs({ page, limit })}`, { method: "GET" });
    },
  },

  settings: {
    get(): Promise<BotSettings> {
      return request(`/api/v1/settings/${qs({ seller_id: SELLER_ID })}`, { method: "GET" });
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
};
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run tests/unit/api.test.ts
```

Expected: 9 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /home/quocanh/live-tiktok/livetiktok
git add frontend/lib/api.ts frontend/tests/unit/ frontend/vitest.config.ts
git commit -m "feat: typed REST API client with unit tests"
```

---

## Task 3: WebSocket Client + Hook (`lib/ws.ts`)

**Files:**
- Create: `frontend/lib/ws.ts`
- Create: `frontend/hooks/useWebSocket.ts`
- Create: `frontend/tests/unit/ws.test.ts`

- [ ] **Step 1: Write failing tests**

Create `frontend/tests/unit/ws.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// ── Mock WebSocket ───────────────────────────────────────────────────────────
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onclose: ((e: { code: number }) => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;

  sentMessages: string[] = [];

  constructor(public url: string) {
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.onopen?.();
    }, 0);
  }

  send(data: string) {
    this.sentMessages.push(data);
  }

  close(code = 1000) {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ code });
  }

  // Test helper: simulate receiving a server message
  receive(msg: object) {
    this.onmessage?.({ data: JSON.stringify(msg) });
  }
}

vi.stubGlobal("WebSocket", MockWebSocket);

// Re-import after stubbing
const { wsClient } = await import("@/lib/ws");

let mockWS: MockWebSocket;

beforeEach(async () => {
  wsClient.disconnect();
  wsClient.connect("ws://localhost:8000/ws/monitor");
  // Wait for async open
  await new Promise((r) => setTimeout(r, 10));
  // Grab the internal WS instance for test helpers
  mockWS = (wsClient as any)._ws;
});

afterEach(() => {
  wsClient.disconnect();
});

describe("wsClient.connect", () => {
  it("opens connection to the given URL", () => {
    expect(mockWS.url).toContain("ws://localhost:8000/ws/monitor");
  });
});

describe("wsClient.on / event dispatch", () => {
  it("calls registered listener when message of matching type arrives", async () => {
    const handler = vi.fn();
    wsClient.on("comment", handler);
    mockWS.receive({ type: "comment", message_id: "m1", user: "alice", content: "hello", timestamp: "2026-01-01T00:00:00Z" });
    expect(handler).toHaveBeenCalledWith(
      expect.objectContaining({ type: "comment", user: "alice" })
    );
    wsClient.off("comment", handler);
  });

  it("does not call listener after off()", () => {
    const handler = vi.fn();
    wsClient.on("comment", handler);
    wsClient.off("comment", handler);
    mockWS.receive({ type: "comment", message_id: "m2", user: "bob", content: "hi", timestamp: "" });
    expect(handler).not.toHaveBeenCalled();
  });

  it("on() returns an unsubscribe function", () => {
    const handler = vi.fn();
    const unsub = wsClient.on("status", handler);
    unsub();
    mockWS.receive({ type: "status", connected: true });
    expect(handler).not.toHaveBeenCalled();
  });
});

describe("wsClient.send", () => {
  it("serializes and sends a command message", () => {
    wsClient.send({ type: "pause_bot" });
    expect(mockWS.sentMessages).toContain(JSON.stringify({ type: "pause_bot" }));
  });
});

describe("wsClient.disconnect", () => {
  it("closes the WebSocket connection", () => {
    wsClient.disconnect();
    expect(mockWS.readyState).toBe(MockWebSocket.CLOSED);
  });
});
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd frontend && npx vitest run tests/unit/ws.test.ts 2>&1 | head -15
```

Expected: `Error: Cannot find module '@/lib/ws'`

- [ ] **Step 3: Create `frontend/lib/ws.ts`**

```typescript
// lib/ws.ts — WebSocket singleton client

export type WSMessage =
  | { type: "comment"; message_id: string; user: string; content: string; timestamp: string }
  | { type: "reply"; message_id: string; content: string; intent: string; chunks_used: string[] }
  | { type: "status"; connected?: boolean; paused?: boolean; room_id?: number }
  | { type: "error"; message: string };

type Handler<T extends WSMessage = WSMessage> = (msg: T) => void;

class WSClient {
  _ws: WebSocket | null = null;
  private _listeners: Map<string, Set<Handler>> = new Map();

  connect(url: string): void {
    if (this._ws && this._ws.readyState <= WebSocket.OPEN) return;

    this._ws = new WebSocket(url);

    this._ws.onmessage = (event: MessageEvent) => {
      let msg: WSMessage;
      try {
        msg = JSON.parse(event.data as string) as WSMessage;
      } catch {
        return;
      }
      const handlers = this._listeners.get(msg.type);
      if (handlers) {
        handlers.forEach((h) => h(msg));
      }
    };

    this._ws.onerror = () => {
      // Suppress — onclose will follow
    };
  }

  disconnect(): void {
    if (this._ws) {
      this._ws.close(1000);
      this._ws = null;
    }
  }

  send(msg: object): void {
    if (this._ws?.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify(msg));
    }
  }

  on<T extends WSMessage>(type: T["type"], handler: Handler<T>): () => void {
    if (!this._listeners.has(type)) {
      this._listeners.set(type, new Set());
    }
    this._listeners.get(type)!.add(handler as Handler);
    return () => this.off(type, handler);
  }

  off<T extends WSMessage>(type: T["type"], handler: Handler<T>): void {
    this._listeners.get(type)?.delete(handler as Handler);
  }
}

export const wsClient = new WSClient();
```

- [ ] **Step 4: Create `frontend/hooks/useWebSocket.ts`**

```typescript
"use client";
// hooks/useWebSocket.ts — React hook for the WS singleton

import { useEffect, useRef } from "react";
import { wsClient, type WSMessage } from "@/lib/ws";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
const WS_TOKEN = process.env.NEXT_PUBLIC_WS_TOKEN ?? "";

export function useWebSocket(
  handlers: Partial<{ [T in WSMessage as T["type"]]: (msg: Extract<WSMessage, { type: T["type"] }>) => void }>,
) {
  // Stable ref — won't cause re-renders when handlers change identity
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    const url = WS_TOKEN
      ? `${WS_URL}/ws/monitor?token=${WS_TOKEN}`
      : `${WS_URL}/ws/monitor`;

    wsClient.connect(url);

    const unsubs = (Object.keys(handlers) as WSMessage["type"][]).map((type) => {
      return wsClient.on(type, (msg) => {
        // Always call the latest version of the handler via ref
        const h = handlersRef.current[type as keyof typeof handlersRef.current];
        if (h) (h as (m: WSMessage) => void)(msg);
      });
    });

    return () => {
      unsubs.forEach((u) => u());
    };
    // Only run once — handlers are accessed via ref
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
```

- [ ] **Step 5: Run tests**

```bash
cd frontend && npx vitest run tests/unit/ws.test.ts
```

Expected: 6 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /home/quocanh/live-tiktok/livetiktok
git add frontend/lib/ws.ts frontend/hooks/ frontend/tests/unit/ws.test.ts
git commit -m "feat: WebSocket singleton client + useWebSocket hook with unit tests"
```

---

## Task 4: Root Layout + Navigation

**Files:**
- Modify: `frontend/app/layout.tsx`
- Create: `frontend/app/page.tsx`
- Create: `frontend/components/nav/Sidebar.tsx`

No separate test file — layout is covered by E2E tests in Tasks 5-7.

- [ ] **Step 1: Create `frontend/components/nav/Sidebar.tsx`**

```tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, Radio, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const links = [
  { href: "/knowledge", label: "Knowledge Base", icon: BookOpen },
  { href: "/monitor", label: "Live Monitor", icon: Radio },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex h-screen w-56 flex-col border-r bg-slate-50 px-3 py-6 shrink-0">
      <div className="mb-8 px-2">
        <h1 className="text-lg font-bold tracking-tight">TikTok Live Bot</h1>
      </div>
      <nav className="flex flex-col gap-1">
        {links.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              pathname.startsWith(href)
                ? "bg-slate-200 text-slate-900"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
```

- [ ] **Step 2: Update `frontend/app/layout.tsx`**

Replace the scaffolded content:

```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/nav/Sidebar";
import { Toaster } from "sonner";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "TikTok Live AI Bot",
  description: "Dashboard for TikTok Live AI Bot",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 overflow-auto p-6">{children}</main>
        </div>
        <Toaster richColors position="top-right" />
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Create `frontend/app/page.tsx`**

```tsx
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/monitor");
}
```

- [ ] **Step 4: Verify layout renders**

```bash
cd frontend && npm run dev
```

Visit http://localhost:3000 — should redirect to /monitor, sidebar visible with 3 links.

- [ ] **Step 5: Commit**

```bash
cd /home/quocanh/live-tiktok/livetiktok
git add frontend/app/ frontend/components/nav/
git commit -m "feat: root layout with sidebar navigation"
```

---

## Task 5: Knowledge Base Page

**Files:**
- Create: `frontend/app/knowledge/page.tsx`
- Create: `frontend/components/knowledge/ChunkTable.tsx`
- Create: `frontend/components/knowledge/ChunkDialog.tsx`
- Create: `frontend/components/knowledge/CsvUpload.tsx`
- Create: `frontend/tests/e2e/knowledge.spec.ts`

- [ ] **Step 1: Write E2E test first**

Create `frontend/tests/e2e/knowledge.spec.ts`:

```typescript
import { test, expect } from "@playwright/test";

// All tests mock the backend API via page.route()
// so they run without a real backend.

const MOCK_LIST = {
  items: [
    { id: "c1", seller_id: "s1", content: "Áo cotton giá 150k", category: "product", metadata: {}, needs_reembed: false },
  ],
  total: 1,
  page: 1,
  limit: 20,
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/knowledge/**", (route) => {
    const method = route.request().method();
    const url = route.request().url();
    if (method === "GET") {
      route.fulfill({ json: MOCK_LIST });
    } else if (method === "POST" && url.includes("/api/v1/knowledge/") && !url.includes("upload")) {
      route.fulfill({
        status: 201,
        json: { id: "c-new", seller_id: "s1", content: "New chunk", category: "faq", metadata: {}, needs_reembed: true },
      });
    } else if (method === "PUT") {
      route.fulfill({ json: { id: "c1", seller_id: "s1", content: "Updated", category: "product", metadata: {}, needs_reembed: true } });
    } else if (method === "DELETE") {
      route.fulfill({ status: 204, body: "" });
    } else {
      route.continue();
    }
  });
});

test("knowledge page loads and shows chunks", async ({ page }) => {
  await page.goto("/knowledge");
  await expect(page.getByText("Áo cotton giá 150k")).toBeVisible();
  await expect(page.getByText("product")).toBeVisible();
});

test("can open create chunk dialog", async ({ page }) => {
  await page.goto("/knowledge");
  await page.getByRole("button", { name: /add chunk/i }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByLabel(/content/i)).toBeVisible();
});

test("can create a new chunk", async ({ page }) => {
  await page.goto("/knowledge");
  await page.getByRole("button", { name: /add chunk/i }).click();
  await page.getByLabel(/content/i).fill("New chunk content");
  await page.getByRole("button", { name: /save/i }).click();
  // Dialog should close (success)
  await expect(page.getByRole("dialog")).not.toBeVisible();
});

test("can delete a chunk", async ({ page }) => {
  await page.goto("/knowledge");
  await page.getByRole("button", { name: /delete/i }).first().click();
  // Confirm deletion
  await page.getByRole("button", { name: /confirm/i }).click();
  // Toast or row removed — just verify no error
  await expect(page.getByText(/error/i)).not.toBeVisible();
});
```

- [ ] **Step 2: Run to verify tests fail (no page yet)**

```bash
cd frontend && npx playwright test tests/e2e/knowledge.spec.ts 2>&1 | head -15
```

Expected: tests fail (page returns 404 or empty).

- [ ] **Step 3: Create `frontend/components/knowledge/ChunkTable.tsx`**

```tsx
"use client";
import { useState } from "react";
import { Trash2, Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import type { KnowledgeChunk } from "@/lib/api";

interface Props {
  chunks: KnowledgeChunk[];
  onEdit: (chunk: KnowledgeChunk) => void;
  onDelete: (id: string) => Promise<void>;
}

export function ChunkTable({ chunks, onEdit, onDelete }: Props) {
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function handleConfirmDelete() {
    if (!confirmId) return;
    setDeleting(true);
    await onDelete(confirmId);
    setDeleting(false);
    setConfirmId(null);
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[60%]">Content</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {chunks.map((chunk) => (
            <TableRow key={chunk.id}>
              <TableCell className="max-w-xs truncate">{chunk.content}</TableCell>
              <TableCell>
                <Badge variant="outline">{chunk.category}</Badge>
              </TableCell>
              <TableCell>
                {chunk.needs_reembed && (
                  <Badge variant="secondary" className="text-xs">pending embed</Badge>
                )}
              </TableCell>
              <TableCell className="text-right">
                <Button variant="ghost" size="icon" onClick={() => onEdit(chunk)} aria-label="edit">
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" onClick={() => setConfirmId(chunk.id)} aria-label="delete">
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
          {chunks.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                No knowledge chunks yet. Add your first one.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {/* Delete confirmation dialog */}
      <Dialog open={!!confirmId} onOpenChange={() => setConfirmId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete chunk?</DialogTitle>
            <DialogDescription>
              This removes the chunk from the database and ChromaDB. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmId(null)}>Cancel</Button>
            <Button variant="destructive" disabled={deleting} onClick={handleConfirmDelete}>
              {deleting ? "Deleting…" : "Confirm"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
```

- [ ] **Step 4: Create `frontend/components/knowledge/ChunkDialog.tsx`**

```tsx
"use client";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import type { KnowledgeChunk, KnowledgeCategory } from "@/lib/api";

interface Props {
  open: boolean;
  chunk?: KnowledgeChunk | null;
  onClose: () => void;
  onSave: (data: { content: string; category: KnowledgeCategory; metadata: Record<string, unknown> }) => Promise<void>;
}

export function ChunkDialog({ open, chunk, onClose, onSave }: Props) {
  const [content, setContent] = useState("");
  const [category, setCategory] = useState<KnowledgeCategory>("faq");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (chunk) {
      setContent(chunk.content);
      setCategory(chunk.category);
    } else {
      setContent("");
      setCategory("faq");
    }
  }, [chunk, open]);

  async function handleSave() {
    if (!content.trim()) return;
    setSaving(true);
    await onSave({ content: content.trim(), category, metadata: chunk?.metadata ?? {} });
    setSaving(false);
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{chunk ? "Edit Chunk" : "Add Chunk"}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <div className="grid gap-2">
            <Label htmlFor="content">Content</Label>
            <Textarea
              id="content"
              rows={4}
              placeholder="Describe a product, policy, or FAQ answer…"
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="category">Category</Label>
            <Select value={category} onValueChange={(v) => setCategory(v as KnowledgeCategory)}>
              <SelectTrigger id="category">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="product">Product</SelectItem>
                <SelectItem value="policy">Policy</SelectItem>
                <SelectItem value="faq">FAQ</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button disabled={saving || !content.trim()} onClick={handleSave}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 5: Create `frontend/components/knowledge/CsvUpload.tsx`**

```tsx
"use client";
import { useRef, useState } from "react";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { api } from "@/lib/api";

interface Props {
  onDone: () => void;  // refresh list after upload
}

export function CsvUpload({ onDone }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith(".csv")) {
      toast.error("Only CSV files are supported");
      return;
    }

    setUploading(true);
    try {
      const result = await api.knowledge.upload(file);
      toast.success(`Imported ${result.created} chunks (${result.skipped} skipped)`);
      onDone();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      // Reset so the same file can be re-uploaded
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={handleFile}
      />
      <Button
        variant="outline"
        disabled={uploading}
        onClick={() => inputRef.current?.click()}
      >
        <Upload className="mr-2 h-4 w-4" />
        {uploading ? "Uploading…" : "Upload CSV"}
      </Button>
    </>
  );
}
```

- [ ] **Step 6: Create `frontend/app/knowledge/page.tsx`**

```tsx
"use client";
import { useCallback, useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ChunkTable } from "@/components/knowledge/ChunkTable";
import { ChunkDialog } from "@/components/knowledge/ChunkDialog";
import { CsvUpload } from "@/components/knowledge/CsvUpload";
import { api, type KnowledgeChunk, type KnowledgeCategory } from "@/lib/api";

export default function KnowledgePage() {
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editChunk, setEditChunk] = useState<KnowledgeChunk | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.knowledge.list({ page, limit: 20 });
      setChunks(data.items);
      setTotal(data.total);
    } catch {
      toast.error("Failed to load knowledge base");
    }
  }, [page]);

  useEffect(() => { load(); }, [load]);

  function openCreate() {
    setEditChunk(null);
    setDialogOpen(true);
  }

  function openEdit(chunk: KnowledgeChunk) {
    setEditChunk(chunk);
    setDialogOpen(true);
  }

  async function handleSave(data: { content: string; category: KnowledgeCategory; metadata: Record<string, unknown> }) {
    try {
      if (editChunk) {
        await api.knowledge.update(editChunk.id, data);
        toast.success("Chunk updated");
      } else {
        await api.knowledge.create(data);
        toast.success("Chunk created");
      }
      await load();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Save failed");
      throw err;  // re-throw so dialog stays open on error
    }
  }

  async function handleDelete(id: string) {
    try {
      await api.knowledge.delete(id);
      toast.success("Chunk deleted");
      await load();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Delete failed");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Knowledge Base</h2>
          <p className="text-sm text-muted-foreground">{total} chunks total</p>
        </div>
        <div className="flex gap-2">
          <CsvUpload onDone={load} />
          <Button onClick={openCreate}>
            <Plus className="mr-2 h-4 w-4" />
            Add Chunk
          </Button>
        </div>
      </div>

      <ChunkTable chunks={chunks} onEdit={openEdit} onDelete={handleDelete} />

      {/* Pagination */}
      {total > 20 && (
        <div className="flex justify-center gap-2">
          <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <span className="py-1 text-sm">Page {page} of {Math.ceil(total / 20)}</span>
          <Button variant="outline" size="sm" disabled={page * 20 >= total} onClick={() => setPage((p) => p + 1)}>
            Next
          </Button>
        </div>
      )}

      <ChunkDialog
        open={dialogOpen}
        chunk={editChunk}
        onClose={() => setDialogOpen(false)}
        onSave={handleSave}
      />
    </div>
  );
}
```

- [ ] **Step 7: Run E2E tests**

Ensure the dev server is running (`npm run dev` in a separate terminal), then:

```bash
cd frontend && npx playwright test tests/e2e/knowledge.spec.ts
```

Expected: 4 tests PASS

- [ ] **Step 8: Commit**

```bash
cd /home/quocanh/live-tiktok/livetiktok
git add frontend/app/knowledge/ frontend/components/knowledge/ frontend/tests/e2e/knowledge.spec.ts
git commit -m "feat: Knowledge Base page — CRUD table + create/edit dialog + CSV upload"
```

---

## Task 6: Live Monitor Page

**Files:**
- Create: `frontend/app/monitor/page.tsx`
- Create: `frontend/components/monitor/SessionControl.tsx`
- Create: `frontend/components/monitor/CommentFeed.tsx`
- Create: `frontend/components/monitor/BotControls.tsx`
- Create: `frontend/hooks/useSession.ts`
- Create: `frontend/tests/e2e/monitor.spec.ts`

- [ ] **Step 1: Write E2E test first**

Create `frontend/tests/e2e/monitor.spec.ts`:

```typescript
import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  // Mock session status
  await page.route("**/api/v1/sessions/status", (route) => {
    route.fulfill({ json: { connected: false, session: null } });
  });
  await page.route("**/api/v1/sessions/start", (route) => {
    route.fulfill({
      json: {
        connected: true,
        session: { id: "s1", seller_id: "s1", status: "active", started_at: new Date().toISOString() },
      },
    });
  });
  await page.route("**/api/v1/sessions/stop", (route) => {
    route.fulfill({ json: { message: "Session stopped" } });
  });
});

test("monitor page loads with session offline status", async ({ page }) => {
  await page.goto("/monitor");
  await expect(page.getByText(/offline/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /start session/i })).toBeVisible();
});

test("can start a session", async ({ page }) => {
  await page.goto("/monitor");
  await page.getByRole("button", { name: /start session/i }).click();
  // After start, status changes — button should flip to Stop
  await expect(page.getByRole("button", { name: /stop session/i })).toBeVisible({ timeout: 3000 });
});

test("can stop an active session", async ({ page }) => {
  // Override initial status to active
  await page.route("**/api/v1/sessions/status", (route) => {
    route.fulfill({
      json: {
        connected: true,
        session: { id: "s1", seller_id: "s1", status: "active", started_at: new Date().toISOString() },
      },
    });
  });
  await page.goto("/monitor");
  await expect(page.getByRole("button", { name: /stop session/i })).toBeVisible();
  await page.getByRole("button", { name: /stop session/i }).click();
  await expect(page.getByRole("button", { name: /start session/i })).toBeVisible({ timeout: 3000 });
});
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd frontend && npx playwright test tests/e2e/monitor.spec.ts 2>&1 | head -15
```

Expected: tests fail (page not implemented).

- [ ] **Step 3: Create `frontend/hooks/useSession.ts`**

```typescript
"use client";
import { useState, useEffect, useCallback } from "react";
import { api, type SessionState } from "@/lib/api";

export function useSession() {
  const [state, setState] = useState<SessionState>({ connected: false, session: null });
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const s = await api.sessions.status();
      setState(s);
    } catch {
      setState({ connected: false, session: null });
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  async function start() {
    setLoading(true);
    try {
      const s = await api.sessions.start();
      setState(s);
    } finally {
      setLoading(false);
    }
  }

  async function stop() {
    setLoading(true);
    try {
      await api.sessions.stop();
      setState({ connected: false, session: null });
    } finally {
      setLoading(false);
    }
  }

  return { state, loading, start, stop, refresh };
}
```

- [ ] **Step 4: Create `frontend/components/monitor/SessionControl.tsx`**

```tsx
"use client";
import { Power, Wifi, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { SessionState } from "@/lib/api";

interface Props {
  state: SessionState;
  loading: boolean;
  onStart: () => void;
  onStop: () => void;
}

export function SessionControl({ state, loading, onStart, onStop }: Props) {
  return (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-2">
        {state.connected ? (
          <Wifi className="h-5 w-5 text-green-500" />
        ) : (
          <WifiOff className="h-5 w-5 text-slate-400" />
        )}
        <Badge variant={state.connected ? "default" : "secondary"}>
          {state.connected ? "Live" : "Offline"}
        </Badge>
        {state.session?.tiktok_room_id && (
          <span className="text-xs text-muted-foreground">
            Room {state.session.tiktok_room_id}
          </span>
        )}
      </div>

      {state.connected ? (
        <Button variant="destructive" size="sm" disabled={loading} onClick={onStop}>
          <Power className="mr-2 h-4 w-4" />
          {loading ? "Stopping…" : "Stop Session"}
        </Button>
      ) : (
        <Button size="sm" disabled={loading} onClick={onStart}>
          <Power className="mr-2 h-4 w-4" />
          {loading ? "Starting…" : "Start Session"}
        </Button>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Create `frontend/components/monitor/CommentFeed.tsx`**

```tsx
"use client";
import { useEffect, useRef } from "react";
import { Badge } from "@/components/ui/badge";
import type { WSMessage } from "@/lib/ws";

export type FeedItem =
  | (Extract<WSMessage, { type: "comment" }> & { reply?: string; intent?: string })

interface Props {
  items: FeedItem[];
  selectedId?: string | null;
  onSelect?: (messageId: string) => void;
}

export function CommentFeed({ items, selectedId, onSelect }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new items arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [items.length]);

  return (
    <div className="flex flex-col gap-2 h-[480px] overflow-y-auto rounded-md border bg-slate-50 p-3">
      {items.length === 0 && (
        <p className="m-auto text-sm text-muted-foreground">
          Waiting for comments…
        </p>
      )}
      {items.map((item) => (
        <div
          key={item.message_id}
          data-message-id={item.message_id}
          onClick={() => onSelect?.(item.message_id)}
          className={`rounded-md bg-white border p-3 text-sm shadow-sm cursor-pointer transition-colors ${
            selectedId === item.message_id ? "ring-2 ring-primary" : "hover:border-slate-300"
          }`}
        >
          <div className="flex items-center justify-between gap-2 mb-1">
            <span className="font-semibold text-slate-800">{item.user}</span>
            <div className="flex items-center gap-1">
              {item.intent && (
                <Badge variant="outline" className="text-xs">{item.intent}</Badge>
              )}
              <span className="text-xs text-muted-foreground">
                {new Date(item.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>
          <p className="text-slate-700">{item.content}</p>
          {item.reply && (
            <p className="mt-2 pl-3 border-l-2 border-green-400 text-slate-600 text-xs italic">
              Bot: {item.reply}
            </p>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
```

- [ ] **Step 6: Create `frontend/components/monitor/BotControls.tsx`**

```tsx
"use client";
import { useState } from "react";
import { Pause, Play, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { wsClient } from "@/lib/ws";

interface Props {
  paused: boolean;
  connected: boolean;
  replyTargetId: string | null;  // message_id for manual reply
}

export function BotControls({ paused, connected, replyTargetId }: Props) {
  const [manualText, setManualText] = useState("");

  function togglePause() {
    wsClient.send({ type: paused ? "resume_bot" : "pause_bot" });
  }

  function sendManualReply() {
    if (!manualText.trim() || !replyTargetId) return;
    wsClient.send({ type: "manual_reply", message_id: replyTargetId, content: manualText.trim() });
    setManualText("");
  }

  return (
    <div className="flex flex-col gap-3">
      <Button
        variant={paused ? "default" : "outline"}
        size="sm"
        disabled={!connected}
        onClick={togglePause}
      >
        {paused ? <Play className="mr-2 h-4 w-4" /> : <Pause className="mr-2 h-4 w-4" />}
        {paused ? "Resume Bot" : "Pause Bot"}
      </Button>

      <div className="flex gap-2">
        <Input
          placeholder={replyTargetId ? "Type manual reply…" : "Select a comment first"}
          value={manualText}
          disabled={!connected || !replyTargetId}
          onChange={(e) => setManualText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendManualReply()}
        />
        <Button
          size="icon"
          disabled={!connected || !replyTargetId || !manualText.trim()}
          onClick={sendManualReply}
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Create `frontend/app/monitor/page.tsx`**

```tsx
"use client";
import { useState, useCallback } from "react";
import { toast } from "sonner";
import { SessionControl } from "@/components/monitor/SessionControl";
import { CommentFeed, type FeedItem } from "@/components/monitor/CommentFeed";
import { BotControls } from "@/components/monitor/BotControls";
import { useSession } from "@/hooks/useSession";
import { useWebSocket } from "@/hooks/useWebSocket";

export default function MonitorPage() {
  const { state, loading, start, stop, refresh } = useSession();
  const [feedItems, setFeedItems] = useState<FeedItem[]>([]);
  const [paused, setPaused] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const addOrUpdate = useCallback((updater: (items: FeedItem[]) => FeedItem[]) => {
    setFeedItems(updater);
  }, []);

  useWebSocket({
    comment: (msg) => {
      addOrUpdate((items) => [...items, { ...msg }]);
    },
    reply: (msg) => {
      addOrUpdate((items) =>
        items.map((item) =>
          item.message_id === msg.message_id
            ? { ...item, reply: msg.content, intent: msg.intent }
            : item,
        ),
      );
    },
    status: (msg) => {
      if (typeof msg.connected === "boolean") {
        refresh();
      }
      if (typeof msg.paused === "boolean") {
        setPaused(msg.paused);
      }
    },
    error: (msg) => {
      toast.error(msg.message);
    },
  });

  async function handleStart() {
    try {
      await start();
      toast.success("Session started");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to start session");
    }
  }

  async function handleStop() {
    try {
      await stop();
      setFeedItems([]);
      toast.success("Session stopped");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to stop session");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Live Monitor</h2>
        <SessionControl
          state={state}
          loading={loading}
          onStart={handleStart}
          onStop={handleStop}
        />
      </div>

      <div className="grid grid-cols-[1fr_260px] gap-4">
        {/* Comment feed — click a card to select it for manual reply */}
        <CommentFeed
          items={feedItems}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />

        {/* Bot controls sidebar */}
        <div className="space-y-4 rounded-md border p-4">
          <h3 className="font-semibold text-sm">Bot Controls</h3>
          <BotControls
            paused={paused}
            connected={state.connected}
            replyTargetId={selectedId}
          />
          {state.session && (
            <div className="text-xs text-muted-foreground space-y-1 border-t pt-3">
              <p>Session ID: <span className="font-mono">{state.session.id.slice(0, 8)}…</span></p>
              <p>Started: {new Date(state.session.started_at).toLocaleTimeString()}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 8: Run E2E tests**

```bash
cd frontend && npx playwright test tests/e2e/monitor.spec.ts
```

Expected: 3 tests PASS

- [ ] **Step 9: Commit**

```bash
cd /home/quocanh/live-tiktok/livetiktok
git add frontend/app/monitor/ frontend/components/monitor/ frontend/hooks/ frontend/tests/e2e/monitor.spec.ts
git commit -m "feat: Live Monitor page — session control, realtime comment feed, bot pause/resume"
```

---

## Task 7: Settings Page

**Files:**
- Create: `frontend/app/settings/page.tsx`
- Create: `frontend/components/settings/SettingsForm.tsx`
- Create: `frontend/components/settings/TestReply.tsx`
- Create: `frontend/tests/e2e/settings.spec.ts`

- [ ] **Step 1: Write E2E test first**

Create `frontend/tests/e2e/settings.spec.ts`:

```typescript
import { test, expect } from "@playwright/test";

const MOCK_SETTINGS = {
  tone: "friendly",
  blacklist_keywords: ["spam"],
  reply_delay_min: 5,
  reply_delay_max: 15,
  user_cooldown_seconds: 60,
  max_replies_per_session: 500,
  auto_reply_enabled: true,
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/settings/**", (route) => {
    const method = route.request().method();
    if (method === "GET") {
      route.fulfill({ json: MOCK_SETTINGS });
    } else if (method === "PUT") {
      route.fulfill({ json: { ...MOCK_SETTINGS, tone: "professional" } });
    } else {
      route.continue();
    }
  });
  await page.route("**/api/v1/settings/test-reply", (route) => {
    route.fulfill({ json: { reply: "Dạ shop có ạ!", intent: "product_inquiry", chunks_used: ["c1"] } });
  });
});

test("settings page loads and shows current settings", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByDisplayValue("friendly")).toBeVisible();
  await expect(page.getByText("Auto Reply")).toBeVisible();
});

test("can update settings", async ({ page }) => {
  await page.goto("/settings");
  // Change tone field
  const toneInput = page.getByLabel(/tone/i);
  await toneInput.fill("professional");
  await page.getByRole("button", { name: /save settings/i }).click();
  await expect(page.getByText(/saved/i)).toBeVisible({ timeout: 3000 });
});

test("can run test-reply", async ({ page }) => {
  await page.goto("/settings");
  await page.getByPlaceholder(/enter a test comment/i).fill("Còn hàng không?");
  await page.getByRole("button", { name: /test reply/i }).click();
  await expect(page.getByText("Dạ shop có ạ!")).toBeVisible({ timeout: 3000 });
});
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd frontend && npx playwright test tests/e2e/settings.spec.ts 2>&1 | head -15
```

Expected: tests fail.

- [ ] **Step 3: Create `frontend/components/settings/SettingsForm.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type BotSettings } from "@/lib/api";

export function SettingsForm() {
  const [settings, setSettings] = useState<BotSettings | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.settings.get().then(setSettings).catch(() => toast.error("Failed to load settings"));
  }, []);

  if (!settings) return <p className="text-sm text-muted-foreground">Loading…</p>;

  function update<K extends keyof BotSettings>(key: K, value: BotSettings[K]) {
    setSettings((s) => (s ? { ...s, [key]: value } : s));
  }

  async function handleSave() {
    if (!settings) return;
    setSaving(true);
    try {
      const updated = await api.settings.update(settings);
      setSettings(updated);
      toast.success("Settings saved");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6 max-w-md">
      <div className="grid gap-2">
        <Label htmlFor="tone">Tone</Label>
        <Input
          id="tone"
          value={settings.tone}
          onChange={(e) => update("tone", e.target.value)}
          placeholder="friendly, professional, casual…"
        />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="blacklist">Blacklist Keywords (comma-separated)</Label>
        <Input
          id="blacklist"
          value={settings.blacklist_keywords.join(", ")}
          onChange={(e) =>
            update("blacklist_keywords", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))
          }
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="grid gap-2">
          <Label htmlFor="delay-min">Reply Delay Min (s)</Label>
          <Input
            id="delay-min"
            type="number"
            min={0}
            value={settings.reply_delay_min}
            onChange={(e) => update("reply_delay_min", Number(e.target.value))}
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="delay-max">Reply Delay Max (s)</Label>
          <Input
            id="delay-max"
            type="number"
            min={0}
            value={settings.reply_delay_max}
            onChange={(e) => update("reply_delay_max", Number(e.target.value))}
          />
        </div>
      </div>

      <div className="grid gap-2">
        <Label htmlFor="cooldown">User Cooldown (s)</Label>
        <Input
          id="cooldown"
          type="number"
          min={0}
          value={settings.user_cooldown_seconds}
          onChange={(e) => update("user_cooldown_seconds", Number(e.target.value))}
        />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="max-replies">Max Replies per Session</Label>
        <Input
          id="max-replies"
          type="number"
          min={1}
          value={settings.max_replies_per_session}
          onChange={(e) => update("max_replies_per_session", Number(e.target.value))}
        />
      </div>

      <div className="flex items-center gap-3">
        <input
          id="auto-reply"
          type="checkbox"
          className="h-4 w-4 accent-primary"
          checked={settings.auto_reply_enabled}
          onChange={(e) => update("auto_reply_enabled", e.target.checked)}
        />
        <Label htmlFor="auto-reply">Auto Reply</Label>
      </div>

      <Button disabled={saving} onClick={handleSave}>
        {saving ? "Saving…" : "Save Settings"}
      </Button>
    </div>
  );
}
```

- [ ] **Step 4: Create `frontend/components/settings/TestReply.tsx`**

```tsx
"use client";
import { useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { api, type TestReplyResult } from "@/lib/api";

export function TestReply() {
  const [comment, setComment] = useState("");
  const [result, setResult] = useState<TestReplyResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleTest() {
    if (!comment.trim()) return;
    setLoading(true);
    try {
      const r = await api.settings.testReply(comment.trim());
      setResult(r);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Test failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3 max-w-md">
      <div className="flex gap-2">
        <Input
          placeholder="Enter a test comment…"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleTest()}
        />
        <Button disabled={loading || !comment.trim()} onClick={handleTest}>
          <Send className="mr-2 h-4 w-4" />
          {loading ? "Testing…" : "Test Reply"}
        </Button>
      </div>

      {result && (
        <div className="rounded-md border bg-slate-50 p-4 space-y-2">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Intent:</span>
            <Badge variant="outline">{result.intent}</Badge>
          </div>
          <p className="text-sm font-medium">Bot reply:</p>
          <p className="text-sm text-slate-700 italic">"{result.reply}"</p>
          {result.chunks_used.length > 0 && (
            <p className="text-xs text-muted-foreground">
              Used chunks: {result.chunks_used.join(", ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Create `frontend/app/settings/page.tsx`**

```tsx
import { SettingsForm } from "@/components/settings/SettingsForm";
import { TestReply } from "@/components/settings/TestReply";
import { Separator } from "@/components/ui/separator";

export default function SettingsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold">Settings</h2>
        <p className="text-sm text-muted-foreground">Configure bot behavior and test replies.</p>
      </div>

      <div>
        <h3 className="text-lg font-semibold mb-4">Bot Configuration</h3>
        <SettingsForm />
      </div>

      <Separator />

      <div>
        <h3 className="text-lg font-semibold mb-1">Test Reply</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Preview how the bot would respond to a comment. Does not send to TikTok.
        </p>
        <TestReply />
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Run E2E tests**

```bash
cd frontend && npx playwright test tests/e2e/settings.spec.ts
```

Expected: 3 tests PASS

- [ ] **Step 7: Run all unit tests**

```bash
cd frontend && npx vitest run
```

Expected: all unit tests PASS (api + ws)

- [ ] **Step 8: Run all E2E tests**

```bash
cd frontend && npx playwright test
```

Expected: all 10 E2E tests PASS

- [ ] **Step 9: Commit**

```bash
cd /home/quocanh/live-tiktok/livetiktok
git add frontend/app/settings/ frontend/components/settings/ frontend/tests/e2e/settings.spec.ts
git commit -m "feat: Settings page — bot config form + test-reply preview"
```

---

## Task 8: Dockerfile + docker-compose + Makefile Update

**Files:**
- Create: `frontend/Dockerfile`
- Modify: root `Makefile` — add `install-fe` and `dev-frontend` targets (already exist, verify they work)
- Create: `docker-compose.yml` (if not present) — wire frontend + backend services

- [ ] **Step 1: Create `frontend/Dockerfile`**

```dockerfile
# Stage 1: build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: production server
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

Note: for the standalone output to work, add `output: "standalone"` to the existing `frontend/next.config.ts` (created in Task 1 Step 8). Open the file and add the field inside the existing `nextConfig` object — do NOT replace the `rewrites()` function:

```typescript
const nextConfig: NextConfig = {
  output: "standalone",   // ADD this line
  async rewrites() {      // keep the existing rewrites from Task 1
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
      },
    ];
  },
};
```

- [ ] **Step 2: Check if `docker-compose.yml` exists at repo root**

```bash
ls /home/quocanh/live-tiktok/livetiktok/docker-compose.yml 2>/dev/null || echo "NOT FOUND"
```

If NOT FOUND, create it:

```yaml
# docker-compose.yml — production
version: "3.9"

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    volumes:
      - chroma_data:/app/chroma_data
      - ./backend/app.db:/app/app.db
    restart: unless-stopped
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
      - NEXT_PUBLIC_WS_URL=ws://backend:8000
      - NEXT_PUBLIC_SELLER_ID=${SELLER_ID}
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  chroma_data:
```

- [ ] **Step 3: Verify Makefile `install-fe` and `dev-frontend` targets work**

```bash
cd /home/quocanh/live-tiktok/livetiktok/frontend && npm install && npm run dev &
sleep 5 && curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

Expected: `200` (or `307` for redirect to /monitor)

Kill the background server after check.

- [ ] **Step 4: Build production Docker image to verify**

```bash
cd /home/quocanh/live-tiktok/livetiktok/frontend && docker build -t livetiktok-frontend:test . 2>&1 | tail -5
```

Expected: `Successfully built ...`

- [ ] **Step 5: Commit**

```bash
cd /home/quocanh/live-tiktok/livetiktok
git add frontend/Dockerfile frontend/next.config.ts docker-compose.yml
git commit -m "feat: frontend Dockerfile + docker-compose wiring"
git tag plan3-complete
```

---

## Summary: What Plan 3 Delivers

| Component | Files | Tests |
|-----------|-------|-------|
| REST API client | `lib/api.ts` | 9 unit tests (Vitest) |
| WebSocket client | `lib/ws.ts`, `hooks/useWebSocket.ts` | 6 unit tests (Vitest) |
| Root layout + nav | `app/layout.tsx`, `components/nav/Sidebar.tsx` | E2E smoke |
| Knowledge page | `app/knowledge/page.tsx` + 3 components | 4 E2E tests (Playwright) |
| Monitor page | `app/monitor/page.tsx` + 3 components | 3 E2E tests (Playwright) |
| Settings page | `app/settings/page.tsx` + 2 components | 3 E2E tests (Playwright) |
| Docker + compose | `frontend/Dockerfile`, `docker-compose.yml` | Docker build check |

**Total: 15 unit tests + 10 E2E tests**

**Next:** Plan 4 — Integration testing with a real TikTok stream + onboarding script for first sellers.
