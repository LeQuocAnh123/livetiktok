// lib/ws.ts — WebSocket singleton client with auto-reconnect

export type WSMessage =
  | {
      type: "comment";
      message_id: string;
      user: string;
      content: string;
      timestamp: string;
    }
  | { type: "reply"; message_id: string; content: string; intent: string; chunks_used: string[] }
  | {
      type: "reply_failed";
      message_id: string;
      content: string;
      error: string;
    }
  | {
      type: "gift";
      gift_log_id: string;
      user: string;
      gift_name: string;
      diamond_count: number;
      repeat_count: number;
      total_diamonds: number;
      estimated_usd: number;
      timestamp: string;
    }
  | { type: "gift_reply"; gift_log_id: string; user: string; content: string }
  | { type: "status"; connected?: boolean; paused?: boolean; room_id?: number }
  | { type: "error"; message: string }
  | { type: "alert"; severity: string; message_id: string; comment: string; user: string }
  | { type: "connection"; status: "connecting" | "connected" | "disconnected" | "reconnecting" };

type Handler<T extends WSMessage = WSMessage> = (msg: T) => void;

export type SendMessage =
  | { type: "pause_bot" }
  | { type: "resume_bot" }
  | { type: "manual_reply"; message_id: string; content: string };

const MAX_RETRIES = 10;
const BASE_DELAY_MS = 1000;
const MAX_DELAY_MS = 16000;

export class WSClient {
  _ws: WebSocket | null = null;
  private _listeners: Map<string, Set<Handler>> = new Map();
  private _url: string = "";
  private _reconnectAttempt: number = 0;
  private _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _manualDisconnect: boolean = false;

  connect(url: string): void {
    if (this._ws && this._ws.readyState <= WebSocket.OPEN) return;

    this._url = url;
    this._manualDisconnect = false;
    this._doConnect();
  }

  private _doConnect(): void {
    this._emit({ type: "connection", status: "connecting" });

    this._ws = new WebSocket(this._url);

    this._ws.onopen = () => {
      this._reconnectAttempt = 0;
      this._emit({ type: "connection", status: "connected" });
    };

    this._ws.onmessage = (event: MessageEvent) => {
      let msg: WSMessage;
      try {
        msg = JSON.parse(event.data as string) as WSMessage;
      } catch {
        return;
      }
      this._emit(msg);
    };

    this._ws.onerror = () => {
      // Suppress — onclose will follow
    };

    this._ws.onclose = (event) => {
      this._emit({ type: "connection", status: "disconnected" });

      // Don't reconnect if manually disconnected or normal close
      if (this._manualDisconnect || event.code === 1000) {
        return;
      }

      this._scheduleReconnect();
    };
  }

  private _scheduleReconnect(): void {
    if (this._reconnectAttempt >= MAX_RETRIES) {
      this._emit({ type: "error", message: "Max reconnection attempts reached" });
      return;
    }

    const delay = Math.min(
      BASE_DELAY_MS * Math.pow(2, this._reconnectAttempt),
      MAX_DELAY_MS
    );

    this._reconnectAttempt++;
    this._emit({ type: "connection", status: "reconnecting" });

    this._reconnectTimer = setTimeout(() => {
      this._doConnect();
    }, delay);
  }

  private _emit(msg: WSMessage): void {
    const handlers = this._listeners.get(msg.type);
    if (handlers) {
      handlers.forEach((h) => h(msg));
    }
  }

  disconnect(): void {
    this._manualDisconnect = true;

    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }

    if (this._ws) {
      this._ws.close(1000);
      this._ws = null;
    }
  }

  send(msg: SendMessage): boolean {
    if (this._ws?.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify(msg));
      return true;
    }
    return false;
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
