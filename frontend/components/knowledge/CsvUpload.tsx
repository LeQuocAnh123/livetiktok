"use client";
import { useRef, useState } from "react";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { api } from "@/lib/api";

interface Props {
  onDone: () => void;
}

export function CsvUpload({ onDone }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    const validCsv = file.name.endsWith(".csv") || file.type === "text/csv" || file.type === "application/csv";
    if (!validCsv) {
      toast.error("Only CSV files are supported");
      return;
    }

    setUploading(true);
    try {
      const result = await api.knowledge.upload(file);
      toast.success(`Imported ${result.created} chunks (${result.skipped} skipped)`);
      onDone();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
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
        disabled={uploading}
        onClick={() => inputRef.current?.click()}
      >
        <Upload className="mr-2 h-4 w-4" />
        {uploading ? "Uploading…" : "Upload CSV"}
      </Button>
    </>
  );
}
