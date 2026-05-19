/**
 * Top-of-page header on the segments panel: shows the current OCR
 * review status for the page and exposes the canonical state-machine
 * actions (Sprint 1 §2 / T-4.3.1):
 *
 *   ausstehend → in_review → go | go_with_warning | no_go
 *
 * The "Resolve no-go" surface is the explicit user action — there is no
 * automatic no_go → go path on the backend either (named structural
 * failure mode in DBB Abkürzung 5 / OCR-Review-Status-Kein-Auto-Go-Test).
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

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
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import { qk } from "@/lib/queries";
import type { OcrPageStatus, Page } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUS_LABEL: Record<Page["ocr_status"], string> = {
  ausstehend: "pending",
  in_review: "in review",
  go: "approved",
  go_with_warning: "approved with warning",
  no_go: "blocked",
};

const STATUS_TONE: Record<Page["ocr_status"], string> = {
  ausstehend: "bg-muted text-muted-foreground",
  in_review: "bg-blue-100 text-blue-800",
  go: "bg-emerald-100 text-emerald-800",
  go_with_warning: "bg-amber-100 text-amber-800",
  no_go: "bg-destructive/10 text-destructive",
};

export type ViewMode = "edit" | "compare";

export interface OcrReviewBarProps {
  page: Page;
  projectUuid: string;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}

export function OcrReviewBar({
  page,
  projectUuid,
  viewMode,
  onViewModeChange,
}: OcrReviewBarProps): JSX.Element {
  const qc = useQueryClient();
  const [resolveOpen, setResolveOpen] = useState(false);
  const [resolveNote, setResolveNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const onSuccess = (next: OcrPageStatus): void => {
    qc.setQueryData(qk.page(page.page_uuid), (prev: Page | undefined): Page | undefined =>
      prev ? { ...prev, ocr_status: next.ocr_status } : prev,
    );
    void qc.invalidateQueries({ queryKey: qk.projectPages(projectUuid) });
  };

  const enterMutation = useMutation({
    mutationFn: () =>
      api.post<OcrPageStatus>(`/pages/${page.page_uuid}/ocr-review/enter`),
    onSuccess,
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Failed"),
  });

  // Shared mutationKey lets `OcrAutoRunPanel` detect that a per-page
  // Run-OCR is in flight (via `useIsMutating`) and disable its bulk
  // Start button while this is running.
  const ocrAutoRunMutation = useMutation({
    mutationKey: [...OCR_PAGE_AUTO_RUN_MUTATION_KEY],
    mutationFn: () =>
      api.post<{
        page_uuid: string;
        text: string;
        text_chars: number;
      }>(`/ocr/pages/${page.page_uuid}/auto-run`),
    onSuccess: async () => {
      // Status doesn't change here — page stays `ausstehend` per the
      // canonical separation between OCR run and review state machine.
      // Refresh both the segment list and the per-segment history. The
      // OCR pane resolves source text from history first, so only
      // invalidating `/pages/{u}/segments` can leave the UI showing the
      // previous OCR/source revision even after a successful run.
      await Promise.all([
        qc.invalidateQueries({ queryKey: qk.pageSegments(page.page_uuid) }),
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

  // Is the project-wide bulk auto-run active? If so, refuse the
  // per-page Run-OCR click — the runner row-locks each Page row, so
  // a concurrent per-page click would block at the DB level and just
  // hang the UI. Surfacing the conflict in the button state is
  // clearer than letting the request stall.
  const bulkAutoRunActive = useProjectOcrAutoRunActive(projectUuid);

  const approveAsGoMutation = useMutation({
    mutationFn: () =>
      api.post<OcrPageStatus>(`/pages/${page.page_uuid}/ocr-review/findings`, {
        findings: [],
      }),
    onSuccess,
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Approval failed"),
  });

  const resolveMutation = useMutation({
    mutationFn: (note: string) =>
      api.post<OcrPageStatus>(
        `/pages/${page.page_uuid}/ocr-review/resolve-no-go`,
        { note },
      ),
    onSuccess: (next) => {
      onSuccess(next);
      setResolveOpen(false);
      setResolveNote("");
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Failed"),
  });

  return (
    <div className="sticky top-0 z-10 border-b border-border/80 bg-card px-4 py-4">
      <div className="flex items-baseline justify-between gap-2 mb-2">
        <div>
          <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
            Page {page.page_index}
          </div>
          <div className="font-medium text-[#1d221d]">OCR review</div>
        </div>
        <span
          className={cn(
            "text-xs px-2 py-0.5 rounded-full font-medium",
            STATUS_TONE[page.ocr_status],
          )}
        >
          {STATUS_LABEL[page.ocr_status]}
        </span>
      </div>

      <div className="mt-2 inline-flex overflow-hidden rounded-xl border border-border/80 bg-background">
        <button
          type="button"
          onClick={() => onViewModeChange("edit")}
          className={cn(
            "px-3 py-1 text-xs",
            viewMode === "edit"
              ? "bg-accent text-accent-foreground"
              : "hover:bg-accent/50",
          )}
        >
          Edit
        </button>
        <button
          type="button"
          onClick={() => onViewModeChange("compare")}
          className={cn(
            "px-3 py-1 text-xs border-l",
            viewMode === "compare"
              ? "bg-accent text-accent-foreground"
              : "hover:bg-accent/50",
          )}
        >
          Read
        </button>
      </div>

      <div className="flex flex-wrap gap-2 mt-2">
        {page.ocr_status === "ausstehend" && (
          <>
            <Button
              size="sm"
              onClick={() => {
                setError(null);
                ocrAutoRunMutation.mutate();
              }}
              disabled={ocrAutoRunMutation.isPending || bulkAutoRunActive}
              title={
                bulkAutoRunActive
                  ? "Project-wide Auto-OCR is running. Wait or cancel it before running OCR on a single page."
                  : undefined
              }
            >
              {ocrAutoRunMutation.isPending ? "Running OCR…" : "Run OCR"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setError(null);
                enterMutation.mutate();
              }}
              disabled={enterMutation.isPending}
            >
              {enterMutation.isPending ? "Entering…" : "Enter review"}
            </Button>
          </>
        )}
        {page.ocr_status === "in_review" && (
          <Button
            size="sm"
            onClick={() => {
              setError(null);
              approveAsGoMutation.mutate();
            }}
            disabled={approveAsGoMutation.isPending}
          >
            {approveAsGoMutation.isPending ? "Approving…" : "Approve as GO"}
          </Button>
        )}
        {(page.ocr_status === "go" ||
          page.ocr_status === "go_with_warning" ||
          page.ocr_status === "no_go") && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => enterMutation.mutate()}
            disabled={enterMutation.isPending}
          >
            Re-enter review
          </Button>
        )}
        {page.ocr_status === "no_go" && (
          <Button
            size="sm"
            variant="destructive"
            onClick={() => setResolveOpen(true)}
          >
            Resolve no-go → go
          </Button>
        )}
      </div>

      {error && <p className="text-xs text-destructive mt-2">{error}</p>}

      <Dialog open={resolveOpen} onOpenChange={setResolveOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Resolve no-go to go</DialogTitle>
            <DialogDescription>
              The aggregator never auto-clears a no-go page. This writes a
              Decision Event (decision_source=ocr_review) recording the
              explicit resolution.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            placeholder="Optional note (lands in the Decision-Event content)"
            value={resolveNote}
            onChange={(e) => setResolveNote(e.target.value)}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setResolveOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => resolveMutation.mutate(resolveNote)}
              disabled={resolveMutation.isPending}
            >
              {resolveMutation.isPending ? "Resolving…" : "Resolve"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
