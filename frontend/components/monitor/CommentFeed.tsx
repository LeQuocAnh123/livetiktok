"use client";
import { useEffect, useRef } from "react";
import { Badge } from "@/components/ui/badge";
import type { WSMessage } from "@/lib/ws";

export type FeedItem = Extract<WSMessage, { type: "comment" }> & {
  reply?: string;
  intent?: string;
};

interface Props {
  items: FeedItem[];
  selectedId?: string | null;
  onSelect?: (messageId: string) => void;
}

export function CommentFeed({ items, selectedId, onSelect }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [items.length]);

  return (
    <div className="flex flex-col gap-2 h-[480px] overflow-y-auto rounded-md border bg-slate-50 p-3">
      {items.length === 0 && (
        <p className="m-auto text-sm text-muted-foreground">
          Waiting for comments…
        </p>
      )}
      {items.map((item) => (
        <div
          key={item.message_id}
          data-message-id={item.message_id}
          role="button"
          tabIndex={0}
          onClick={() => onSelect?.(item.message_id)}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onSelect?.(item.message_id)}
          className={`rounded-md bg-white border p-3 text-sm shadow-sm cursor-pointer transition-colors ${
            selectedId === item.message_id ? "ring-2 ring-primary" : "hover:border-slate-300"
          }`}
        >
          <div className="flex items-center justify-between gap-2 mb-1">
            <span className="font-semibold text-slate-800">{item.user}</span>
            <div className="flex items-center gap-1">
              {item.intent && (
                <Badge variant="outline" className="text-xs">{item.intent}</Badge>
              )}
              <span className="text-xs text-muted-foreground">
                {new Date(item.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>
          <p className="text-slate-700">{item.content}</p>
          {item.reply && (
            <p className="mt-2 pl-3 border-l-2 border-green-400 text-slate-600 text-xs italic">
              Bot: {item.reply}
            </p>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
