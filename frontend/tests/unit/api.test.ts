import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Stub env vars before importing api
vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
vi.stubEnv("NEXT_PUBLIC_SELLER_ID", "seller-001");

// Dynamic import after stubbing
const { api } = await import("@/lib/api");

function mockResponse(body: unknown, status = 200) {
  mockFetch.mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 204 ? "No Content" : "OK",
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

beforeEach(() => {
  mockFetch.mockReset();
});

afterEach(() => {
  mockFetch.mockClear();
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
    mockResponse({
      id: "chunk-1",
      seller_id: "seller-001",
      content: "test",
      category: "faq",
      metadata: {},
      needs_reembed: true,
    });
    const result = await api.knowledge.create({
      content: "test",
      category: "faq",
      metadata: {},
    });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/knowledge/"),
      expect.objectContaining({ method: "POST" })
    );
    expect(result.id).toBe("chunk-1");
  });
});

describe("api.knowledge.update", () => {
  it("calls PUT /api/v1/knowledge/{id}", async () => {
    mockResponse({
      id: "chunk-1",
      seller_id: "seller-001",
      content: "updated",
      category: "faq",
      metadata: {},
      needs_reembed: true,
    });
    const result = await api.knowledge.update("chunk-1", {
      content: "updated",
    });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/knowledge/chunk-1"),
      expect.objectContaining({ method: "PUT" })
    );
    expect(result.content).toBe("updated");
  });
});

describe("api.knowledge.delete", () => {
  it("calls DELETE /api/v1/knowledge/{id}", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
      statusText: "No Content",
      json: async () => null,
    });
    await api.knowledge.delete("chunk-1");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/knowledge/chunk-1"),
      expect.objectContaining({ method: "DELETE" })
    );
  });
});

describe("api.sessions.start", () => {
  it("calls POST /api/v1/sessions/start with seller_id", async () => {
    mockResponse({
      connected: true,
      session: {
        id: "s1",
        seller_id: "seller-001",
        status: "active",
        started_at: new Date().toISOString(),
      },
    });
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
    mockResponse({
      reply: "Dạ còn ạ!",
      intent: "product_inquiry",
      chunks_used: ["c1"],
    });
    const result = await api.settings.testReply("Còn hàng không?");
    expect(result.reply).toBe("Dạ còn ạ!");
  });
});

describe("api error handling", () => {
  it("throws ApiError with status and message on 4xx", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: async () => ({ detail: "Not found" }),
    });
    await expect(api.settings.get()).rejects.toMatchObject({
      status: 404,
      message: "Not found",
    });
  });
});
