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

import { useEffect, useMemo, useState } from "react";
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
import { ApiError, api, apiPath } from "@/lib/api";
import { queries } from "@/lib/queries";
import type {
  Job,
  Page,
  ProjectTranslationAvailability,
  Segment,
} from "@/lib/types";
import { useAuthStore } from "@/store/auth";
import { cn } from "@/lib/utils";

interface TranslationJobPayload {
  chunks_total?: number;
  chunks_translated?: number;
  chunks_processed?: number;
  cancel_requested?: boolean;
}

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

interface GuardNearResponse {
  passes: boolean;
  blockers: string[];
  advisories: string[];
  evidence: Record<string, string[]>;
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

type PdfFormatChoice = "digital_rgb" | "print_pdf_x_1a";

// Canonical 4 Pflichtfragen per §4.7.2 — keys + answer shapes are
// validated server-side via per-question Pydantic schemas. The shape
// of `answer` differs per question; sending the wrong key or shape
// gives a 400.
type PflichtfrageAnswer =
  | { heading_level: number }
  | { position: "front" | "back" }
  | { display: boolean };

interface PflichtfrageDef {
  index: 1 | 2 | 3 | 4;
  key:
    | "header_heading_level"
    | "chapter_break_heading_level"
    | "toc_position"
    | "display_arabic_chapter_headings";
  label: string;
}

const PFLICHTFRAGEN: ReadonlyArray<PflichtfrageDef> = [
  {
    index: 1,
    key: "header_heading_level",
    label: "Running header source",
  },
  {
    index: 2,
    key: "chapter_break_heading_level",
    label: "Chapter break level",
  },
  { index: 3, key: "toc_position", label: "Contents position" },
  {
    index: 4,
    key: "display_arabic_chapter_headings",
    label: "Arabic/OCR source text",
  },
];

const PFLICHTFRAGE_HELP: Record<PflichtfrageDef["key"], string> = {
  header_heading_level:
    "Chooses which heading depth should feed running headers when the export has heading-aware headers.",
  chapter_break_heading_level:
    "Chooses which heading depth starts a new chapter section in the exported book.",
  toc_position:
    "Places the generated table of contents before the body or after the body.",
  display_arabic_chapter_headings:
    "Controls whether Arabic OCR/source paragraphs are included beside the translation in the exported document.",
};

interface PflichtfragenState {
  header_heading_level: number;
  chapter_break_heading_level: number;
  toc_position: "front" | "back";
  display_arabic_chapter_headings: boolean;
}

const DEFAULT_PFLICHTFRAGEN_STATE: PflichtfragenState = {
  header_heading_level: 1,
  chapter_break_heading_level: 1,
  toc_position: "front",
  display_arabic_chapter_headings: true,
};

const PREFLIGHT_LABELS: Record<string, string> = {
  digit_standard: "Some exported translation text still contains Arabic-Indic digits.",
  critical_rtl: "A critical right-to-left formatting issue was detected.",
  style_template_integrity: "The export style template has a structural problem.",
  critical_font_missing: "One or more preferred print fonts are missing on the backend.",
  p_03_kritisch: "Critical audit, consistency, or OCR findings are still unresolved.",
  p_04_hoch_pflichthinweis: "High-priority mandatory notices are still unresolved.",
  hadith_h2: "A hadith reference check is blocking export.",
  konfigurationsschicht_unvollstaendig:
    "All four export setup questions must be confirmed for this run.",
  w_01_mittel_audit: "Medium audit findings need acknowledgement before export.",
  w_02_konsistenz: "Consistency findings need acknowledgement before export.",
  w_03_formatvorlagen_graduell:
    "Non-critical style-template differences need acknowledgement before export.",
  hadith_h1: "Hadith reference warnings need acknowledgement before export.",
};

const describeCode = (code: string): string => PREFLIGHT_LABELS[code] ?? code;

const describeApiError = (err: unknown, fallback: string): string => {
  if (!(err instanceof ApiError)) return fallback;
  const body = err.body as { detail?: unknown } | null;
  const detail = body?.detail;
  if (detail && typeof detail === "object") {
    const reason = "reason" in detail ? String((detail as { reason?: unknown }).reason) : null;
    const blockers = Array.isArray((detail as { blockers?: unknown }).blockers)
      ? ((detail as { blockers: unknown[] }).blockers as unknown[]).map(String)
      : [];
    const advisories = Array.isArray((detail as { advisories?: unknown }).advisories)
      ? ((detail as { advisories: unknown[] }).advisories as unknown[]).map(String)
      : [];
    const parts = [
      reason ? describeCode(reason) : fallback,
      ...blockers.map(describeCode),
      ...advisories.map((code) => `Advisory: ${describeCode(code)}`),
    ];
    return parts.join(" ");
  }
  return err.detail || fallback;
};

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
  const [pflichtfragenAnswers, setPflichtfragenAnswers] = useState<PflichtfragenState>(
    DEFAULT_PFLICHTFRAGEN_STATE,
  );
  const [pdfFormatChoice, setPdfFormatChoice] =
    useState<PdfFormatChoice>("print_pdf_x_1a");
  const [preflightState, setPreflightState] = useState<PreflightEvaluateResponse | null>(
    null,
  );
  const [exportResult, setExportResult] = useState<ExportRunResponse | null>(null);
  const [projectTitle, setProjectTitle] = useState(projectName);

  const buildAnswer = (key: PflichtfrageDef["key"]): PflichtfrageAnswer => {
    switch (key) {
      case "header_heading_level":
        return { heading_level: pflichtfragenAnswers.header_heading_level };
      case "chapter_break_heading_level":
        return { heading_level: pflichtfragenAnswers.chapter_break_heading_level };
      case "toc_position":
        return { position: pflichtfragenAnswers.toc_position };
      case "display_arabic_chapter_headings":
        return { display: pflichtfragenAnswers.display_arabic_chapter_headings };
    }
  };

  const pagesQ = useQuery({
    ...queries.projectPages(projectUuid),
    enabled: open,
  });

  const translationAvailabilityQ = useQuery<ProjectTranslationAvailability>({
    queryKey: ["projects", projectUuid, "translation-availability"],
    enabled: open,
    queryFn: () =>
      api.get<ProjectTranslationAvailability>(
        `/projects/${projectUuid}/translation-availability`,
      ),
  });
  const { refetch: refetchTranslationAvailability } = translationAvailabilityQ;

  const guardNearQ = useQuery<GuardNearResponse>({
    queryKey: ["projects", projectUuid, "preflight", "guard-near"],
    enabled: open,
    queryFn: () =>
      api.get<GuardNearResponse>(`/projects/${projectUuid}/preflight/guard-near`),
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
      // /run is now async — returns 202 immediately with state=pending.
      // The poll query below picks up the running state + progress.
      return api.post<Job>(`/translation-jobs/${job.job_uuid}/run`);
    },
    onSuccess: (j) => setTranslationJob(j),
    onError: (err) =>
      setError(describeApiError(err, "Translation failed")),
  });

  // Poll the job while it's still active so we can show a progress bar
  // + react to completion. Stop polling on terminal states.
  const isJobActive =
    translationJob !== null &&
    (translationJob.state === "pending" || translationJob.state === "running");
  const jobPollQuery = useQuery<Job>({
    queryKey: ["translation-job", translationJob?.job_uuid],
    enabled: isJobActive,
    refetchInterval: isJobActive ? 1500 : false,
    queryFn: () => api.get<Job>(`/translation-jobs/${translationJob!.job_uuid}`),
  });

  useEffect(() => {
    if (jobPollQuery.data) setTranslationJob(jobPollQuery.data);
  }, [jobPollQuery.data]);

  useEffect(() => {
    if (translationJob?.state === "completed") {
      void refetchTranslationAvailability();
    }
  }, [translationJob?.state, refetchTranslationAvailability]);

  const cancelMutation = useMutation({
    mutationFn: () => {
      if (!translationJob) throw new Error("no job to cancel");
      return api.post<Job>(`/translation-jobs/${translationJob.job_uuid}/cancel`);
    },
    onSuccess: (j) => setTranslationJob(j),
    onError: (err) =>
      setError(describeApiError(err, "Cancel failed")),
  });

  const jobPayload = (translationJob?.payload ?? {}) as TranslationJobPayload;
  const chunksTotal = jobPayload.chunks_total ?? segmentUuids.length;
  const chunksTranslated = jobPayload.chunks_translated ?? 0;
  const chunksProcessed = jobPayload.chunks_processed ?? 0;
  const progressPct = chunksTotal > 0 ? Math.min(100, (chunksProcessed / chunksTotal) * 100) : 0;
  const cancelRequested = jobPayload.cancel_requested === true;
  const jobError = translationJob?.error as { phase?: string; repr?: string } | null | undefined;
  const persistedTranslation = translationAvailabilityQ.data;
  const translationReady =
    translationJob?.state === "completed" ||
    persistedTranslation?.has_full_fresh_translation === true;

  const openPreflightMutation = useMutation({
    mutationFn: () =>
      api.post<PreflightRunResponse>(`/projects/${projectUuid}/preflight/runs`),
    onSuccess: (r) => {
      setPreflightRunUuid(r.run_uuid);
      setConfirmedFragen(new Set());
      setPreflightState(null);
    },
    onError: (err) =>
      setError(describeApiError(err, "Preflight could not start")),
  });

  const confirmFrageMutation = useMutation({
    mutationFn: async (index: number) => {
      const f = PFLICHTFRAGEN.find((p) => p.index === index);
      if (!f || !preflightRunUuid) throw new Error("inconsistent state");
      await api.post(
        `/projects/${projectUuid}/preflight/runs/${preflightRunUuid}/pflichtfragen`,
        { frage_index: f.index, frage_key: f.key, answer: buildAnswer(f.key) },
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
      setError(describeApiError(err, "Confirmation failed")),
  });

  const evaluateMutation = useMutation({
    mutationFn: async () => {
      if (!preflightRunUuid) throw new Error("no preflight run");
      await api.post(
        `/projects/${projectUuid}/preflight/runs/${preflightRunUuid}/pdf-format`,
        { choice: pdfFormatChoice },
      );
      return api.post<PreflightEvaluateResponse>(
        `/projects/${projectUuid}/preflight/runs/${preflightRunUuid}/evaluate`,
      );
    },
    onSuccess: (e) => setPreflightState(e),
    onError: (err) =>
      setError(describeApiError(err, "Evaluation failed")),
  });

  const acceptWarningsMutation = useMutation({
    mutationFn: async (): Promise<PreflightEvaluateResponse> => {
      if (!preflightRunUuid || !preflightState) throw new Error("no warning state");
      await Promise.all(
        preflightState.open_warning_slots.map((warningSlot) =>
          api.post(
            `/projects/${projectUuid}/preflight/runs/${preflightRunUuid}/warnings`,
            { warning_slot: warningSlot },
          ),
        ),
      );
      return api.post<PreflightEvaluateResponse>(
        `/projects/${projectUuid}/preflight/runs/${preflightRunUuid}/evaluate`,
      );
    },
    onSuccess: (e) => setPreflightState(e),
    onError: (err) =>
      setError(describeApiError(err, "Warning acknowledgement failed")),
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
      setError(describeApiError(err, "Export failed")),
  });

  const reset = (): void => {
    setError(null);
    setTranslationJob(null);
    setPreflightRunUuid(null);
    setConfirmedFragen(new Set());
    setPflichtfragenAnswers(DEFAULT_PFLICHTFRAGEN_STATE);
    setPdfFormatChoice("print_pdf_x_1a");
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
    const url = apiPath(
      pdf
        ? `/exports/artefacts/${poUuid}/pdf`
        : `/exports/artefacts/${poUuid}`,
    );
    const resp = await fetch(url, { headers });
    if (!resp.ok) {
      setError(`Download failed: HTTP ${resp.status}`);
      return;
    }
    const contentType = resp.headers.get("content-type") ?? "";
    const expectedType = pdf
      ? "application/pdf"
      : "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
    if (!contentType.includes(expectedType)) {
      setError(`Download failed: unexpected content type (${contentType || "unknown"})`);
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
      <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col">
        <div className="flex-1 overflow-y-auto pr-1 space-y-4">
          <DialogHeader>
            <DialogTitle>Export translation</DialogTitle>
            <DialogDescription>
              Translates every segment, checks export readiness, records the
              required setup choices, then creates DOCX and PDF downloads.
            </DialogDescription>
          </DialogHeader>
          {/* --- Stage 1: translation -------------------------------- */}
          <section className="rounded border p-3 space-y-2">
            <header className="text-sm font-medium">1. Translate</header>
            <p className="text-xs text-muted-foreground">
              {segmentUuids.length} segment(s) under this project. Runs
              segment-by-segment with §3.6 cross-check; you can cancel
              while in progress.
            </p>
            {!translationJob && (
              <>
                {persistedTranslation?.has_translation && (
                  <p
                    className={cn(
                      "text-xs",
                      persistedTranslation.has_full_fresh_translation
                        ? "text-emerald-700"
                        : "text-amber-700",
                    )}
                  >
                    {persistedTranslation.has_full_fresh_translation
                      ? `Fresh stored translation available for all ${persistedTranslation.total_segments} segment(s).`
                      : persistedTranslation.has_full_translation
                        ? `Translation exists for all ${persistedTranslation.total_segments} segment(s), but ${persistedTranslation.stale_translated_segments} segment(s) are outdated.`
                        : `Translation exists for ${persistedTranslation.translated_segments} of ${persistedTranslation.total_segments} segment(s); ${persistedTranslation.untranslated_segments} segment(s) still need translation.`}
                    {" "}
                    {persistedTranslation.has_full_fresh_translation
                      ? "You can continue to preflight or rerun translation."
                      : "Rerun translation before preflight/export."}
                  </p>
                )}
                {persistedTranslation &&
                  persistedTranslation.stale_translated_segments > 0 && (
                    <p className="text-xs text-amber-700">
                      OCR/source edits were made after translation on{" "}
                      {persistedTranslation.stale_translated_segments} segment(s).
                    </p>
                  )}
                {translationAvailabilityQ.isLoading && (
                  <p className="text-xs text-muted-foreground">
                    Checking existing translation state…
                  </p>
                )}
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
                    ? "Starting…"
                    : persistedTranslation?.has_translation
                      ? "Run translation again"
                      : "Run translation"}
                </Button>
              </>
            )}
            {translationJob && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span
                    className={cn(
                      "font-medium",
                      translationJob.state === "completed" && "text-emerald-700",
                      translationJob.state === "failed" && "text-destructive",
                      (translationJob.state === "running" ||
                        translationJob.state === "pending") &&
                        "text-amber-700",
                    )}
                  >
                    {translationJob.state}
                    {cancelRequested &&
                      translationJob.state === "running" &&
                      " (cancelling…)"}
                  </span>
                  <span className="text-muted-foreground">
                    {chunksProcessed}/{chunksTotal} segment(s)
                    {chunksProcessed !== chunksTranslated &&
                      ` — ${chunksTranslated} translated, ${chunksProcessed - chunksTranslated} skipped`}
                  </span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded bg-muted">
                  <div
                    className={cn(
                      "h-full transition-[width] duration-300 ease-out",
                      translationJob.state === "completed"
                        ? "bg-emerald-600"
                        : translationJob.state === "failed"
                          ? "bg-destructive"
                          : "bg-amber-500",
                    )}
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
                {(translationJob.state === "running" ||
                  translationJob.state === "pending") && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={cancelMutation.isPending || cancelRequested}
                    onClick={() => {
                      setError(null);
                      cancelMutation.mutate();
                    }}
                  >
                    {cancelRequested ? "Cancelling…" : "Cancel translation"}
                  </Button>
                )}
                {translationJob.state === "failed" && (
                  <div className="space-y-1">
                    <p className="text-xs text-destructive">
                      {jobError?.phase === "user_cancelled"
                        ? "Cancelled."
                        : `Failed (${jobError?.phase ?? "unknown phase"}).`}
                      {jobError?.repr && jobError.phase !== "user_cancelled" && (
                        <span className="block opacity-70 font-mono break-all">
                          {jobError.repr}
                        </span>
                      )}
                    </p>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setError(null);
                        setTranslationJob(null);
                      }}
                    >
                      Try again
                    </Button>
                  </div>
                )}
              </div>
            )}
          </section>

          {/* --- Stage 2: preflight --------------------------------- */}
          <section
            className={cn(
              "rounded border p-3 space-y-2",
              translationReady ? "" : "opacity-50",
            )}
          >
            <header className="text-sm font-medium">2. Preflight</header>
            <p className="text-xs text-muted-foreground">
              This is an export safety check and setup step. It does not change
              your translation text. It records the layout choices below, checks
              unresolved review/font/style blockers, and then allows export.
            </p>
            {guardNearQ.data && (
              <div className="rounded border bg-muted/30 p-2 text-xs space-y-1">
                <p className="font-medium">
                  Readiness preview:{" "}
                  <span
                    className={
                      guardNearQ.data.passes ? "text-emerald-700" : "text-destructive"
                    }
                  >
                    {guardNearQ.data.passes ? "no hard blockers" : "blocked"}
                  </span>
                </p>
                {guardNearQ.data.blockers.length > 0 && (
                  <ul className="list-disc pl-4 text-destructive">
                    {guardNearQ.data.blockers.map((code) => (
                      <li key={code}>{describeCode(code)}</li>
                    ))}
                  </ul>
                )}
                {guardNearQ.data.advisories.length > 0 && (
                  <ul className="list-disc pl-4 text-amber-700">
                    {guardNearQ.data.advisories.map((code) => (
                      <li key={code}>{describeCode(code)}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            {!translationReady && persistedTranslation && (
              <p className="text-xs text-muted-foreground">
                Preflight unlocks when the whole project has a fresh translation state.
              </p>
            )}
            {!preflightRunUuid && (
              <Button
                size="sm"
                disabled={
                  !translationReady ||
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
                  Confirm each export-layout choice. These are saved only for
                  this export run and applied when DOCX/PDF is generated.
                </p>
                <ul className="space-y-2">
                  {PFLICHTFRAGEN.map((f) => {
                    const done = confirmedFragen.has(f.index);
                    return (
                      <li
                        key={f.key}
                        className="flex flex-col gap-1 rounded border p-2"
                      >
                        <span className="text-xs font-medium">
                          {f.index}. {f.label}
                        </span>
                        <span className="text-[11px] text-muted-foreground">
                          {PFLICHTFRAGE_HELP[f.key]}
                        </span>
                        <div className="flex items-center gap-2">
                          {(f.key === "header_heading_level" ||
                            f.key === "chapter_break_heading_level") && (
                            <select
                              className="h-8 rounded border bg-background px-2 text-sm"
                              disabled={done}
                              value={pflichtfragenAnswers[f.key]}
                              onChange={(e) =>
                                setPflichtfragenAnswers((prev) => ({
                                  ...prev,
                                  [f.key]: Number(e.target.value),
                                }))
                              }
                            >
                              {[1, 2, 3, 4, 5, 6].map((n) => (
                                <option key={n} value={n}>
                                  Heading {n}
                                </option>
                              ))}
                            </select>
                          )}
                          {f.key === "toc_position" && (
                            <select
                              className="h-8 rounded border bg-background px-2 text-sm"
                              disabled={done}
                              value={pflichtfragenAnswers.toc_position}
                              onChange={(e) =>
                                setPflichtfragenAnswers((prev) => ({
                                  ...prev,
                                  toc_position: e.target.value as "front" | "back",
                                }))
                              }
                            >
                              <option value="front">Front</option>
                              <option value="back">Back</option>
                            </select>
                          )}
                          {f.key === "display_arabic_chapter_headings" && (
                            <label className="flex items-center gap-2 text-sm">
                              <input
                                type="checkbox"
                                disabled={done}
                                checked={
                                  pflichtfragenAnswers.display_arabic_chapter_headings
                                }
                                onChange={(e) =>
                                  setPflichtfragenAnswers((prev) => ({
                                    ...prev,
                                    display_arabic_chapter_headings: e.target.checked,
                                  }))
                                }
                              />
                              <span>Include Arabic/OCR source</span>
                            </label>
                          )}
                          <Button
                            size="sm"
                            variant={done ? "default" : "outline"}
                            disabled={done || confirmFrageMutation.isPending}
                            onClick={() => {
                              setError(null);
                              confirmFrageMutation.mutate(f.index);
                            }}
                          >
                            {done ? "✓ Confirmed" : "Confirm"}
                          </Button>
                        </div>
                      </li>
                    );
                  })}
                </ul>
                <div className="rounded border p-2 space-y-1">
                  <Label htmlFor="pdf-format">PDF output</Label>
                  <select
                    id="pdf-format"
                    className="h-8 rounded border bg-background px-2 text-sm"
                    value={pdfFormatChoice}
                    onChange={(e) =>
                      setPdfFormatChoice(e.target.value as PdfFormatChoice)
                    }
                  >
                    <option value="print_pdf_x_1a">Print PDF/X-1a</option>
                    <option value="digital_rgb">Digital RGB PDF</option>
                  </select>
                  <p className="text-[11px] text-muted-foreground">
                    Print mode uses the stricter Ghostscript PDF/X path; digital
                    mode is lighter and better for screen review.
                  </p>
                </div>
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
                          <li key={r}>{describeCode(r)}</li>
                        ))}
                      </ul>
                    )}
                    {preflightState.open_warning_slots.length > 0 && (
                      <div className="space-y-2">
                        <ul className="list-disc pl-4 text-amber-700">
                          {preflightState.open_warning_slots.map((w) => (
                            <li key={w}>{describeCode(w)}</li>
                          ))}
                        </ul>
                        {preflightState.blocking_reasons.length === 0 &&
                          preflightState.state === "blockiert" && (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={acceptWarningsMutation.isPending}
                              onClick={() => {
                                setError(null);
                                acceptWarningsMutation.mutate();
                              }}
                            >
                              {acceptWarningsMutation.isPending
                                ? "Acknowledging…"
                                : "Acknowledge warnings and re-check"}
                            </Button>
                          )}
                      </div>
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
            <p className="text-[11px] text-muted-foreground">
              Export uses the saved project style profile at the moment you run export.
              Save style changes in Book preview or Solo Translation before exporting.
            </p>
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

        <DialogFooter className="pt-3">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
