"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { api, type MessageLog } from "@/lib/api";

interface Props {
  sessionId: string;
}

export function SessionDetail({ sessionId }: Props) {
  const [messages, setMessages] = useState<MessageLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.sessions
      .messages(sessionId)
      .then(setMessages)
      .catch(() => toast.error("Không tải được tin nhắn"))
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) return <p className="text-sm text-muted-foreground p-4">Đang tải…</p>;
  if (messages.length === 0)
    return <p className="text-sm text-muted-foreground p-4">Không có comment nào.</p>;

  return (
    <div className="flex flex-col gap-2 max-h-[520px] overflow-y-auto pr-1">
      {messages.map((m) => (
        <div key={m.id} className="rounded-md border bg-white p-3 text-sm shadow-sm">
          <div className="flex items-center justify-between gap-2 mb-1">
            <span className="font-semibold text-slate-800">{m.user_unique_id}</span>
            <div className="flex items-center gap-1">
              <Badge variant="outline" className="text-xs">{m.intent}</Badge>
              <span className="text-xs text-muted-foreground">
                {new Date(m.created_at).toLocaleTimeString("vi-VN")}
              </span>
            </div>
          </div>
          <p className="text-slate-700">{m.comment}</p>
          {m.reply ? (
            <p className="mt-2 pl-3 border-l-2 border-green-400 text-slate-600 text-xs italic">
              Bot: {m.reply}
            </p>
          ) : (
            <p className="mt-2 pl-3 border-l-2 border-slate-200 text-xs text-muted-foreground italic">
              Không có reply
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
