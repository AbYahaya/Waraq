/**
 * Sub-batch O (out-of-phase, 2026-05-12) — OCR auto-run progress + cancel panel.
 *
 * Replaces the old fire-and-block "Auto-OCR all pages" button. Three states:
 *   - idle: shows a "Start Auto-OCR" button + total ausstehend count
 *   - running / pending: shows a live progress bar (N/M pages) + Cancel button
 *   - terminal (completed / failed): shows the result + "New run" button
 *
 * On mount the panel calls `GET /ocr/projects/{u}/ocr-jobs/in-flight` so a
 * page refresh during a long OCR run picks the progress UI back up
 * (no localStorage needed — server state is the source of truth).
 *
 * Polls `GET /ocr/ocr-jobs/{u}` every 1.5s while non-terminal. Cancel calls
 * `POST /ocr/ocr-jobs/{u}/cancel` which flips a cooperative flag; the
 * runner aborts at the next page boundary.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useIsMutating, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { qk } from "@/lib/queries";

// Shared mutation key for the per-page Run-OCR mutation in OcrReviewBar.
// The panel uses `useIsMutating({ mutationKey })` against this so the
// project-wide Start button disables while ANY per-page run is in flight.
export const OCR_PAGE_AUTO_RUN_MUTATION_KEY = ["ocr-page-auto-run"] as const;

// Shared query key for the in-flight project auto-run lookup. The panel
// fetches/invalidates it; OcrReviewBar reads it via
// `useProjectOcrAutoRunActive` to disable its per-page Run-OCR button
// when the project-wide run is active.
const inFlightKey = (projectUuid: string) =>
  ["ocr-auto-run", "in-flight", projectUuid] as const;

interface OcrJobStatus {
  ocr_job_uuid: string;
  project_uuid: string;
  state: "pending" | "running" | "paused" | "completed" | "failed";
  total_pages: number;
  processed_count: number;
  skipped_count: number;
  current_page_index: number | null;
  cancel_requested: boolean;
  last_error: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  created_at: string;
}

interface OcrAutoRunStartResponse {
  ocr_job_uuid: string;
  project_uuid: string;
  state: string;
  total_pages: number;
}

const TERMINAL_STATES = new Set(["completed", "failed"]);

/**
 * Reads the project-wide OCR auto-run in-flight state. Returns `true`
 * iff there's a non-terminal `ocr_auto_run` Job for the project.
 *
 * Used by `OcrReviewBar` to disable its per-page "Run OCR" button when
 * the bulk run is active. The runner row-locks the Page row, so a
 * per-page click during the bulk run would block at the DB level and
 * hang the UI — disabling the button surfaces the conflict explicitly.
 */
export function useProjectOcrAutoRunActive(projectUuid: string): boolean {
  const q = useQuery<OcrJobStatus | null>({
    queryKey: inFlightKey(projectUuid),
    queryFn: () =>
      api.get<OcrJobStatus | null>(
        `/ocr/projects/${projectUuid}/ocr-jobs/in-flight`,
      ),
    // Poll while there IS an in-flight job (so the bar picks up the
    // terminal transition without waiting for an explicit invalidate).
    // When idle (data === null), the panel will invalidate on start, so
    // no polling needed.
    refetchInterval: (rq) => (rq.state.data ? 2000 : false),
  });
  return q.data !== null && q.data !== undefined;
}

export function OcrAutoRunPanel({
  projectUuid,
}: {
  projectUuid: string;
}): JSX.Element {
  const qc = useQueryClient();
  const [activeJobUuid, setActiveJobUuid] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  // On mount: check for an in-flight job so a refresh picks the progress
  // UI back up. Shares its queryKey with `useProjectOcrAutoRunActive` so
  // `OcrReviewBar` reads the same state without a separate fetch.
  const inFlightQ = useQuery<OcrJobStatus | null>({
    queryKey: inFlightKey(projectUuid),
    queryFn: () =>
      api.get<OcrJobStatus | null>(
        `/ocr/projects/${projectUuid}/ocr-jobs/in-flight`,
      ),
  });

  // Number of per-page Run-OCR mutations currently in flight (any page,
  // any component). Drives the Start button's disabled state — we
  // refuse to launch project-wide while a per-page run is still
  // running, since both would race on the same Page row lock.
  const perPageRunCount = useIsMutating({
    mutationKey: [...OCR_PAGE_AUTO_RUN_MUTATION_KEY],
  });

  useEffect(() => {
    if (
      inFlightQ.data &&
      typeof inFlightQ.data === "object" &&
      "ocr_job_uuid" in inFlightQ.data &&
      activeJobUuid === null
    ) {
      setActiveJobUuid(inFlightQ.data.ocr_job_uuid);
    }
  }, [inFlightQ.data, activeJobUuid]);

  // Poll the active job's status.
  const statusQ = useQuery<OcrJobStatus>({
    queryKey: ["ocr-auto-run", "status", activeJobUuid],
    queryFn: () =>
      api.get<OcrJobStatus>(`/ocr/ocr-jobs/${activeJobUuid}`),
    enabled: !!activeJobUuid,
    refetchInterval: (q) => {
      const s = q.state.data;
      if (!s) return 1500;
      return TERMINAL_STATES.has(s.state) ? false : 1500;
    },
  });

  // When the job reaches a terminal state, invalidate the pages list
  // so OCR'd pages reflect their new status in the sidebar. Also
  // invalidate the in-flight query so OcrReviewBar re-enables its
  // per-page Run-OCR button.
  useEffect(() => {
    if (statusQ.data && TERMINAL_STATES.has(statusQ.data.state)) {
      void qc.invalidateQueries({ queryKey: qk.projectPages(projectUuid) });
      void qc.invalidateQueries({ queryKey: inFlightKey(projectUuid) });
    }
  }, [statusQ.data, qc, projectUuid]);

  const startRun = useCallback(async () => {
    setStartError(null);
    setStarting(true);
    try {
      const resp = await api.post<OcrAutoRunStartResponse>(
        `/ocr/projects/${projectUuid}/auto-run`,
      );
      setActiveJobUuid(resp.ocr_job_uuid);
      // Invalidate the shared in-flight query so other components
      // (e.g. OcrReviewBar via useProjectOcrAutoRunActive) flip into
      // the "bulk run is active, disable per-page" state immediately.
      void qc.invalidateQueries({ queryKey: inFlightKey(projectUuid) });
    } catch (e) {
      setStartError(e instanceof ApiError ? e.detail : "Failed to start Auto-OCR");
    } finally {
      setStarting(false);
    }
  }, [projectUuid, qc]);

  const cancelRun = useCallback(async () => {
    if (!activeJobUuid) return;
    try {
      await api.post(`/ocr/ocr-jobs/${activeJobUuid}/cancel`);
    } catch (e) {
      setStartError(e instanceof ApiError ? e.detail : "Failed to cancel Auto-OCR");
    }
  }, [activeJobUuid]);

  const reset = useCallback(() => {
    setActiveJobUuid(null);
    setStartError(null);
  }, []);

  const status = statusQ.data;
  const isTerminal = status ? TERMINAL_STATES.has(status.state) : false;
  const inProgress = status && !isTerminal;

  const percentage = useMemo(() => {
    if (!status || status.total_pages === 0) return 0;
    return Math.min(100, Math.round((status.processed_count / status.total_pages) * 100));
  }, [status]);

  // ------------------------------------------------------------ idle
  if (!activeJobUuid) {
    const perPageBusy = perPageRunCount > 0;
    return (
      <div className="space-y-1">
        <Button
          size="sm"
          variant="outline"
          onClick={startRun}
          disabled={starting || inFlightQ.isLoading || perPageBusy}
          title={
            perPageBusy
              ? "A per-page Run-OCR is in progress. Wait for it to finish before starting the bulk run."
              : undefined
          }
        >
          {starting ? "Starting…" : "Auto-OCR all pages"}
        </Button>
        {perPageBusy && (
          <p className="text-[10px] text-muted-foreground">
            Per-page OCR in progress — bulk run disabled until it finishes.
          </p>
        )}
        {startError && (
          <p className="text-xs text-destructive">{startError}</p>
        )}
      </div>
    );
  }

  // ------------------------------------------------------------ in-progress / terminal
  return (
    <div className="space-y-1 rounded border bg-muted/30 p-2">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium">
          {inProgress
            ? `Auto-OCR running (${status?.processed_count ?? 0}/${status?.total_pages ?? 0})`
            : status?.state === "completed"
              ? `Auto-OCR complete — ${status.processed_count} processed, ${status.skipped_count} skipped`
              : status?.state === "failed"
                ? `Auto-OCR failed${
                    status.last_error && typeof status.last_error.phase === "string"
                      ? ` (${status.last_error.phase})`
                      : ""
                  }`
                : "Loading…"}
        </span>
        {inProgress && (
          <Button
            size="sm"
            variant="outline"
            onClick={cancelRun}
            disabled={status?.cancel_requested === true}
          >
            {status?.cancel_requested ? "Cancelling…" : "Cancel"}
          </Button>
        )}
        {isTerminal && (
          <Button size="sm" variant="outline" onClick={reset}>
            New run
          </Button>
        )}
      </div>
      {status && status.total_pages > 0 && (
        <div className="h-1 rounded bg-muted overflow-hidden">
          <div
            className={`h-1 transition-all ${
              status.state === "failed"
                ? "bg-red-500"
                : status.state === "completed"
                  ? "bg-emerald-500"
                  : "bg-primary"
            }`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      )}
      {status && status.current_page_index !== null && inProgress && (
        <p className="text-[10px] text-muted-foreground">
          Current page: #{status.current_page_index}
        </p>
      )}
      {status?.last_error && (
        <p className="text-[10px] text-destructive">
          {typeof status.last_error.message === "string"
            ? status.last_error.message
            : JSON.stringify(status.last_error)}
        </p>
      )}
      {startError && (
        <p className="text-[10px] text-destructive">{startError}</p>
      )}
    </div>
  );
}
