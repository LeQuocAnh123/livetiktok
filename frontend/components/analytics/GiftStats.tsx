import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GiftStats as GiftStatsType } from "@/lib/api";
import { Diamond, DollarSign } from "lucide-react";

interface Props {
  stats: GiftStatsType;
}

export function GiftStatsSection({ stats }: Props) {
  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Tổng gifts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{stats.total_gifts}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="flex items-center gap-1 text-sm font-medium text-muted-foreground">
              <Diamond className="h-4 w-4" /> Tổng diamonds
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{stats.total_diamonds.toLocaleString()}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="flex items-center gap-1 text-sm font-medium text-muted-foreground">
              <DollarSign className="h-4 w-4" /> Doanh thu ước tính
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">${stats.estimated_usd.toFixed(2)}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Top Gifters */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top Gifters</CardTitle>
          </CardHeader>
          <CardContent>
            {stats.top_gifters.length === 0 ? (
              <p className="text-sm text-muted-foreground">Chưa có dữ liệu.</p>
            ) : (
              <div className="space-y-2">
                {stats.top_gifters.map((gifter, i) => (
                  <div key={gifter.user} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-muted-foreground w-5">{i + 1}.</span>
                      <span className="font-medium">{gifter.user}</span>
                    </div>
                    <div className="flex items-center gap-3 text-muted-foreground">
                      <span>{gifter.gift_count} gifts</span>
                      <span className="font-semibold text-foreground">
                        {gifter.total_diamonds.toLocaleString()} <Diamond className="inline h-3 w-3" />
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Gift Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Loại gift</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {stats.gift_breakdown.length === 0 ? (
              <p className="text-sm text-muted-foreground">Chưa có dữ liệu.</p>
            ) : (
              stats.gift_breakdown.map((g) => {
                const max = stats.gift_breakdown[0]?.total_diamonds ?? 1;
                return (
                  <div key={g.gift_name} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span>{g.gift_name} ({g.count}x)</span>
                      <span className="font-medium">{g.total_diamonds.toLocaleString()} <Diamond className="inline h-3 w-3" /></span>
                    </div>
                    <div className="h-2 rounded-full bg-amber-100">
                      <div
                        className="h-2 rounded-full bg-amber-500 transition-all"
                        style={{ width: `${Math.round((g.total_diamonds / max) * 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
