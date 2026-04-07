"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { KeywordEntry } from "@/lib/api";

interface Props {
  keywords: KeywordEntry[];
  title?: string;
}

export function KeywordCloud({ keywords, title = "Từ khóa nổi bật" }: Props) {
  if (keywords.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Chưa có dữ liệu.</p>
        </CardContent>
      </Card>
    );
  }

  // Take top 15, sorted descending by count
  const chartData = keywords.slice(0, 15).reverse();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={Math.max(200, chartData.length * 28)}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 60 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" tick={{ fontSize: 12 }} />
            <YAxis
              type="category"
              dataKey="word"
              tick={{ fontSize: 12 }}
              width={55}
            />
            <Tooltip />
            <Bar dataKey="count" name="Số lần" fill="#3b82f6" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
