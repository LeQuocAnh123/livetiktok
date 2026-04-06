import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalyticsData } from "@/lib/api";

interface Props {
  data: AnalyticsData;
}

export function StatsCards({ data }: Props) {
  const stats = [
    { label: "Tổng buổi live", value: data.total_sessions },
    { label: "Tổng comment", value: data.total_comments },
    { label: "Đã reply", value: data.total_replies },
    { label: "Tỷ lệ reply", value: `${data.reply_rate}%` },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      {stats.map((s) => (
        <Card key={s.label}>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {s.label}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{s.value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
