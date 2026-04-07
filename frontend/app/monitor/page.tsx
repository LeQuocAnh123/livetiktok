"use client";
import { useState, useCallback } from "react";
import { toast } from "sonner";
import { SessionControl } from "@/components/monitor/SessionControl";
import { CommentFeed, type FeedItem } from "@/components/monitor/CommentFeed";
import { BotControls } from "@/components/monitor/BotControls";
import { useSession } from "@/hooks/useSession";
import { useWebSocket } from "@/hooks/useWebSocket";

const MAX_FEED_ITEMS = 200;

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
      addOrUpdate((items) => {
        const updated = [...items, { ...msg }];
        // Keep only the most recent MAX_FEED_ITEMS items
        if (updated.length > MAX_FEED_ITEMS) {
          const trimmed = updated.slice(-MAX_FEED_ITEMS);
          // Clear selection if selected item was removed
          const removedIds = new Set(
            updated.slice(0, updated.length - MAX_FEED_ITEMS).map((i) => i.message_id)
          );
          if (selectedId && removedIds.has(selectedId)) {
            setSelectedId(null);
          }
          return trimmed;
        }
        return updated;
      });
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
        <CommentFeed
          items={feedItems}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />

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
