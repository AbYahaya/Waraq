/**
 * Translation export dialog — walks the post-`uebersetzungsstart` flow:
 *
 *   1. Translate  — collects all segments under the project, creates a
 *      translation Job, then POST /translation-jobs/{u}/run (synchronous,
 *      uses the OpenAI translator built from server env).
 *   2. Preflight  — opens a fresh preflight run, lets the user confirm
 *      the four canonical Pflichtfragen (active confirmation per export,
 *      Sprint 4 §A), then evaluates.
 *   3. Export     — POST /projects/{u}/exports → atomic EXPORT_EVENT.
 *   4. Download   — DOCX (always) + PDF (LibreOffice-backed; available
 *      only if the backend host has soffice + ghostscript installed).
 *
 * Each phase is gated by the previous one's success — the UI advances
 * automatically and exposes only the actions that are valid in the
 * current state.
 */

import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

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
import { ApiError, api } from "@/lib/api";
import { queries } from "@/lib/queries";
import type { Job, Page, Segment } from "@/lib/types";
import { useAuthStore } from "@/store/auth";
import { cn } from "@/lib/utils";

interface PreflightRunResponse {
  run_uuid: string;
  state: string;
}

interface PreflightEvaluateResponse {
  run_uuid: string;
  state: string;
  blocking_reasons: string[];
  open_warning_slots: string[];
  konfigurationsschicht_complete: boolean;
  pflichtfrage_active_count: number;
}

interface ExportRunResponse {
  job_uuid: string;
  job_state: string;
  export_event_po_uuid: string;
  artefact_uuid: string;
  artefact_sha256: string;
  artefact_size_bytes: number;
  gate_mode: string;
  n_segments_exported: number;
}

const PFLICHTFRAGEN: ReadonlyArray<{ index: number; key: string; label: string }> = [
  { index: 1, key: "frage_1", label: "Page break level (Kapitelumbruch-Ebene) confirmed?" },
  { index: 2, key: "frage_2", label: "Footnote restart strategy confirmed?" },
  { index: 3, key: "frage_3", label: "Heading style mapping confirmed?" },
  { index: 4, key: "frage_4", label: "TOC inclusion confirmed?" },
];

export interface TranslationExportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectUuid: string;
  projectName: string;
}

export function TranslationExportDialog({
  open,
  onOpenChange,
  projectUuid,
  projectName,
}: TranslationExportDialogProps): JSX.Element {
  const [error, setError] = useState<string | null>(null);
  const [translationJob, setTranslationJob] = useState<Job | null>(null);
  const [preflightRunUuid, setPreflightRunUuid] = useState<string | null>(null);
  const [confirmedFragen, setConfirmedFragen] = useState<Set<number>>(new Set());
  const [preflightState, setPreflightState] = useState<PreflightEvaluateResponse | null>(
    null,
  );
  const [exportResult, setExportResult] = useState<ExportRunResponse | null>(null);
  const [projectTitle, setProjectTitle] = useState(projectName);

  const pagesQ = useQuery({
    ...queries.projectPages(projectUuid),
    enabled: open,
  });

  // Collect every segment UUID across all pages — translation runs
  // project-wide.
  const allSegmentsQuery = useQuery<Segment[]>({
    queryKey: ["projects", projectUuid, "all-segments"],
    enabled: open && !!pagesQ.data && pagesQ.data.length > 0,
    queryFn: async () => {
      const pages = pagesQ.data ?? [];
      const lists = await Promise.all(
        pages.map((p: Page) => api.get<Segment[]>(`/pages/${p.page_uuid}/segments`)),
      );
      return lists.flat();
    },
  });

  const segmentUuids = useMemo(
    () => (allSegmentsQuery.data ?? []).map((s) => s.satz_uuid),
    [allSegmentsQuery.data],
  );

  const translateMutation = useMutation({
    mutationFn: async (): Promise<Job> => {
      const job = await api.post<Job>(
        `/projects/${projectUuid}/translation-jobs`,
        { segment_uuids: segmentUuids },
      );
      return api.post<Job>(`/translation-jobs/${job.job_uuid}/run`);
    },
    onSuccess: (j) => setTranslationJob(j),
    onError: (err) =>
      setError(err instanceof ApiError ? err.detail : "Translation failed"),
  });

  const openPreflightMutation = useMutation({
    mutationFn: () =>
      api.post<PreflightRunResponse>(`/projects/${projectUuid}/preflight/runs`),
    onSuccess: (r) => {
      setPreflightRunUuid(r.run_uuid);
      setConfirmedFragen(new Set());
      setPreflightState(null);
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.detail : "Preflight could not start"),
  });

  const confirmFrageMutation = useMutation({
    mutationFn: async (index: number) => {
      const f = PFLICHTFRAGEN.find((p) => p.index === index);
      if (!f || !preflightRunUuid) throw new Error("inconsistent state");
      await api.post(
        `/projects/${projectUuid}/preflight/runs/${preflightRunUuid}/pflichtfragen`,
        { frage_index: f.index, frage_key: f.key, answer: { value: "yes" } },
      );
      return f.index;
    },
    onSuccess: (index) =>
      setConfirmedFragen((prev) => {
        const next = new Set(prev);
        next.add(index);
        return next;
      }),
    onError: (err) =>
      setError(err instanceof ApiError ? err.detail : "Confirmation failed"),
  });

  const evaluateMutation = useMutation({
    mutationFn: () => {
      if (!preflightRunUuid) throw new Error("no preflight run");
      return api.post<PreflightEvaluateResponse>(
        `/projects/${projectUuid}/preflight/runs/${preflightRunUuid}/evaluate`,
      );
    },
    onSuccess: (e) => setPreflightState(e),
    onError: (err) =>
      setError(err instanceof ApiError ? err.detail : "Evaluation failed"),
  });

  const exportMutation = useMutation({
    mutationFn: () => {
      if (!preflightRunUuid) throw new Error("no preflight run");
      return api.post<ExportRunResponse>(`/projects/${projectUuid}/exports`, {
        project_uuid: projectUuid,
        project_title: projectTitle,
        preflight_run_uuid: preflightRunUuid,
      });
    },
    onSuccess: (r) => setExportResult(r),
    onError: (err) =>
      setError(err instanceof ApiError ? err.detail : "Export failed"),
  });

  const reset = (): void => {
    setError(null);
    setTranslationJob(null);
    setPreflightRunUuid(null);
    setConfirmedFragen(new Set());
    setPreflightState(null);
    setExportResult(null);
  };

  const allConfirmed = confirmedFragen.size === PFLICHTFRAGEN.length;
  const exportable =
    preflightState?.state === "exportierbar" ||
    preflightState?.state === "exportierbar_mit_warnungen";

  const onDownload = async (
    poUuid: string,
    pdf: boolean,
  ): Promise<void> => {
    const token = useAuthStore.getState().token;
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const url = pdf
      ? `/exports/artefacts/${poUuid}/pdf`
      : `/exports/artefacts/${poUuid}`;
    const resp = await fetch(url, { headers });
    if (!resp.ok) {
      setError(`Download failed: HTTP ${resp.status}`);
      return;
    }
    const blob = await resp.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = `translation_export_${poUuid}.${pdf ? "pdf" : "docx"}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(blobUrl);
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) reset();
        onOpenChange(o);
      }}
    >
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Export translation</DialogTitle>
          <DialogDescription>
            Translates every segment, runs preflight (4 Pflichtfragen +
            audit/consistency gates), then writes the EXPORT_EVENT and
            offers DOCX + PDF download.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* --- Stage 1: translation -------------------------------- */}
          <section className="rounded border p-3 space-y-2">
            <header className="text-sm font-medium">1. Translate</header>
            <p className="text-xs text-muted-foreground">
              {segmentUuids.length} segment(s) under this project. Runs
              synchronously against OpenAI; allow ~1 second per segment.
            </p>
            {translationJob ? (
              <p
                className={cn(
                  "text-xs font-medium",
                  translationJob.state === "completed"
                    ? "text-emerald-700"
                    : "text-amber-700",
                )}
              >
                Translation job: {translationJob.state}
              </p>
            ) : (
              <Button
                size="sm"
                disabled={
                  translateMutation.isPending || segmentUuids.length === 0
                }
                onClick={() => {
                  setError(null);
                  translateMutation.mutate();
                }}
              >
                {translateMutation.isPending
                  ? "Translating…"
                  : "Run translation"}
              </Button>
            )}
          </section>

          {/* --- Stage 2: preflight --------------------------------- */}
          <section
            className={cn(
              "rounded border p-3 space-y-2",
              translationJob?.state === "completed" ? "" : "opacity-50",
            )}
          >
            <header className="text-sm font-medium">2. Preflight</header>
            {!preflightRunUuid && (
              <Button
                size="sm"
                disabled={
                  translationJob?.state !== "completed" ||
                  openPreflightMutation.isPending
                }
                onClick={() => {
                  setError(null);
                  openPreflightMutation.mutate();
                }}
              >
                {openPreflightMutation.isPending ? "Opening…" : "Open preflight run"}
              </Button>
            )}
            {preflightRunUuid && (
              <>
                <p className="text-xs text-muted-foreground">
                  Confirm each Pflichtfrage (Sprint 4 §A — active
                  confirmation per export run).
                </p>
                <ul className="space-y-1">
                  {PFLICHTFRAGEN.map((f) => (
                    <li
                      key={f.key}
                      className="flex items-center gap-2 text-sm"
                    >
                      <Button
                        size="sm"
                        variant={
                          confirmedFragen.has(f.index) ? "default" : "outline"
                        }
                        disabled={confirmedFragen.has(f.index) || confirmFrageMutation.isPending}
                        onClick={() => {
                          setError(null);
                          confirmFrageMutation.mutate(f.index);
                        }}
                      >
                        {confirmedFragen.has(f.index) ? "✓" : `Confirm ${f.index}`}
                      </Button>
                      <span className="text-xs">{f.label}</span>
                    </li>
                  ))}
                </ul>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!allConfirmed || evaluateMutation.isPending}
                  onClick={() => {
                    setError(null);
                    evaluateMutation.mutate();
                  }}
                >
                  {evaluateMutation.isPending ? "Evaluating…" : "Evaluate preflight"}
                </Button>
                {preflightState && (
                  <div className="text-xs space-y-1 pt-2">
                    <p>
                      <span className="text-muted-foreground">State:</span>{" "}
                      <span
                        className={cn(
                          "font-medium",
                          preflightState.state === "blockiert" &&
                            "text-destructive",
                          preflightState.state === "exportierbar_mit_warnungen" &&
                            "text-amber-700",
                          preflightState.state === "exportierbar" &&
                            "text-emerald-700",
                        )}
                      >
                        {preflightState.state}
                      </span>
                    </p>
                    {preflightState.blocking_reasons.length > 0 && (
                      <ul className="list-disc pl-4 text-destructive">
                        {preflightState.blocking_reasons.map((r) => (
                          <li key={r}>{r}</li>
                        ))}
                      </ul>
                    )}
                    {preflightState.open_warning_slots.length > 0 && (
                      <ul className="list-disc pl-4 text-amber-700">
                        {preflightState.open_warning_slots.map((w) => (
                          <li key={w}>{w}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </>
            )}
          </section>

          {/* --- Stage 3: export ------------------------------------- */}
          <section
            className={cn(
              "rounded border p-3 space-y-2",
              exportable ? "" : "opacity-50",
            )}
          >
            <header className="text-sm font-medium">3. Export</header>
            <div className="space-y-1">
              <Label htmlFor="project-title">Title (used in DOCX header)</Label>
              <Input
                id="project-title"
                value={projectTitle}
                onChange={(e) => setProjectTitle(e.target.value)}
              />
            </div>
            {exportResult ? (
              <div className="space-y-2 pt-1">
                <p className="text-xs text-emerald-700 font-medium">
                  Export complete — {exportResult.n_segments_exported} segment(s),{" "}
                  {(exportResult.artefact_size_bytes / 1024).toFixed(1)} KB
                </p>
                <p className="text-xs text-muted-foreground truncate">
                  sha256: {exportResult.artefact_sha256.slice(0, 16)}…
                </p>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => onDownload(exportResult.export_event_po_uuid, false)}
                  >
                    Download DOCX
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onDownload(exportResult.export_event_po_uuid, true)}
                  >
                    Download PDF
                  </Button>
                </div>
                <p className="text-[11px] text-muted-foreground">
                  PDF requires LibreOffice + Ghostscript on the backend host;
                  503 if unavailable.
                </p>
              </div>
            ) : (
              <Button
                size="sm"
                disabled={!exportable || exportMutation.isPending}
                onClick={() => {
                  setError(null);
                  exportMutation.mutate();
                }}
              >
                {exportMutation.isPending ? "Exporting…" : "Run export"}
              </Button>
            )}
          </section>

          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
