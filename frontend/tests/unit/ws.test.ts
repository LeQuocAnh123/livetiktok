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
  mockWS = wsClient._ws as unknown as MockWebSocket;
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
    mockWS.receive({
      type: "comment",
      message_id: "m1",
      user: "alice",
      content: "hello",
      timestamp: "2026-01-01T00:00:00Z",
    });
    expect(handler).toHaveBeenCalledWith(
      expect.objectContaining({ type: "comment", user: "alice" })
    );
    wsClient.off("comment", handler);
  });

  it("does not call listener after off()", () => {
    const handler = vi.fn();
    wsClient.on("comment", handler);
    wsClient.off("comment", handler);
    mockWS.receive({
      type: "comment",
      message_id: "m2",
      user: "bob",
      content: "hi",
      timestamp: "",
    });
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
