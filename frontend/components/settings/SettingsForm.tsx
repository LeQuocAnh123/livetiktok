"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type BotSettings } from "@/lib/api";

export function SettingsForm() {
  const [settings, setSettings] = useState<BotSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);

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
        <Label htmlFor="tone">Tone</Label>
        <Input
          id="tone"
          value={settings.tone}
          onChange={(e) => update("tone", e.target.value)}
          placeholder="friendly, professional, casual…"
        />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="blacklist">Blacklist Keywords (comma-separated)</Label>
        <Input
          id="blacklist"
          value={settings.blacklist_keywords.join(", ")}
          onChange={(e) =>
            update("blacklist_keywords", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))
          }
        />
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
