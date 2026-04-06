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

    const unsubs = (Object.keys(handlers) as Array<keyof typeof handlers>).map(
      (type) =>
        // wsClient.on<T>(type, ...) narrows `msg` to the specific variant
        // matching `type`, so the handler from the ref is safe to invoke
        // without an unsafe `as (m: WSMessage) => void` cast.
        wsClient.on(type, (msg) => {
          (
            handlersRef.current[type] as
              | ((m: typeof msg) => void)
              | undefined
          )?.(msg);
        }),
    );

    return () => {
      unsubs.forEach((u) => u());
    };
    // Only run once — handlers are accessed via ref
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
