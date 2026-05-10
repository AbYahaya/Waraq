/**
 * OCR-text export Pflichtfragen + run + download dialog.
 *
 * Three steps:
 *   1. Pflichtfragen — page range + block types + markings + mode.
 *   2. Check gate — POST /projects/{uuid}/ocr-export/gate (no log/DE).
 *   3. Run — POST /confirm (writes the Pflichtfragen DE bound to
 *      `export_attempt_id`) then POST /run (gate-recheck → DOCX build →
 *      atomic OCR_EXPORT_EVENT-PO).
 *
 * On success the dialog renders a download link to
 * /ocr-export/artefacts/{po_uuid}.
 */

import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api, apiPath } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { cn } from "@/lib/utils";

interface OcrExportGateResponse {
  state: "exportierbar" | "exportierbar_mit_warnungen" | "blockiert";
  blocking_reasons: string[];
  warnings: string[];
}

interface OcrExportRunResponse {
  job_uuid: string;
  job_state: string;
  artefact_uuid: string;
  sha256: string;
  size_bytes: number;
  ocr_export_event_po_uuid: string;
  n_segments_exported: number;
  n_pages_exported: number;
}

const ALL_BLOCK_TYPES = ["main_text", "UE", "HD", "FN", "QR", "RN"] as const;

export interface OcrExportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectUuid: string;
  /** Pre-fills the page-range input from the page list. */
  defaultPageRange?: number[];
}

export function OcrExportDialog({
  open,
  onOpenChange,
  projectUuid,
  defaultPageRange,
}: OcrExportDialogProps): JSX.Element {
  const [pageRangeText, setPageRangeText] = useState("");
  const [blockTypes, setBlockTypes] = useState<string[]>(["main_text"]);
  const [markingsEnabled, setMarkingsEnabled] = useState(false);
  const [mode, setMode] = useState<"arbeitsstand" | "endgueltig">("arbeitsstand");
  const [gate, setGate] = useState<OcrExportGateResponse | null>(null);
  const [runResult, setRunResult] = useState<OcrExportRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Re-derive default page range when caller updates it.
  useEffect(() => {
    if (defaultPageRange && defaultPageRange.length > 0 && pageRangeText === "") {
      setPageRangeText(defaultPageRange.join(","));
    }
  }, [defaultPageRange, pageRangeText]);

  const pageRange = parseRange(pageRangeText);

  const buildPayload = () => ({
    page_range: pageRange,
    block_types_enabled: blockTypes,
    markings_enabled: markingsEnabled,
    mode,
  });

  const gateMutation = useMutation({
    mutationFn: () =>
      api.post<OcrExportGateResponse>(
        `/projects/${projectUuid}/ocr-export/gate`,
        buildPayload(),
      ),
    onSuccess: (g) => {
      setGate(g);
      setRunResult(null);
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Gate check failed"),
  });

  const runMutation = useMutation({
    mutationFn: async (): Promise<OcrExportRunResponse> => {
      const attemptId = `attempt-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      const body = { pflichtfragen: buildPayload(), export_attempt_id: attemptId };
      // Confirm Pflichtfragen first (writes the DE bound to attemptId).
      await api.post(
        `/projects/${projectUuid}/ocr-export/confirm`,
        body,
      );
      // Then run — gate is re-checked server-side.
      return api.post<OcrExportRunResponse>(
        `/projects/${projectUuid}/ocr-export/run`,
        body,
      );
    },
    onSuccess: (r) => setRunResult(r),
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Export failed"),
  });

  const reset = (): void => {
    setGate(null);
    setRunResult(null);
    setError(null);
  };

  const downloadHref = (poUuid: string): string =>
    apiPath(`/ocr-export/artefacts/${poUuid}`);

  const onDownload = async (poUuid: string): Promise<void> => {
    // The download endpoint requires a bearer token, so we fetch with
    // auth and trigger a save via blob URL.
    const token = useAuthStore.getState().token;
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const resp = await fetch(downloadHref(poUuid), { headers });
    if (!resp.ok) {
      setError(`Download failed: HTTP ${resp.status}`);
      return;
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ocr_export_${poUuid}.docx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const canRun =
    gate?.state === "exportierbar" || gate?.state === "exportierbar_mit_warnungen";

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) reset();
        onOpenChange(o);
      }}
    >
      <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col">
        <div className="flex-1 overflow-y-auto pr-1 space-y-4">
          <DialogHeader>
            <DialogTitle>Export OCR text (DOCX)</DialogTitle>
            <DialogDescription>
              Pflichtfragen require active answers per export. Saved
              profiles never replace this dialog (Sprint-OCR §B).
            </DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1 col-span-2">
              <Label htmlFor="page-range">Page range (e.g. 1,2,5-7)</Label>
              <Input
                id="page-range"
                value={pageRangeText}
                onChange={(e) => setPageRangeText(e.target.value)}
                placeholder="1-3"
              />
            </div>
            <div className="space-y-1 col-span-2">
              <Label>Block types enabled</Label>
              <div className="flex flex-wrap gap-2">
                {ALL_BLOCK_TYPES.map((bt) => (
                  <button
                    key={bt}
                    type="button"
                    onClick={() =>
                      setBlockTypes((cur) =>
                        cur.includes(bt) ? cur.filter((c) => c !== bt) : [...cur, bt],
                      )
                    }
                    className={cn(
                      "rounded border px-2 py-1 text-xs",
                      blockTypes.includes(bt)
                        ? "bg-accent border-foreground/40"
                        : "hover:bg-accent/50",
                    )}
                  >
                    {bt}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <input
                id="markings"
                type="checkbox"
                checked={markingsEnabled}
                onChange={(e) => setMarkingsEnabled(e.target.checked)}
              />
              <Label htmlFor="markings">Markings enabled</Label>
            </div>
            <div className="space-y-1">
              <Label>Mode</Label>
              <div className="flex gap-2">
                {(["arbeitsstand", "endgueltig"] as const).map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setMode(m)}
                    className={cn(
                      "rounded border px-2 py-1 text-xs",
                      mode === m
                        ? "bg-accent border-foreground/40"
                        : "hover:bg-accent/50",
                    )}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {gate && (
            <div className="rounded border p-3 text-sm space-y-1">
              <p>
                <span className="text-muted-foreground">Gate:</span>{" "}
                <span
                  className={cn(
                    "font-medium",
                    gate.state === "blockiert" && "text-destructive",
                    gate.state === "exportierbar_mit_warnungen" && "text-amber-700",
                    gate.state === "exportierbar" && "text-emerald-700",
                  )}
                >
                  {gate.state}
                </span>
              </p>
              {gate.blocking_reasons.length > 0 && (
                <ul className="text-xs text-destructive list-disc pl-4">
                  {gate.blocking_reasons.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              )}
              {gate.warnings.length > 0 && (
                <ul className="text-xs text-amber-700 list-disc pl-4">
                  {gate.warnings.slice(0, 5).map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {runResult && (
            <div className="rounded border border-emerald-200 bg-emerald-50 p-3 text-sm space-y-1">
              <p className="font-medium text-emerald-800">
                Export complete — {runResult.n_pages_exported} pages,{" "}
                {runResult.n_segments_exported} segments.
              </p>
              <p className="text-xs text-emerald-700 truncate">
                sha256: {runResult.sha256.slice(0, 16)}… ·{" "}
                {(runResult.size_bytes / 1024).toFixed(1)} KB
              </p>
              <Button
                size="sm"
                onClick={() => onDownload(runResult.ocr_export_event_po_uuid)}
              >
                Download DOCX
              </Button>
            </div>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <DialogFooter className="pt-3">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setError(null);
              gateMutation.mutate();
            }}
            disabled={gateMutation.isPending || pageRange.length === 0}
          >
            {gateMutation.isPending ? "Checking…" : "Check gate"}
          </Button>
          <Button
            onClick={() => {
              setError(null);
              runMutation.mutate();
            }}
            disabled={!canRun || runMutation.isPending}
          >
            {runMutation.isPending ? "Exporting…" : "Export"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Parse a comma/range string like "1,3,5-7" into [1,3,5,6,7]. */
function parseRange(input: string): number[] {
  const out = new Set<number>();
  for (const piece of input.split(",")) {
    const trimmed = piece.trim();
    if (!trimmed) continue;
    if (trimmed.includes("-")) {
      const [a, b] = trimmed.split("-", 2).map((s) => parseInt(s.trim(), 10));
      if (Number.isFinite(a) && Number.isFinite(b)) {
        const lo = Math.min(a, b);
        const hi = Math.max(a, b);
        for (let i = lo; i <= hi; i++) out.add(i);
      }
    } else {
      const n = parseInt(trimmed, 10);
      if (Number.isFinite(n)) out.add(n);
    }
  }
  return [...out].sort((a, b) => a - b);
}
