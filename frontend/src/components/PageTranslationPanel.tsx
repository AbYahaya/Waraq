import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";
import { qk, queries } from "@/lib/queries";
import type { Job } from "@/lib/types";

interface TranslationJobPayload {
  chunks_total?: number;
  chunks_translated?: number;
  chunks_processed?: number;
  cancel_requested?: boolean;
}

export interface PageTranslationPanelProps {
  projectUuid: string;
  pageUuid: string;
}

export function PageTranslationPanel({
  projectUuid,
  pageUuid,
}: PageTranslationPanelProps): JSX.Element {
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [translationJob, setTranslationJob] = useState<Job | null>(null);
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

  return (
    <div className="flex flex-wrap items-center gap-2">
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
        onClick={() => {
          setError(null);
          startMutation.mutate();
        }}
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
    </div>
  );
}
