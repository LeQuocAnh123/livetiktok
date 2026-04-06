"use client";
import { useRef, useState } from "react";
import { Download, Upload, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function BackupRestore() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [downloading, setDownloading] = useState(false);
  const [restoreFile, setRestoreFile] = useState<File | null>(null);
  const [restoring, setRestoring] = useState(false);

  async function handleDownload() {
    setDownloading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/backup/download`);
      if (!res.ok) throw new Error("Download thất bại");
      const blob = await res.blob();
      const disposition = res.headers.get("content-disposition") ?? "";
      const match = disposition.match(/filename="?([^"]+)"?/);
      const filename = match?.[1] ?? "backup.db";
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Đã tải backup về máy");
    } catch {
      toast.error("Không thể tải backup");
    } finally {
      setDownloading(false);
    }
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (inputRef.current) inputRef.current.value = "";
    if (file) setRestoreFile(file);
  }

  async function handleRestore() {
    if (!restoreFile) return;
    setRestoring(true);
    try {
      const form = new FormData();
      form.append("file", restoreFile);
      const res = await fetch(`${API_URL}/api/v1/backup/restore`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? "Restore thất bại");
      }
      toast.success("Restore thành công! Hãy restart server để áp dụng.");
      setRestoreFile(null);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Restore thất bại");
    } finally {
      setRestoring(false);
    }
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept=".db"
        className="hidden"
        onChange={handleFileSelect}
        aria-hidden="true"
        tabIndex={-1}
      />

      <div className="flex gap-3">
        <Button variant="outline" disabled={downloading} onClick={handleDownload}>
          <Download className="h-4 w-4 mr-2" />
          {downloading ? "Đang tải…" : "Tải backup (.db)"}
        </Button>

        <Button variant="outline" onClick={() => inputRef.current?.click()}>
          <Upload className="h-4 w-4 mr-2" />
          Restore từ file
        </Button>
      </div>

      {/* Confirm restore dialog */}
      <Dialog open={!!restoreFile} onOpenChange={() => setRestoreFile(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Xác nhận Restore
            </DialogTitle>
            <DialogDescription>
              File <strong>{restoreFile?.name}</strong> sẽ thay thế toàn bộ database hiện tại.
              Dữ liệu hiện tại sẽ được backup tự động trước khi ghi đè.
              <br /><br />
              Sau khi restore, hãy <strong>restart server</strong> để kết nối lại database.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRestoreFile(null)} disabled={restoring}>Huỷ</Button>
            <Button variant="destructive" onClick={handleRestore} disabled={restoring}>
              {restoring ? "Đang restore…" : "Xác nhận Restore"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
