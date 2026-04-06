// lib/ws.ts — WebSocket singleton client

export type WSMessage =
  | {
      type: "comment";
      message_id: string;
      user: string;
      content: string;
      timestamp: string;
    }
  | { type: "reply"; message_id: string; content: string; intent: string; chunks_used: string[] }
  | { type: "status"; connected?: boolean; paused?: boolean; room_id?: number }
  | { type: "error"; message: string };

type Handler<T extends WSMessage = WSMessage> = (msg: T) => void;

export type SendMessage =
  | { type: "pause_bot" }
  | { type: "resume_bot" }
  | { type: "manual_reply"; message_id: string; content: string };

export class WSClient {
  // Intentionally public (no underscore-private) so test code can inspect or
  // stub the underlying socket without resorting to `as any` casts.
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
