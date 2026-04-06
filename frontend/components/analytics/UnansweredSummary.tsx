import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Props {
  count: number;
}

export function UnansweredSummary({ count }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Comment chưa được trả lời</CardTitle>
      </CardHeader>
      <CardContent className="flex items-center gap-3">
        <span className="text-4xl font-bold text-destructive">{count}</span>
        {count > 0 ? (
          <Badge variant="destructive">Cần bổ sung Knowledge Base</Badge>
        ) : (
          <Badge variant="outline" className="text-green-600 border-green-400">
            Tất cả đã được xử lý
          </Badge>
        )}
      </CardContent>
    </Card>
  );
}
