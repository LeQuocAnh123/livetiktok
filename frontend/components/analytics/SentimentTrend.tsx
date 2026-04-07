"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SentimentTrendEntry } from "@/lib/api";

interface Props {
  data: SentimentTrendEntry[];
}

export function SentimentTrend({ data }: Props) {
  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Xu hướng cảm xúc</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Chưa có dữ liệu.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Xu hướng cảm xúc</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Area
              type="monotone"
              dataKey="positive"
              name="Tích cực"
              stackId="1"
              stroke="#22c55e"
              fill="#22c55e"
              fillOpacity={0.6}
            />
            <Area
              type="monotone"
              dataKey="neutral"
              name="Trung lập"
              stackId="1"
              stroke="#94a3b8"
              fill="#94a3b8"
              fillOpacity={0.6}
            />
            <Area
              type="monotone"
              dataKey="negative"
              name="Tiêu cực"
              stackId="1"
              stroke="#ef4444"
              fill="#ef4444"
              fillOpacity={0.6}
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
