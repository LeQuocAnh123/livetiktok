"use client";

import {
  ComposedChart,
  Area,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TimelineBucket } from "@/lib/api";

interface Props {
  data: TimelineBucket[];
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

export function ActivityTimeline({ data }: Props) {
  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Timeline hoạt động</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Chưa có dữ liệu.</p>
        </CardContent>
      </Card>
    );
  }

  const chartData = data.map((b) => ({
    ...b,
    time: formatTime(b.bucket_start),
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Timeline hoạt động</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={350}>
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" tick={{ fontSize: 12 }} />
            <YAxis
              yAxisId="left"
              tick={{ fontSize: 12 }}
              label={{ value: "Comments", angle: -90, position: "insideLeft", fontSize: 11 }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fontSize: 12 }}
              label={{ value: "Diamonds", angle: 90, position: "insideRight", fontSize: 11 }}
            />
            <Tooltip />
            <Legend />
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="comment_count"
              name="Comments"
              stroke="#3b82f6"
              fill="#3b82f6"
              fillOpacity={0.3}
            />
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="reply_count"
              name="Replies"
              stroke="#22c55e"
              fill="#22c55e"
              fillOpacity={0.2}
            />
            <Bar
              yAxisId="right"
              dataKey="gift_diamonds"
              name="Diamonds"
              fill="#f59e0b"
              opacity={0.8}
              radius={[2, 2, 0, 0]}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
