"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { StatsCards } from "@/components/analytics/StatsCards";
import { IntentBreakdown } from "@/components/analytics/IntentBreakdown";
import { UnansweredSummary } from "@/components/analytics/UnansweredSummary";
import { api, type AnalyticsData } from "@/lib/api";
import { Button } from "@/components/ui/button";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  function load() {
    setError(false);
    setLoading(true);
    api.analytics
      .get()
      .then(setData)
      .catch(() => {
        setError(true);
        toast.error("Không tải được thống kê");
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Analytics</h2>
          <p className="text-sm text-muted-foreground">
            Thống kê toàn bộ buổi live
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          {loading ? "Đang tải…" : "Làm mới"}
        </Button>
      </div>

      {error && (
        <div className="space-y-2">
          <p className="text-sm text-destructive">Không tải được dữ liệu.</p>
          <Button variant="outline" size="sm" onClick={load}>
            Thử lại
          </Button>
        </div>
      )}

      {loading && !data && (
        <p className="text-sm text-muted-foreground">Đang tải…</p>
      )}

      {data && (
        <div className="space-y-6">
          <StatsCards data={data} />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <IntentBreakdown breakdown={data.intent_breakdown} />
            <UnansweredSummary count={data.unanswered_count} />
          </div>
        </div>
      )}
    </div>
  );
}
