import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { EngagementMetrics as EngagementMetricsType } from "@/lib/api";

interface Props {
  metrics: EngagementMetricsType;
}

function formatPeakMinute(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

export function EngagementMetrics({ metrics }: Props) {
  const cards = [
    {
      label: "Tỷ lệ hỏi sản phẩm",
      value: `${metrics.product_inquiry_rate}%`,
      description: "Proxy conversion rate",
    },
    {
      label: "Người bình luận",
      value: metrics.unique_commenters,
      description: "Unique commenters",
    },
    {
      label: "Comments/phút",
      value: metrics.comments_per_minute_avg,
      description: "Trung bình",
    },
    {
      label: "Phút cao điểm",
      value: metrics.peak_minute
        ? `${formatPeakMinute(metrics.peak_minute)} (${metrics.peak_comments})`
        : "—",
      description: "Thời điểm + số comments",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      {cards.map((c) => (
        <Card key={c.label}>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {c.label}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{c.value}</p>
            <p className="text-xs text-muted-foreground">{c.description}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
