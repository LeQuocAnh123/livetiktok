"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { StatsCards } from "@/components/analytics/StatsCards";
import { IntentBreakdown } from "@/components/analytics/IntentBreakdown";
import { UnansweredSummary } from "@/components/analytics/UnansweredSummary";
import { DateRangeFilter } from "@/components/analytics/DateRangeFilter";
import { GiftStatsSection } from "@/components/analytics/GiftStats";
import { SentimentTrend } from "@/components/analytics/SentimentTrend";
import { KeywordCloud } from "@/components/analytics/KeywordCloud";
import { SessionList } from "@/components/analytics/SessionList";
import { api, type AnalyticsData } from "@/lib/api";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  function load() {
    setError(false);
    setLoading(true);
    api.analytics
      .get({
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      })
      .then(setData)
      .catch(() => {
        setData(null);
        setError(true);
        toast.error("Failed to load analytics");
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Analytics</h2>
          <p className="text-sm text-muted-foreground">
            Live session statistics
            {startDate && endDate
              ? ` from ${startDate} to ${endDate}`
              : " (all time)"}
          </p>
        </div>
      </div>

      <DateRangeFilter
        startDate={startDate}
        endDate={endDate}
        onStartChange={setStartDate}
        onEndChange={setEndDate}
        onApply={load}
        loading={loading}
      />

      {error && (
        <div className="space-y-2">
          <p className="text-sm text-destructive">Failed to load data.</p>
          <button
            onClick={load}
            className="text-sm underline"
          >
            Retry
          </button>
        </div>
      )}

      {loading && !data && (
        <p className="text-sm text-muted-foreground">Loading...</p>
      )}

      {data && (
        <div className="space-y-6">
          <StatsCards data={data} />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <IntentBreakdown breakdown={data.intent_breakdown} />
            <UnansweredSummary count={data.unanswered_count} />
          </div>
          {data.gift_stats && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Gift & Revenue</h3>
              <GiftStatsSection stats={data.gift_stats} />
            </div>
          )}

          {/* Deep Analytics sections */}
          <SentimentTrend data={data.sentiment_trend} />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <KeywordCloud keywords={data.top_keywords_overall} />
            <div /> {/* Placeholder for visual balance */}
          </div>
          <SessionList sessions={data.session_list} />
        </div>
      )}
    </div>
  );
}
