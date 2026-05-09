/**
 * Project workspace: three-pane layout — pages sidebar, scan viewer,
 * segment list. The route accepts an optional `pageUuid` so deep links
 * land directly on a page; without it the workspace shows the project
 * overview and auto-redirects to the first page when one exists.
 */

import { Navigate, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { ComparisonView } from "@/components/ComparisonView";
import { OcrExportDialog } from "@/components/OcrExportDialog";
import { OcrReviewBar, type ViewMode } from "@/components/OcrReviewBar";
import { PageList } from "@/components/PageList";
import { ReleaseGatePanel } from "@/components/ReleaseGatePanel";
import { ScanViewer } from "@/components/ScanViewer";
import { SegmentEditor } from "@/components/SegmentEditor";
import { TranslationExportDialog } from "@/components/TranslationExportDialog";
import { UploadPdfDialog } from "@/components/UploadPdfDialog";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ApiError, api } from "@/lib/api";
import { qk, queries } from "@/lib/queries";

export function ProjectWorkspacePage(): JSX.Element {
  const { projectUuid, pageUuid } = useParams<{
    projectUuid: string;
    pageUuid?: string;
  }>();
  const navigate = useNavigate();

  if (projectUuid === undefined) {
    return <Navigate to="/" replace />;
  }

  const projectQ = useQuery(queries.project(projectUuid));
  const pagesQ = useQuery(queries.projectPages(projectUuid));
  const pageQ = useQuery({
    ...queries.page(pageUuid ?? ""),
    enabled: pageUuid !== undefined,
  });
  const [viewMode, setViewMode] = useState<ViewMode>("edit");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [translateExportOpen, setTranslateExportOpen] = useState(false);
  const [bulkOcrError, setBulkOcrError] = useState<string | null>(null);
  const [bulkOcrResult, setBulkOcrResult] = useState<string | null>(null);
  const qc = useQueryClient();
  const bulkOcrMutation = useMutation({
    mutationFn: () =>
      api.post<{ pages_processed: number; pages_skipped: number }>(
        `/ocr/projects/${projectUuid}/auto-run`,
      ),
    onSuccess: (r) => {
      setBulkOcrError(null);
      setBulkOcrResult(
        `Auto-OCR complete: ${r.pages_processed} processed, ${r.pages_skipped} skipped`,
      );
      void qc.invalidateQueries({ queryKey: qk.projectPages(projectUuid) });
    },
    onError: (err) => {
      setBulkOcrResult(null);
      setBulkOcrError(err instanceof ApiError ? err.detail : "Bulk OCR failed");
    },
  });

  // Auto-redirect to first page when none is selected.
  useEffect(() => {
    if (
      pageUuid === undefined &&
      pagesQ.data &&
      pagesQ.data.length > 0
    ) {
      navigate(`/projects/${projectUuid}/pages/${pagesQ.data[0].page_uuid}`, {
        replace: true,
      });
    }
  }, [pageUuid, pagesQ.data, projectUuid, navigate]);

  return (
    <div className="-mx-4 -my-8 grid h-[calc(100vh-3.5rem)] grid-cols-[16rem_1fr_28rem]">
      <aside className="border-r bg-card overflow-y-auto flex flex-col">
        <div className="px-3 py-3 border-b">
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            Project
          </div>
          <div className="font-medium truncate">
            {projectQ.data?.name ?? "Loading…"}
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            <Button size="sm" variant="outline" onClick={() => setUploadOpen(true)}>
              Upload PDF
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setBulkOcrError(null);
                setBulkOcrResult(null);
                bulkOcrMutation.mutate();
              }}
              disabled={bulkOcrMutation.isPending}
            >
              {bulkOcrMutation.isPending ? "Running OCR…" : "Auto-OCR all pages"}
            </Button>
            <Button size="sm" variant="outline" onClick={() => setExportOpen(true)}>
              OCR text
            </Button>
            <Button size="sm" onClick={() => setTranslateExportOpen(true)}>
              Translate &amp; export
            </Button>
          </div>
          {bulkOcrResult && (
            <p className="text-xs text-emerald-700 mt-2">{bulkOcrResult}</p>
          )}
          {bulkOcrError && (
            <p className="text-xs text-destructive mt-2">{bulkOcrError}</p>
          )}
        </div>
        <ReleaseGatePanel projectUuid={projectUuid} />
        <PageList projectUuid={projectUuid} activePageUuid={pageUuid} />
      </aside>

      <UploadPdfDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        projectUuid={projectUuid}
      />
      <OcrExportDialog
        open={exportOpen}
        onOpenChange={setExportOpen}
        projectUuid={projectUuid}
        defaultPageRange={(pagesQ.data ?? []).map((p) => p.page_index)}
      />
      <TranslationExportDialog
        open={translateExportOpen}
        onOpenChange={setTranslateExportOpen}
        projectUuid={projectUuid}
        projectName={projectQ.data?.name ?? "Waraq Export"}
      />

      <section className="bg-muted/30 min-h-0">
        {pageUuid === undefined && (
          <div className="flex h-full items-center justify-center text-center p-12">
            <div className="max-w-md space-y-2">
              <h2 className="text-lg font-medium">No page selected</h2>
              {pagesQ.data && pagesQ.data.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  Upload a PDF to this project to materialize pages.
                </p>
              )}
            </div>
          </div>
        )}
        {pageUuid !== undefined && pageQ.isError && (
          <div className="flex h-full items-center justify-center text-center p-6">
            <Card className="p-6">
              <p className="text-destructive font-medium">Could not load page</p>
              <p className="text-sm text-muted-foreground mt-2">
                {pageQ.error instanceof ApiError ? pageQ.error.detail : "Unknown error"}
              </p>
            </Card>
          </div>
        )}
        {pageUuid !== undefined && pageQ.data && (
          <ScanViewer pageUuid={pageUuid} pageIndex={pageQ.data.page_index} />
        )}
      </section>

      <aside className="border-l bg-card overflow-y-auto min-h-0">
        {pageUuid !== undefined && pageQ.data ? (
          <>
            <OcrReviewBar
              page={pageQ.data}
              projectUuid={projectUuid}
              viewMode={viewMode}
              onViewModeChange={setViewMode}
            />
            {viewMode === "edit" ? (
              <SegmentEditor pageUuid={pageUuid} />
            ) : (
              <ComparisonView pageUuid={pageUuid} />
            )}
          </>
        ) : (
          <div className="px-3 py-3">
            <div className="text-xs uppercase tracking-wide text-muted-foreground">
              Segments
            </div>
            <p className="text-sm text-muted-foreground mt-2">
              Select a page to see its segments.
            </p>
          </div>
        )}
      </aside>
    </div>
  );
}
