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
  attentionReturnUrl?: string | null;
}

export function OcrReviewBar({
  page,
  projectUuid,
  viewMode,
  onViewModeChange,
  attentionReturnUrl,
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
    void qc.invalidateQueries({ queryKey: qk.releaseGate(projectUuid) });
    void qc.invalidateQueries({ queryKey: qk.guidedReviewQueue(projectUuid) });
    void qc.invalidateQueries({
      predicate: (query) =>
        Array.isArray(query.queryKey) &&
        (query.queryKey[0] === "audit" || query.queryKey[0] === "difficulty"),
    });
  };

  const enterMutation = useMutation({
    mutationFn: () =>
      api.post<OcrPageStatus>(`/pages/${page.page_uuid}/ocr-review/enter`),
    onSuccess,
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Failed"),
  });

  const approveAsGoMutation = useMutation({
    mutationFn: () =>
      api.post<OcrPageStatus>(`/pages/${page.page_uuid}/ocr-review/approve-go`, {
        note: "Approved from project workspace.",
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
    <div className="sticky top-0 z-20 border-b border-border/80 bg-card/95 px-4 py-2.5 backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            Page {page.page_index}
          </div>
          <div className="text-sm font-medium text-[#1d221d]">OCR review</div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={cn(
              "text-xs px-2 py-0.5 rounded-full font-medium",
              STATUS_TONE[page.ocr_status],
            )}
          >
            {STATUS_LABEL[page.ocr_status]}
          </span>
          <div className="inline-flex overflow-hidden rounded-xl border border-border/80 bg-background">
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
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mt-2">
        {page.ocr_status === "ausstehend" && (
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
        {attentionReturnUrl && (
          <Button size="sm" variant="outline" asChild>
            <a href={attentionReturnUrl}>Back to attention item</a>
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
