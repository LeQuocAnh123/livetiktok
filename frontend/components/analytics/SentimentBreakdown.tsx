"use client";

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  data: Record<string, number>;
}

const COLORS: Record<string, string> = {
  positive: "#22c55e",
  neutral: "#94a3b8",
  negative: "#ef4444",
};

const LABELS: Record<string, string> = {
  positive: "Tích cực",
  neutral: "Trung lập",
  negative: "Tiêu cực",
};

export function SentimentBreakdown({ data }: Props) {
  const entries = Object.entries(data).filter(([, v]) => v > 0);
  const total = entries.reduce((sum, [, v]) => sum + v, 0);

  if (total === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Phân bố cảm xúc</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Chưa có dữ liệu.</p>
        </CardContent>
      </Card>
    );
  }

  const chartData = entries.map(([name, value]) => ({
    name: LABELS[name] ?? name,
    value,
    color: COLORS[name] ?? "#6b7280",
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Phân bố cảm xúc</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={90}
              dataKey="value"
              nameKey="name"
              label={({ name, percent }: { name?: string; percent?: number }) =>
                `${name ?? ""} ${((percent ?? 0) * 100).toFixed(0)}%`
              }
              labelLine={false}
            >
              {chartData.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
        <p className="text-center text-sm text-muted-foreground mt-1">
          Tổng: {total} comments
        </p>
      </CardContent>
    </Card>
  );
}
