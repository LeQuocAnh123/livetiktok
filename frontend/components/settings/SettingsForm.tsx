"use client";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, type BotSettings } from "@/lib/api";

const TONES = [
  { value: "friendly", label: "Thân thiện" },
  { value: "professional", label: "Chuyên nghiệp" },
  { value: "casual", label: "Tự nhiên, bình thường" },
  { value: "enthusiastic", label: "Nhiệt tình, năng động" },
  { value: "formal", label: "Lịch sự, trang trọng" },
];

export function SettingsForm() {
  const [settings, setSettings] = useState<BotSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);
  const [keywordInput, setKeywordInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function loadSettings() {
    setError(false);
    setSettings(null);
    api.settings
      .get()
      .then((s) => {
        setSettings(s);
        setError(false);
      })
      .catch(() => {
        setError(true);
        toast.error("Failed to load settings");
      });
  }

  useEffect(() => {
    loadSettings();
  }, []);

  if (error)
    return (
      <div className="space-y-2">
        <p className="text-sm text-destructive">Failed to load settings.</p>
        <Button variant="outline" size="sm" onClick={loadSettings}>
          Retry
        </Button>
      </div>
    );
  if (!settings) return <p className="text-sm text-muted-foreground">Loading…</p>;

  function update<K extends keyof BotSettings>(key: K, value: BotSettings[K]) {
    setSettings((s) => (s ? { ...s, [key]: value } : s));
  }

  function addKeyword() {
    const word = keywordInput.trim();
    if (!word) return;
    const words = word.split(/[,\n]+/).map((w) => w.trim()).filter(Boolean);
    const existing = settings!.blacklist_keywords;
    const toAdd = words.filter((w) => !existing.includes(w));
    if (toAdd.length > 0) {
      update("blacklist_keywords", [...existing, ...toAdd]);
    }
    setKeywordInput("");
    inputRef.current?.focus();
  }

  function removeKeyword(kw: string) {
    update(
      "blacklist_keywords",
      settings!.blacklist_keywords.filter((k) => k !== kw),
    );
  }

  function handleKeywordKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addKeyword();
    } else if (e.key === "Backspace" && keywordInput === "" && settings!.blacklist_keywords.length > 0) {
      const kws = settings!.blacklist_keywords;
      update("blacklist_keywords", kws.slice(0, -1));
    }
  }

  async function handleSave() {
    if (!settings) return;
    setSaving(true);
    try {
      const updated = await api.settings.update(settings);
      setSettings(updated);
      toast.success("Settings saved");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6 max-w-md">
      <div className="grid gap-2">
        <Label>Tone</Label>
        <Select value={settings.tone} onValueChange={(v) => update("tone", v)}>
          <SelectTrigger>
            <SelectValue placeholder="Chọn tone…" />
          </SelectTrigger>
          <SelectContent>
            {TONES.map((t) => (
              <SelectItem key={t.value} value={t.value}>
                {t.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-2">
        <Label>Từ khoá bị chặn</Label>
        <div
          className="flex flex-wrap gap-1.5 min-h-[42px] w-full rounded-md border border-input bg-background px-3 py-2 cursor-text"
          onClick={() => inputRef.current?.focus()}
        >
          {settings.blacklist_keywords.map((kw) => (
            <span
              key={kw}
              className="inline-flex items-center gap-1 rounded bg-destructive/10 text-destructive px-2 py-0.5 text-xs font-medium"
            >
              {kw}
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); removeKeyword(kw); }}
                className="hover:text-destructive/70"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
          <Input
            ref={inputRef}
            className="border-0 p-0 h-auto flex-1 min-w-[120px] shadow-none focus-visible:ring-0 text-sm"
            placeholder={settings.blacklist_keywords.length === 0 ? "Nhập từ khoá, Enter để thêm…" : ""}
            value={keywordInput}
            onChange={(e) => setKeywordInput(e.target.value)}
            onKeyDown={handleKeywordKeyDown}
            onBlur={addKeyword}
          />
        </div>
        <p className="text-xs text-muted-foreground">Nhấn Enter hoặc dấu phẩy để thêm. Backspace để xoá từ cuối.</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="grid gap-2">
          <Label htmlFor="delay-min">Reply Delay Min (s)</Label>
          <Input
            id="delay-min"
            type="number"
            min={0}
            value={settings.reply_delay_min}
            onChange={(e) => update("reply_delay_min", Number(e.target.value))}
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="delay-max">Reply Delay Max (s)</Label>
          <Input
            id="delay-max"
            type="number"
            min={0}
            value={settings.reply_delay_max}
            onChange={(e) => update("reply_delay_max", Number(e.target.value))}
          />
        </div>
      </div>

      <div className="grid gap-2">
        <Label htmlFor="cooldown">User Cooldown (s)</Label>
        <Input
          id="cooldown"
          type="number"
          min={0}
          value={settings.user_cooldown_seconds}
          onChange={(e) => update("user_cooldown_seconds", Number(e.target.value))}
        />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="max-replies">Max Replies per Session</Label>
        <Input
          id="max-replies"
          type="number"
          min={1}
          value={settings.max_replies_per_session}
          onChange={(e) => update("max_replies_per_session", Number(e.target.value))}
        />
      </div>

      <div className="flex items-center gap-3">
        <Checkbox
          id="auto-reply"
          checked={settings.auto_reply_enabled}
          onCheckedChange={(checked) => update("auto_reply_enabled", checked === true)}
        />
        <Label htmlFor="auto-reply">Auto Reply</Label>
      </div>

      <Button disabled={saving} onClick={handleSave}>
        {saving ? "Saving…" : "Save Settings"}
      </Button>
    </div>
  );
}
