"use client";
import { useCallback, useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ChunkTable } from "@/components/knowledge/ChunkTable";
import { ChunkDialog } from "@/components/knowledge/ChunkDialog";
import { CsvUpload } from "@/components/knowledge/CsvUpload";
import { api, type KnowledgeChunk, type KnowledgeCategory } from "@/lib/api";

export default function KnowledgePage() {
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editChunk, setEditChunk] = useState<KnowledgeChunk | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.knowledge.list({ page, limit: 20 });
      setChunks(data.items);
      setTotal(data.total);
    } catch {
      toast.error("Failed to load knowledge base");
    }
  }, [page]);

  useEffect(() => { load(); }, [load]);

  function openCreate() {
    setEditChunk(null);
    setDialogOpen(true);
  }

  function openEdit(chunk: KnowledgeChunk) {
    setEditChunk(chunk);
    setDialogOpen(true);
  }

  async function handleSave(data: { content: string; category: KnowledgeCategory; metadata: Record<string, unknown> }) {
    try {
      if (editChunk) {
        await api.knowledge.update(editChunk.id, data);
        toast.success("Chunk updated");
      } else {
        await api.knowledge.create(data);
        toast.success("Chunk created");
      }
      await load();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Save failed");
      throw err;
    }
  }

  async function handleDelete(id: string) {
    try {
      await api.knowledge.delete(id);
      toast.success("Chunk deleted");
      await load();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Delete failed");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Knowledge Base</h2>
          <p className="text-sm text-muted-foreground">{total} chunks total</p>
        </div>
        <div className="flex gap-2">
          <CsvUpload onDone={load} />
          <Button onClick={openCreate}>
            <Plus className="mr-2 h-4 w-4" />
            Add Chunk
          </Button>
        </div>
      </div>

      <ChunkTable chunks={chunks} onEdit={openEdit} onDelete={handleDelete} />

      {total > 20 && (
        <div className="flex justify-center gap-2">
          <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <span className="py-1 text-sm">Page {page} of {Math.ceil(total / 20)}</span>
          <Button variant="outline" size="sm" disabled={page * 20 >= total} onClick={() => setPage((p) => p + 1)}>
            Next
          </Button>
        </div>
      )}

      <ChunkDialog
        open={dialogOpen}
        chunk={editChunk}
        onClose={() => setDialogOpen(false)}
        onSave={handleSave}
      />
    </div>
  );
}
