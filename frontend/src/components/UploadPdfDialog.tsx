/**
 * Chunked upload dialog — Phase 5 K-1 accepts PDFs AND image formats
 * (JPG / JPEG / PNG / TIFF / TIF / HEIC / HEIF / WEBP) per canon §2.1.
 *
 * Walks the canonical 3-step flow exposed by `/uploads/*`:
 *   1. POST /uploads  → returns job_uuid (PENDING)
 *   2. POST /uploads/{job_uuid}/chunks/{n} for each chunk (multipart)
 *   3. POST /uploads/{job_uuid}/finalize → materializes Page rows + SCAN-POs
 *
 * The chunked transport itself is format-agnostic. The backend
 * `finalize` step sniffs the file's magic bytes + extension and
 * branches: PDF → pdftoppm; image → PIL re-encode at OCR time.
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
import { ApiError, api, apiPath } from "@/lib/api";
import { qk } from "@/lib/queries";
import { useAuthStore } from "@/store/auth";

const CHUNK_SIZE = 256 * 1024; // 256 KB — bounded memory per upload

interface UploadStartResponse {
  job_uuid: string;
  state: string;
  expected_next_chunk: number;
}

interface DuplicateMatch {
  page_uuid: string;
  page_index: number;
  upload_job_uuid: string | null;
  original_filename: string | null;
  source_sha256: string | null;
  match_kind: "filename" | "sha256";
}

interface UploadFinalizeResponse {
  job_uuid: string;
  state: string;
  page_count: number;
  page_uuids: string[];
  source_sha256: string;
  duplicate_sha256_matches: DuplicateMatch[];
}

interface UploadPrecheckResponse {
  filename_matches: DuplicateMatch[];
  project_has_existing_pages: boolean;
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
  const [precheck, setPrecheck] = useState<UploadPrecheckResponse | null>(null);
  const [precheckError, setPrecheckError] = useState<string | null>(null);

  const reset = (): void => {
    setFile(null);
    setProgress(null);
    setError(null);
    setResult(null);
    setPrecheck(null);
    setPrecheckError(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  // K-5 row 6+7: on file pick, call the precheck endpoint to surface
  // filename matches + project-has-pages BEFORE any bytes upload.
  const runPrecheck = async (f: File): Promise<void> => {
    setPrecheck(null);
    setPrecheckError(null);
    try {
      const resp = await api.get<UploadPrecheckResponse>(
        `/uploads/precheck?project_uuid=${projectUuid}&filename=${encodeURIComponent(f.name)}`,
      );
      setPrecheck(resp);
    } catch (e) {
      // Non-fatal: precheck failure shouldn't block the upload.
      setPrecheckError(e instanceof ApiError ? e.detail : "Precheck failed");
    }
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
      //    auto-attaches manually (the typed `api` helper sets a JSON
      //    Content-Type which would clobber multipart's boundary). We
      //    must still go through the `apiPath()` helper so the request
      //    is routed via the vite `/api/*` proxy in dev.
      const token = useAuthStore.getState().token;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      for (let i = 0; i < totalChunks; i++) {
        const offset = i * CHUNK_SIZE;
        const slice = file.slice(offset, offset + CHUNK_SIZE);
        const fd = new FormData();
        fd.append("chunk", slice, "chunk");
        const resp = await fetch(apiPath(`/uploads/${start.job_uuid}/chunks/${i}`), {
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
          <DialogTitle>Upload book, document, image, or archive</DialogTitle>
          <DialogDescription>
            Accepts PDF, an image (JPG / PNG / TIFF / HEIC / WEBP), a text
            document (DOCX / ODT / TXT / XML / HTML), an e-book
            (EPUB / MOBI / AZW / AZW3 / DjVu), or an archive
            (ZIP / RAR / CBZ / CBR — extracted, filename-sorted, supported
            entries recursed). Multi-page TIFFs and DjVus become one page
            per frame; document and e-book formats extract paragraphs
            directly (no OCR). The source is uploaded in 256 KB chunks;
            pages and SCAN-POs materialize on finalize.
          </DialogDescription>
        </DialogHeader>

        <input
          ref={fileRef}
          type="file"
          accept="application/pdf,image/jpeg,image/png,image/tiff,image/heic,image/heif,image/webp,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.oasis.opendocument.text,text/plain,text/xml,application/xml,text/html,application/epub+zip,application/x-mobipocket-ebook,image/vnd.djvu,application/zip,application/vnd.rar,application/x-rar-compressed,application/x-cbz,application/x-cbr,.pdf,.jpg,.jpeg,.png,.tif,.tiff,.heic,.heif,.webp,.docx,.odt,.txt,.xml,.html,.htm,.epub,.mobi,.azw,.azw3,.djvu,.djv,.zip,.rar,.cbz,.cbr"
          onChange={(e) => {
            const f = e.target.files?.[0] ?? null;
            setFile(f);
            setProgress(null);
            setResult(null);
            setError(null);
            setPrecheck(null);
            setPrecheckError(null);
            if (f) {
              void runPrecheck(f);
            }
          }}
          className="text-sm file:mr-3 file:rounded file:border file:bg-background file:px-3 file:py-1.5 file:text-sm hover:file:bg-accent"
        />

        {file && (
          <p className="text-xs text-muted-foreground">
            {file.name} — {(file.size / 1024 / 1024).toFixed(2)} MB,{" "}
            {Math.ceil(file.size / CHUNK_SIZE)} chunks
          </p>
        )}

        {file && file.size > 2 * 1024 * 1024 * 1024 && (
          <div className="rounded border border-red-200 bg-red-50 p-3 text-sm">
            <p className="font-medium text-red-800">File exceeds 2 GB limit</p>
            <p className="text-xs text-red-700 mt-1">
              Canon §2.1 caps uploads at 2 GB. Split this file or compress
              before uploading.
            </p>
          </div>
        )}

        {precheck && precheck.filename_matches.length > 0 && (
          <div className="rounded border border-amber-200 bg-amber-50 p-3 text-sm">
            <p className="font-medium text-amber-900">
              Filename already in this project
            </p>
            <p className="text-xs text-amber-800 mt-1">
              {precheck.filename_matches.length} existing{" "}
              {precheck.filename_matches.length === 1 ? "page" : "pages"} came
              from an earlier upload with the same filename. You can still
              proceed — duplicates are not blocked.
            </p>
            <ul className="text-xs text-amber-800 mt-2 list-disc list-inside max-h-24 overflow-auto">
              {precheck.filename_matches.slice(0, 5).map((m) => (
                <li key={m.page_uuid}>page #{m.page_index}</li>
              ))}
              {precheck.filename_matches.length > 5 && (
                <li>… and {precheck.filename_matches.length - 5} more</li>
              )}
            </ul>
          </div>
        )}

        {precheck && precheck.project_has_existing_pages &&
          precheck.filename_matches.length === 0 && (
            <div className="rounded border border-amber-200 bg-amber-50 p-3 text-sm">
              <p className="font-medium text-amber-900">
                Project already has pages
              </p>
              <p className="text-xs text-amber-800 mt-1">
                Canon §2.2 suggests one book per project. This upload will
                add pages alongside existing ones. Proceed if you intended
                to mix sources.
              </p>
            </div>
          )}

        {precheckError && (
          <div className="text-xs text-muted-foreground italic">
            (precheck unavailable: {precheckError})
          </div>
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
            {result.duplicate_sha256_matches.length > 0 && (
              <div className="mt-2 pt-2 border-t border-emerald-200">
                <p className="text-xs font-medium text-amber-900">
                  Content already in this project ({result.duplicate_sha256_matches.length}{" "}
                  matching {result.duplicate_sha256_matches.length === 1 ? "page" : "pages"})
                </p>
                <p className="text-xs text-amber-800 mt-0.5">
                  Same SHA-256 as a page from an earlier upload. You can keep
                  the new pages, or delete them from the workspace if this was
                  unintended.
                </p>
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button
            onClick={onSubmit}
            disabled={
              !file ||
              uploadMutation.isPending ||
              (file !== null && file.size > 2 * 1024 * 1024 * 1024)
            }
          >
            {uploadMutation.isPending ? "Uploading…" : "Upload"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
