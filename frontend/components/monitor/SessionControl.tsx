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
