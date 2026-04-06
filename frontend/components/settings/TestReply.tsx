"use client";
import { useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { api, type TestReplyResult } from "@/lib/api";

export function TestReply() {
  const [comment, setComment] = useState("");
  const [result, setResult] = useState<TestReplyResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleTest() {
    if (!comment.trim()) return;
    setLoading(true);
    try {
      const r = await api.settings.testReply(comment.trim());
      setResult(r);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Test failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3 max-w-md">
      <div className="flex gap-2">
        <Input
          placeholder="Enter a test comment…"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleTest()}
        />
        <Button disabled={loading || !comment.trim()} onClick={handleTest}>
          <Send className="mr-2 h-4 w-4" />
          {loading ? "Testing…" : "Test Reply"}
        </Button>
      </div>

      {result && (
        <div className="rounded-md border bg-slate-50 p-4 space-y-2">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Intent:</span>
            <Badge variant="outline">{result.intent}</Badge>
          </div>
          <p className="text-sm font-medium">Bot reply:</p>
          <p className="text-sm text-slate-700 italic">&quot;{result.reply}&quot;</p>
          {result.chunks_used.length > 0 && (
            <p className="text-xs text-muted-foreground">
              Used chunks: {result.chunks_used.join(", ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
