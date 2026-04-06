"use client";
import { useState } from "react";
import { Pause, Play, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { wsClient } from "@/lib/ws";

interface Props {
  paused: boolean;
  connected: boolean;
  replyTargetId: string | null;
}

export function BotControls({ paused, connected, replyTargetId }: Props) {
  const [manualText, setManualText] = useState("");

  function togglePause() {
    wsClient.send({ type: paused ? "resume_bot" : "pause_bot" });
  }

  function sendManualReply() {
    if (!manualText.trim() || !replyTargetId) return;
    wsClient.send({ type: "manual_reply", message_id: replyTargetId, content: manualText.trim() });
    setManualText("");
  }

  return (
    <div className="flex flex-col gap-3">
      <Button
        variant={paused ? "default" : "outline"}
        size="sm"
        disabled={!connected}
        onClick={togglePause}
      >
        {paused ? <Play className="mr-2 h-4 w-4" /> : <Pause className="mr-2 h-4 w-4" />}
        {paused ? "Resume Bot" : "Pause Bot"}
      </Button>

      <div className="flex gap-2">
        <Input
          placeholder={replyTargetId ? "Type manual reply…" : "Select a comment first"}
          value={manualText}
          disabled={!connected || !replyTargetId}
          onChange={(e) => setManualText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendManualReply()}
        />
        <Button
          size="icon"
          disabled={!connected || !replyTargetId || !manualText.trim()}
          onClick={sendManualReply}
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
