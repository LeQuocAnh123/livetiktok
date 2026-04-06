"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { SessionList } from "@/components/sessions/SessionList";
import { SessionDetail } from "@/components/sessions/SessionDetail";
import { api, type Session } from "@/lib/api";

export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.sessions
      .history()
      .then((data) => {
        setSessions(data);
        if (data.length > 0) setSelectedId(data[0].id);
      })
      .catch(() => toast.error("Không tải được lịch sử"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Lịch sử buổi live</h2>
        <p className="text-sm text-muted-foreground">Xem lại comment và reply của từng buổi</p>
      </div>

      {loading && <p className="text-sm text-muted-foreground">Đang tải…</p>}

      {!loading && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_420px]">
          <div className="rounded-md border">
            <SessionList
              sessions={sessions}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          </div>

          {selectedId && (
            <div className="rounded-md border p-3">
              <h3 className="text-sm font-semibold mb-3">Chi tiết buổi live</h3>
              <SessionDetail sessionId={selectedId} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
