"use client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface DateRangeFilterProps {
  startDate: string;
  endDate: string;
  onStartChange: (date: string) => void;
  onEndChange: (date: string) => void;
  onApply: () => void;
  loading: boolean;
}

export function DateRangeFilter({
  startDate,
  endDate,
  onStartChange,
  onEndChange,
  onApply,
  loading,
}: DateRangeFilterProps) {
  // Quick presets
  const setPreset = (days: number | null) => {
    if (days === null) {
      onStartChange("");
      onEndChange("");
    } else {
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - days + 1);
      onStartChange(start.toISOString().split("T")[0]);
      onEndChange(end.toISOString().split("T")[0]);
    }
  };

  return (
    <div className="flex flex-wrap items-end gap-4">
      <div className="space-y-1">
        <Label htmlFor="start-date" className="text-xs">
          From
        </Label>
        <Input
          id="start-date"
          type="date"
          value={startDate}
          onChange={(e) => onStartChange(e.target.value)}
          className="w-36"
        />
      </div>

      <div className="space-y-1">
        <Label htmlFor="end-date" className="text-xs">
          To
        </Label>
        <Input
          id="end-date"
          type="date"
          value={endDate}
          onChange={(e) => onEndChange(e.target.value)}
          className="w-36"
        />
      </div>

      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPreset(1)}
          className="text-xs"
        >
          Today
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPreset(7)}
          className="text-xs"
        >
          7 days
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPreset(30)}
          className="text-xs"
        >
          30 days
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPreset(null)}
          className="text-xs"
        >
          All time
        </Button>
      </div>

      <Button size="sm" onClick={onApply} disabled={loading}>
        {loading ? "Loading..." : "Apply"}
      </Button>
    </div>
  );
}
