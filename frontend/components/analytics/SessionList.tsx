"use client";

import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SessionListEntry } from "@/lib/api";

interface Props {
  sessions: SessionListEntry[];
}

const INTENT_LABELS: Record<string, string> = {
  product_inquiry: "Hỏi SP",
  greeting: "Chào hỏi",
  unknown: "Không rõ",
  skipped: "Bỏ qua",
  blacklist: "Từ cấm",
  none: "—",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(minutes: number): string {
  if (minutes < 60) return `${Math.round(minutes)} phút`;
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return `${h}h${m > 0 ? ` ${m}p` : ""}`;
}

export function SessionList({ sessions }: Props) {
  const router = useRouter();

  if (sessions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Danh sách buổi live</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Chưa có buổi live nào.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Danh sách buổi live</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="pb-2 pr-4 font-medium">Ngày/Giờ</th>
              <th className="pb-2 pr-4 font-medium">Thời lượng</th>
              <th className="pb-2 pr-4 font-medium text-right">Comments</th>
              <th className="pb-2 pr-4 font-medium text-right">Reply %</th>
              <th className="pb-2 pr-4 font-medium text-right">Gifts</th>
              <th className="pb-2 font-medium">Top Intent</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr
                key={s.id}
                className="border-b cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() => router.push(`/analytics/sessions/${s.id}`)}
              >
                <td className="py-2 pr-4">{formatDate(s.started_at)}</td>
                <td className="py-2 pr-4">{formatDuration(s.duration_minutes)}</td>
                <td className="py-2 pr-4 text-right">{s.comment_count}</td>
                <td className="py-2 pr-4 text-right">{s.reply_rate}%</td>
                <td className="py-2 pr-4 text-right">
                  {s.gift_count > 0 ? `${s.gift_count} (${s.gift_diamonds}💎)` : "—"}
                </td>
                <td className="py-2">{INTENT_LABELS[s.top_intent] ?? s.top_intent}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
