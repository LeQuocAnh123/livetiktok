"use client";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import type { KnowledgeChunk, KnowledgeCategory } from "@/lib/api";

interface Props {
  open: boolean;
  chunk?: KnowledgeChunk | null;
  onClose: () => void;
  onSave: (data: { content: string; category: KnowledgeCategory; metadata: Record<string, unknown> }) => Promise<void>;
}

export function ChunkDialog({ open, chunk, onClose, onSave }: Props) {
  const [content, setContent] = useState("");
  const [category, setCategory] = useState<KnowledgeCategory>("faq");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (chunk) {
      setContent(chunk.content);
      setCategory(chunk.category);
    } else {
      setContent("");
      setCategory("faq");
    }
  }, [chunk, open]);

  async function handleSave() {
    if (!content.trim()) return;
    setSaving(true);
    try {
      await onSave({ content: content.trim(), category, metadata: chunk?.metadata ?? {} });
      onClose();
    } catch {
      // error already toasted by parent; just unblock the button
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{chunk ? "Edit Chunk" : "Add Chunk"}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <div className="grid gap-2">
            <Label htmlFor="content">Content</Label>
            <Textarea
              id="content"
              rows={10}
              placeholder="Describe a product, policy, or FAQ answer…"
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="category">Category</Label>
            <Select value={category} onValueChange={(v) => setCategory(v as KnowledgeCategory)}>
              <SelectTrigger id="category">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="product">Product</SelectItem>
                <SelectItem value="policy">Policy</SelectItem>
                <SelectItem value="faq">FAQ</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button disabled={saving || !content.trim()} onClick={handleSave}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
