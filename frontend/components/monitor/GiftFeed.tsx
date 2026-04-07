"use client";
import { useEffect, useRef } from "react";
import { Badge } from "@/components/ui/badge";
import { Gift } from "lucide-react";
import type { WSMessage } from "@/lib/ws";

export type GiftFeedItem = Extract<WSMessage, { type: "gift" }> & {
  reply?: string;
};

interface Props {
  items: GiftFeedItem[];
}

export function GiftFeed({ items }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [items.length]);

  return (
    <div className="flex flex-col gap-2 h-[480px] overflow-y-auto rounded-md border bg-amber-50 p-3">
      {items.length === 0 && (
        <p className="m-auto text-sm text-muted-foreground">
          Waiting for gifts…
        </p>
      )}
      {items.map((item) => (
        <div
          key={item.gift_log_id}
          className="rounded-md bg-white border border-amber-200 p-3 text-sm shadow-sm"
        >
          <div className="flex items-center justify-between gap-2 mb-1">
            <div className="flex items-center gap-1.5">
              <Gift className="h-4 w-4 text-amber-500" />
              <span className="font-semibold text-slate-800">{item.user}</span>
            </div>
            <div className="flex items-center gap-1">
              <Badge variant="outline" className="text-xs bg-amber-50 text-amber-700 border-amber-300">
                {item.gift_name}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {new Date(item.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>
          <p className="text-slate-700">
            {item.repeat_count}x {item.gift_name}
            <span className="ml-2 text-xs text-muted-foreground">
              ({item.total_diamonds} diamonds, ~${item.estimated_usd.toFixed(2)})
            </span>
          </p>
          {item.reply && (
            <p className="mt-2 pl-3 border-l-2 border-amber-400 text-slate-600 text-xs italic">
              Bot: {item.reply}
            </p>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
