import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import type { Session } from "@/lib/api";

interface Props {
  sessions: Session[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

function duration(started: string, ended: string | undefined): string {
  if (!ended) return "Đang live";
  const ms = new Date(ended).getTime() - new Date(started).getTime();
  const mins = Math.floor(ms / 60000);
  return mins < 60 ? `${mins} phút` : `${Math.floor(mins / 60)}h${mins % 60}p`;
}

const STATUS_LABEL: Record<string, string> = {
  active: "Đang live",
  ended: "Đã kết thúc",
  paused: "Tạm dừng",
};

export function SessionList({ sessions, selectedId, onSelect }: Props) {
  if (sessions.length === 0) {
    return <p className="text-sm text-muted-foreground py-8 text-center">Chưa có buổi live nào.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Thời gian bắt đầu</TableHead>
          <TableHead>Thời lượng</TableHead>
          <TableHead>Trạng thái</TableHead>
          <TableHead className="text-right">Chi tiết</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sessions.map((s) => (
          <TableRow key={s.id} className={selectedId === s.id ? "bg-muted/50" : ""}>
            <TableCell>{new Date(s.started_at).toLocaleString("vi-VN")}</TableCell>
            <TableCell>{duration(s.started_at, s.ended_at ?? undefined)}</TableCell>
            <TableCell>
              <Badge variant={s.status === "active" ? "default" : "secondary"}>
                {STATUS_LABEL[s.status] ?? s.status}
              </Badge>
            </TableCell>
            <TableCell className="text-right">
              <Button
                variant={selectedId === s.id ? "default" : "outline"}
                size="sm"
                onClick={() => onSelect(s.id)}
              >
                {selectedId === s.id ? "Đang xem" : "Xem"}
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
