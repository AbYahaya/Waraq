/**
 * Chunked PDF upload dialog.
 *
 * Walks the canonical 3-step flow exposed by `/uploads/*`:
 *   1. POST /uploads  → returns job_uuid (PENDING)
 *   2. POST /uploads/{job_uuid}/chunks/{n} for each chunk (multipart)
 *   3. POST /uploads/{job_uuid}/finalize → materializes Page rows + SCAN-POs
 *
 * On success we invalidate the project's pages query so the workspace
 * picks the new pages up immediately.
 */

import { useState, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ApiError, api } from "@/lib/api";
import { qk } from "@/lib/queries";
import { useAuthStore } from "@/store/auth";

const CHUNK_SIZE = 256 * 1024; // 256 KB — bounded memory per upload

interface UploadStartResponse {
  job_uuid: string;
  state: string;
  expected_next_chunk: number;
}

interface UploadFinalizeResponse {
  job_uuid: string;
  state: string;
  page_count: number;
  page_uuids: string[];
  source_sha256: string;
}

export interface UploadPdfDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectUuid: string;
}

export function UploadPdfDialog({
  open,
  onOpenChange,
  projectUuid,
}: UploadPdfDialogProps): JSX.Element {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<{ sent: number; total: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadFinalizeResponse | null>(null);

  const reset = (): void => {
    setFile(null);
    setProgress(null);
    setError(null);
    setResult(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  const uploadMutation = useMutation({
    mutationFn: async (file: File): Promise<UploadFinalizeResponse> => {
      const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
      // 1. Start.
      const start = await api.post<UploadStartResponse>("/uploads", {
        project_uuid: projectUuid,
        original_filename: file.name,
        total_chunks: totalChunks,
        total_size_bytes: file.size,
      });
      // 2. Append chunks. Use raw fetch with multipart so the bearer
      //    auto-attaches via the same store the api client uses.
      const token = useAuthStore.getState().token;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      for (let i = 0; i < totalChunks; i++) {
        const offset = i * CHUNK_SIZE;
        const slice = file.slice(offset, offset + CHUNK_SIZE);
        const fd = new FormData();
        fd.append("chunk", slice, "chunk");
        const resp = await fetch(`/uploads/${start.job_uuid}/chunks/${i}`, {
          method: "POST",
          headers,
          body: fd,
        });
        if (!resp.ok) {
          const text = await resp.text();
          throw new ApiError(resp.status, text || resp.statusText, text);
        }
        setProgress({ sent: i + 1, total: totalChunks });
      }
      // 3. Finalize.
      return api.post<UploadFinalizeResponse>(`/uploads/${start.job_uuid}/finalize`);
    },
    onSuccess: (r) => {
      setResult(r);
      void qc.invalidateQueries({ queryKey: qk.projectPages(projectUuid) });
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Upload failed"),
  });

  const onSubmit = (): void => {
    if (!file) return;
    setError(null);
    setResult(null);
    setProgress({ sent: 0, total: 1 });
    uploadMutation.mutate(file);
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) reset();
        onOpenChange(o);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload PDF</DialogTitle>
          <DialogDescription>
            The source PDF is uploaded in 256 KB chunks. Pages and SCAN-POs
            are materialized on finalize via the canonical upload flow.
          </DialogDescription>
        </DialogHeader>

        <input
          ref={fileRef}
          type="file"
          accept="application/pdf,.pdf"
          onChange={(e) => {
            const f = e.target.files?.[0] ?? null;
            setFile(f);
            setProgress(null);
            setResult(null);
            setError(null);
          }}
          className="text-sm file:mr-3 file:rounded file:border file:bg-background file:px-3 file:py-1.5 file:text-sm hover:file:bg-accent"
        />

        {file && (
          <p className="text-xs text-muted-foreground">
            {file.name} — {(file.size / 1024 / 1024).toFixed(2)} MB,{" "}
            {Math.ceil(file.size / CHUNK_SIZE)} chunks
          </p>
        )}

        {progress && (
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">
              Sending chunk {progress.sent} / {progress.total}
            </div>
            <div className="h-1 rounded bg-muted overflow-hidden">
              <div
                className="h-1 bg-primary transition-all"
                style={{
                  width: `${(progress.sent / Math.max(progress.total, 1)) * 100}%`,
                }}
              />
            </div>
          </div>
        )}

        {error && <p className="text-sm text-destructive">{error}</p>}

        {result && (
          <div className="rounded border border-emerald-200 bg-emerald-50 p-3 text-sm">
            <p className="font-medium text-emerald-800">
              Finalized — {result.page_count} pages materialized.
            </p>
            <p className="text-xs text-emerald-700 mt-1 truncate">
              sha256: {result.source_sha256.slice(0, 16)}…
            </p>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button
            onClick={onSubmit}
            disabled={!file || uploadMutation.isPending}
          >
            {uploadMutation.isPending ? "Uploading…" : "Upload"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
