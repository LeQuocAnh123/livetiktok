"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { api, type SessionAnalyticsData } from "@/lib/api";
import { ActivityTimeline } from "@/components/analytics/ActivityTimeline";
import { KeywordCloud } from "@/components/analytics/KeywordCloud";
import { SentimentBreakdown } from "@/components/analytics/SentimentBreakdown";
import { IntentBreakdown } from "@/components/analytics/IntentBreakdown";
import { EngagementMetrics } from "@/components/analytics/EngagementMetrics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("vi-VN", {
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
  return `${h} giờ${m > 0 ? ` ${m} phút` : ""}`;
}

export default function SessionDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<SessionAnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!params.id) return;
    let cancelled = false;
    api.analytics
      .session(params.id)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(true);
          toast.error(err.message || "Không thể tải dữ liệu session");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  if (loading) {
    return <p className="text-sm text-muted-foreground p-6">Đang tải...</p>;
  }

  if (error || !data) {
    return (
      <div className="p-6 space-y-2">
        <p className="text-sm text-destructive">Không thể tải dữ liệu.</p>
        <button onClick={() => router.back()} className="text-sm underline">
          Quay lại
        </button>
      </div>
    );
  }

  const { session_info, summary, timeline, top_keywords, intent_breakdown, sentiment_breakdown, engagement_metrics } = data;

  const summaryCards = [
    { label: "Comments", value: summary.total_comments },
    { label: "Replies", value: summary.total_replies },
    { label: "Tỷ lệ reply", value: `${summary.reply_rate}%` },
    { label: "Gifts", value: summary.total_gifts },
    { label: "Diamonds", value: summary.total_diamonds },
    { label: "USD", value: `$${summary.estimated_usd}` },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.push("/analytics")}
          className="text-sm text-muted-foreground hover:text-foreground underline"
        >
          &larr; Analytics
        </button>
        <div>
          <h2 className="text-2xl font-bold">
            Session {formatDateTime(session_info.started_at)}
          </h2>
          <p className="text-sm text-muted-foreground">
            {formatDuration(session_info.duration_minutes)}
            {session_info.ended_at
              ? ` — kết thúc ${formatDateTime(session_info.ended_at)}`
              : " — đang diễn ra"}
          </p>
        </div>
      </div>

      {/* Summary KPI cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {summaryCards.map((c) => (
          <Card key={c.label}>
            <CardHeader className="pb-1">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {c.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{c.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Activity Timeline */}
      <ActivityTimeline data={timeline} />

      {/* Two-column: Keywords + Breakdowns */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <KeywordCloud keywords={top_keywords} title="Từ khóa trong session" />
        <div className="space-y-4">
          <IntentBreakdown breakdown={intent_breakdown} />
          <SentimentBreakdown data={sentiment_breakdown} />
        </div>
      </div>

      {/* Engagement Metrics */}
      <div>
        <h3 className="text-lg font-semibold mb-3">Chỉ số tương tác</h3>
        <EngagementMetrics metrics={engagement_metrics} />
      </div>
    </div>
  );
}
