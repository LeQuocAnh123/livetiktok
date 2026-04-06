"use client";
import { useRef, useState } from "react";
import { Upload, AlertTriangle, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { api, type CsvPreview, type UploadResult } from "@/lib/api";

interface Props {
  onDone: () => void;
}

export function CsvUpload({ onDone }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<CsvPreview | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (inputRef.current) inputRef.current.value = "";

    setLoading(true);
    try {
      const data = await api.knowledge.preview(file);
      setPreview(data);
      setPendingFile(file);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Không đọc được file CSV");
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm() {
    if (!pendingFile) return;
    setLoading(true);
    try {
      const data = await api.knowledge.upload(pendingFile);
      setPreview(null);
      setPendingFile(null);
      setResult(data);
      onDone();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Import thất bại");
    } finally {
      setLoading(false);
    }
  }

  function handleCancel() {
    setPreview(null);
    setPendingFile(null);
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={handleFile}
        aria-hidden="true"
        tabIndex={-1}
      />
      <Button
        variant="outline"
        disabled={loading}
        onClick={() => inputRef.current?.click()}
      >
        <Upload className="mr-2 h-4 w-4" />
        {loading ? "Đang đọc…" : "Upload CSV"}
      </Button>

      {/* Preview modal */}
      <Dialog open={!!preview} onOpenChange={handleCancel}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Xác nhận import CSV</DialogTitle>
            <DialogDescription>
              Kiểm tra dữ liệu trước khi import vào Knowledge Base.
            </DialogDescription>
          </DialogHeader>

          {preview && (
            <div className="space-y-4">
              {/* Summary */}
              <div className="flex gap-4 text-sm">
                <span className="text-muted-foreground">Tổng dòng: <strong>{preview.total_rows}</strong></span>
                <span className="text-green-600">Hợp lệ: <strong>{preview.valid_rows}</strong></span>
                {preview.total_rows - preview.valid_rows > 0 && (
                  <span className="text-destructive">Bỏ qua: <strong>{preview.total_rows - preview.valid_rows}</strong></span>
                )}
              </div>

              {/* Warnings */}
              {preview.warnings.length > 0 && (
                <div className="rounded-md bg-yellow-50 border border-yellow-200 p-3 space-y-1">
                  {preview.warnings.map((w, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm text-yellow-800">
                      <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                      {w}
                    </div>
                  ))}
                </div>
              )}

              {/* Preview rows */}
              <div>
                <p className="text-xs text-muted-foreground mb-2">Preview 5 dòng đầu:</p>
                <div className="space-y-2">
                  {preview.preview.map((row) => (
                    <div
                      key={row.row}
                      className={`rounded-md border p-2 text-sm ${row.is_valid ? "bg-white" : "bg-red-50 border-red-200"}`}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="text-xs text-muted-foreground">Dòng {row.row}</span>
                        <div className="flex items-center gap-1">
                          <Badge variant="outline" className="text-xs">{row.category}</Badge>
                          {row.warning && (
                            <span className="text-xs text-yellow-700">{row.warning}</span>
                          )}
                          {!row.is_valid && (
                            <span className="text-xs text-destructive font-medium">Bỏ qua</span>
                          )}
                        </div>
                      </div>
                      <p className={row.is_valid ? "text-slate-700" : "text-slate-400 line-through"}>
                        {row.content || "(trống)"}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={handleCancel} disabled={loading}>Huỷ</Button>
            <Button onClick={handleConfirm} disabled={loading || (preview?.valid_rows === 0)}>
              {loading ? "Đang import…" : `Import ${preview?.valid_rows ?? 0} chunks`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Result modal */}
      <Dialog open={!!result} onOpenChange={() => setResult(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              Import hoàn tất
            </DialogTitle>
          </DialogHeader>

          {result && (
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="rounded-md bg-green-50 border border-green-200 p-3">
                  <p className="text-2xl font-bold text-green-700">{result.created}</p>
                  <p className="text-green-600">Đã tạo</p>
                </div>
                <div className="rounded-md bg-slate-50 border p-3">
                  <p className="text-2xl font-bold text-slate-500">{result.skipped}</p>
                  <p className="text-slate-500">Bỏ qua</p>
                </div>
                <div className="rounded-md bg-yellow-50 border border-yellow-200 p-3">
                  <p className="text-2xl font-bold text-yellow-700">{result.errors.length}</p>
                  <p className="text-yellow-600">Cảnh báo</p>
                </div>
              </div>
              {result.errors.length > 0 && (
                <div className="rounded-md bg-yellow-50 border border-yellow-200 p-3 space-y-1 max-h-32 overflow-y-auto">
                  {result.errors.map((e, i) => (
                    <p key={i} className="text-xs text-yellow-800">{e}</p>
                  ))}
                </div>
              )}
              <p className="text-xs text-muted-foreground">
                Các chunks đang được embedding trong nền, trạng thái sẽ cập nhật sau.
              </p>
            </div>
          )}

          <DialogFooter>
            <Button onClick={() => setResult(null)}>Đóng</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
