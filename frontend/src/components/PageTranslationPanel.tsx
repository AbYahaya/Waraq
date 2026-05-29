import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  OCR_PAGE_AUTO_RUN_MUTATION_KEY,
  useProjectOcrAutoRunActive,
} from "@/components/OcrAutoRunPanel";
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
import { qk, queries } from "@/lib/queries";
import type { Job, Page } from "@/lib/types";

interface TranslationJobPayload {
  chunks_total?: number;
  chunks_translated?: number;
  chunks_processed?: number;
  cancel_requested?: boolean;
}

export interface PageTranslationPanelProps {
  projectUuid: string;
  pageUuid: string;
  pageOcrStatus?: Page["ocr_status"];
}

export function PageTranslationPanel({
  projectUuid,
  pageUuid,
  pageOcrStatus,
}: PageTranslationPanelProps): JSX.Element {
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [translationJob, setTranslationJob] = useState<Job | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState<"translate" | "ocr" | null>(null);
  const segmentsQ = useQuery(queries.pageSegments(pageUuid));

  const segmentUuids = useMemo(
    () => (segmentsQ.data ?? []).map((segment) => segment.satz_uuid),
    [segmentsQ.data],
  );

  const startMutation = useMutation({
    mutationFn: async (): Promise<Job> => {
      await api.post(`/projects/${projectUuid}/release-gate/start-translation`, {
        note: `Page-scoped translation run for ${pageUuid}`,
      });
      const job = await api.post<Job>(`/projects/${projectUuid}/translation-jobs`, {
        segment_uuids: segmentUuids,
      });
      return api.post<Job>(`/translation-jobs/${job.job_uuid}/run`);
    },
    onSuccess: (job) => {
      setError(null);
      setTranslationJob(job);
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.detail : "Could not start page translation"),
  });

  const ocrAutoRunMutation = useMutation({
    mutationKey: [...OCR_PAGE_AUTO_RUN_MUTATION_KEY],
    mutationFn: () =>
      api.post<{
        page_uuid: string;
        text: string;
        text_chars: number;
      }>(`/ocr/pages/${pageUuid}/auto-run`),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: qk.pageSegments(pageUuid) }),
        qc.invalidateQueries({
          predicate: (query) =>
            Array.isArray(query.queryKey) &&
            query.queryKey[0] === "segments" &&
            query.queryKey[2] === "history",
        }),
      ]);
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "OCR failed"),
  });

  const bulkAutoRunActive = useProjectOcrAutoRunActive(projectUuid);
  const isApproved = pageOcrStatus === "go" || pageOcrStatus === "go_with_warning";
  const canRunOcr =
    pageOcrStatus === "ausstehend" ||
    pageOcrStatus === "in_review" ||
    isApproved;

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
      void qc.invalidateQueries({ queryKey: qk.pageSegments(pageUuid) });
      void qc.invalidateQueries({ queryKey: ["segments"] });
    }
  }, [pageUuid, qc, translationJob?.state]);

  const payload = (translationJob?.payload ?? {}) as TranslationJobPayload;
  const chunksTotal = payload.chunks_total ?? segmentUuids.length;
  const chunksProcessed = payload.chunks_processed ?? 0;
  const chunksTranslated = payload.chunks_translated ?? 0;

  const runAction = (action: "translate" | "ocr"): void => {
    setError(null);
    if (action === "translate") {
      startMutation.mutate();
      return;
    }
    ocrAutoRunMutation.mutate();
  };

  const requestAction = (action: "translate" | "ocr"): void => {
    if (isApproved) {
      setPendingAction(action);
      setConfirmOpen(true);
      return;
    }
    runAction(action);
  };

  const confirmContinue = (): void => {
    if (!pendingAction) return;
    runAction(pendingAction);
    setPendingAction(null);
    setConfirmOpen(false);
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      {canRunOcr && (
        <Button
          type="button"
          size="sm"
          disabled={ocrAutoRunMutation.isPending || bulkAutoRunActive}
          title={
            bulkAutoRunActive
              ? "Project-wide Auto-OCR is running. Wait or cancel it before running OCR on a single page."
              : undefined
          }
          onClick={() => requestAction("ocr")}
        >
          {ocrAutoRunMutation.isPending ? "Running OCR…" : "Run OCR"}
        </Button>
      )}
      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={
          startMutation.isPending ||
          isJobActive ||
          segmentsQ.isLoading ||
          segmentUuids.length === 0
        }
        onClick={() => requestAction("translate")}
      >
        {startMutation.isPending || isJobActive
          ? "Translating page…"
          : "Translate this page"}
      </Button>

      {translationJob && (
        <span className="text-xs text-muted-foreground">
          {translationJob.state}
          {chunksTotal > 0 &&
            ` · ${chunksProcessed}/${chunksTotal} processed, ${chunksTranslated} translated`}
        </span>
      )}

      {error && <span className="text-xs text-destructive">{error}</span>}

      <Dialog
        open={confirmOpen}
        onOpenChange={(open) => {
          if (!open) setPendingAction(null);
          setConfirmOpen(open);
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Page already approved</DialogTitle>
            <DialogDescription>
              This page is marked approved. Continuing will still run the selected action.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setPendingAction(null);
                setConfirmOpen(false);
              }}
            >
              Cancel
            </Button>
            <Button type="button" onClick={confirmContinue}>
              Continue
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
