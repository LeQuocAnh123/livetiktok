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
