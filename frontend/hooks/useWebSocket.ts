"use client";
// hooks/useWebSocket.ts — React hook for the WS singleton

import { useEffect, useRef } from "react";
import { wsClient, type WSMessage } from "@/lib/ws";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
const WS_TOKEN = process.env.NEXT_PUBLIC_WS_TOKEN ?? "";

/**
 * Subscribes to wsClient events for the handler types present at mount time.
 * Handler *values* may change between renders — the latest version is always
 * called via handlersRef. However, new handler *keys* added after mount are
 * NOT subscribed. Pass a stable, complete set of handler keys.
 *
 * Does not automatically reconnect if the server closes the connection.
 * For reconnection, call wsClient.connect() manually or re-mount the component.
 */
export function useWebSocket(
  handlers: Partial<{
    [T in WSMessage as T["type"]]: (msg: Extract<WSMessage, { type: T["type"] }>) => void;
  }>,
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
