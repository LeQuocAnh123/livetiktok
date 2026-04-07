import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { WSClient } from "@/lib/ws";

// ── Mock WebSocket ───────────────────────────────────────────────────────────
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: ((event: { code: number }) => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(_url: string) {
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.onopen?.();
    }, 0);
  }

  send = vi.fn();

  close(code = 1000) {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ code });
  }
}

vi.stubGlobal("WebSocket", MockWebSocket);

describe("WSClient", () => {
  let wsClient: WSClient;
  let mockWS: MockWebSocket;

  beforeEach(() => {
    vi.useFakeTimers();
    wsClient = new WSClient();
    wsClient.connect("ws://localhost:8000/ws/monitor");
    mockWS = wsClient._ws as unknown as MockWebSocket;
  });

  afterEach(() => {
    wsClient.disconnect();
    vi.useRealTimers();
  });

  it("connects to the WebSocket server", async () => {
    await vi.runAllTimersAsync();
    expect(mockWS.readyState).toBe(MockWebSocket.OPEN);
  });

  it("emits connection status on connect", async () => {
    const handler = vi.fn();
    wsClient.on("connection", handler);
    await vi.runAllTimersAsync();
    expect(handler).toHaveBeenCalledWith({ type: "connection", status: "connected" });
  });

  it("dispatches messages to registered handlers", async () => {
    await vi.runAllTimersAsync();
    const handler = vi.fn();
    wsClient.on("comment", handler);

    const msg = { type: "comment", message_id: "1", user: "u", content: "hi", timestamp: "" };
    mockWS.onmessage?.({ data: JSON.stringify(msg) });

    expect(handler).toHaveBeenCalledWith(msg);
  });

  it("unsubscribes handler when calling returned function", async () => {
    await vi.runAllTimersAsync();
    const handler = vi.fn();
    const unsub = wsClient.on("comment", handler);
    unsub();

    const msg = { type: "comment", message_id: "1", user: "u", content: "hi", timestamp: "" };
    mockWS.onmessage?.({ data: JSON.stringify(msg) });

    expect(handler).not.toHaveBeenCalled();
  });

  it("sends messages when connected", async () => {
    await vi.runAllTimersAsync();
    const result = wsClient.send({ type: "pause_bot" });
    expect(result).toBe(true);
    expect(mockWS.send).toHaveBeenCalledWith('{"type":"pause_bot"}');
  });

  it("returns false when sending while disconnected", () => {
    wsClient.disconnect();
    const result = wsClient.send({ type: "pause_bot" });
    expect(result).toBe(false);
  });

  it("closes the WebSocket connection", async () => {
    await vi.runAllTimersAsync();
    wsClient.disconnect();
    expect(mockWS.readyState).toBe(MockWebSocket.CLOSED);
  });

  it("does not auto-reconnect after manual disconnect", async () => {
    await vi.runAllTimersAsync();
    wsClient.disconnect();

    // Advance timers - should not reconnect
    await vi.advanceTimersByTimeAsync(5000);
    expect(wsClient._ws).toBeNull();
  });

  it("schedules reconnect on abnormal close", async () => {
    await vi.runAllTimersAsync();
    const connectionHandler = vi.fn();
    wsClient.on("connection", connectionHandler);

    // Simulate abnormal close
    mockWS.onclose?.({ code: 1006 });

    expect(connectionHandler).toHaveBeenCalledWith({ type: "connection", status: "disconnected" });
    expect(connectionHandler).toHaveBeenCalledWith({ type: "connection", status: "reconnecting" });
  });
});
