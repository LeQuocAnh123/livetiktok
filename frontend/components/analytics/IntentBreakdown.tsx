import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const INTENT_LABELS: Record<string, string> = {
  product_inquiry: "Hỏi sản phẩm",
  greeting: "Chào hỏi",
  unknown: "Không xác định",
  skipped: "Bỏ qua",
  blacklist: "Từ cấm",
};

interface Props {
  breakdown: Record<string, number>;
}

export function IntentBreakdown({ breakdown }: Props) {
  const entries = Object.entries(breakdown).sort((a, b) => b[1] - a[1]);
  const max = entries[0]?.[1] ?? 1;

  if (entries.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Phân loại intent</CardTitle>
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
        <CardTitle className="text-base">Phân loại intent</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {entries.map(([intent, count]) => (
          <div key={intent} className="space-y-1">
            <div className="flex justify-between text-sm">
              <span>{INTENT_LABELS[intent] ?? intent}</span>
              <span className="font-medium">{count}</span>
            </div>
            <div className="h-2 rounded-full bg-slate-100">
              <div
                className="h-2 rounded-full bg-primary transition-all"
                style={{ width: `${Math.round((count / max) * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
