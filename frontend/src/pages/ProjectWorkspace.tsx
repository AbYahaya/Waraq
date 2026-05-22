/**
 * Project workspace — sidebar (pages) + mode-driven main area.
 *
 * The main area uses a grouped Triple / Double / Solo selector while
 * still honoring the canonical comparison panes behind the scenes.
 * The previous "Edit" workspace mode is preserved as a
 * separate toggle that replaces the comparison area with the
 * existing per-segment editor — clicking a sentence ID in the
 * comparison panes broadcasts a cross-pane scroll-sync event.
 */

import { Link, Navigate, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import {
  ComparisonModeSelector,
  comparisonModeLabel,
  type ComparisonMode,
  type SinglePane,
} from "@/components/ComparisonModeSelector";
import { BookPreview } from "@/components/BookPreview";
import { DeleteProjectDialog } from "@/components/DeleteProjectDialog";
import { DifficultyBadge } from "@/components/DifficultyBadge";
import { DpiCompareView } from "@/components/DpiCompareView";
import { GuidedReviewPanel } from "@/components/GuidedReviewPanel";
import { MultiPaneView, type PaneConfig } from "@/components/MultiPaneView";
import { OcrAutoRunPanel } from "@/components/OcrAutoRunPanel";
import { OcrExportDialog } from "@/components/OcrExportDialog";
import { OcrPane } from "@/components/OcrPane";
import { OcrReviewBar } from "@/components/OcrReviewBar";
import { PageTranslationPanel } from "@/components/PageTranslationPanel";
import { OriginalPane } from "@/components/OriginalPane";
import { PageList } from "@/components/PageList";
import { ReleaseGatePanel } from "@/components/ReleaseGatePanel";
import { TocPanel } from "@/components/TocPanel";
import { TranslationExportDialog } from "@/components/TranslationExportDialog";
import { TranslationPane } from "@/components/TranslationPane";
import { UploadPdfDialog } from "@/components/UploadPdfDialog";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ApiError } from "@/lib/api";
import { queries } from "@/lib/queries";

export function ProjectWorkspacePage(): JSX.Element {
  const { projectUuid, pageUuid } = useParams<{
    projectUuid: string;
    pageUuid?: string;
  }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  if (projectUuid === undefined) {
    return <Navigate to="/" replace />;
  }

  const projectQ = useQuery(queries.project(projectUuid));
  const pagesQ = useQuery(queries.projectPages(projectUuid));
  const logicalPages = useMemo(() => dedupePagesByIndex(pagesQ.data ?? []), [pagesQ.data]);
  const pageQ = useQuery({
    ...queries.page(pageUuid ?? ""),
    enabled: pageUuid !== undefined,
  });

  const [comparisonMode, setComparisonMode] = useState<ComparisonMode>("ocr_translation");
  const [singlePaneSelection, setSinglePaneSelection] = useState<SinglePane>("ocr");
  const [editMode, setEditMode] = useState<boolean>(false);
  const [dpiCompareOpen, setDpiCompareOpen] = useState<boolean>(false);
  const [tocOpen, setTocOpen] = useState<boolean>(false);
  const [bookPreviewOpen, setBookPreviewOpen] = useState<boolean>(false);

  const [uploadOpen, setUploadOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [translateExportOpen, setTranslateExportOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  // Sub-batch O — the bulk OCR mutation is replaced by OcrAutoRunPanel,
  // which polls the new BackgroundTask-driven /ocr/ocr-jobs/{u} endpoint
  // for live progress, survives page refresh, and exposes a Cancel button.

  // Auto-redirect to first page when none is selected.
  useEffect(() => {
    if (pageUuid === undefined && logicalPages.length > 0) {
      navigate(`/projects/${projectUuid}/pages/${logicalPages[0].page_uuid}`, {
        replace: true,
      });
    }
  }, [pageUuid, logicalPages, projectUuid, navigate]);

  useEffect(() => {
    if (searchParams.get("panel") !== "dpi") return;
    setDpiCompareOpen(true);
    setTocOpen(false);
    setBookPreviewOpen(false);
  }, [searchParams]);

  const panes = useMemo<PaneConfig[]>(() => {
    if (pageUuid === undefined || pageQ.data === undefined) return [];
    const idx = pageQ.data.page_index;
    const original: PaneConfig = {
      id: "original",
      label: "Original (scan)",
      node: <OriginalPane pageUuid={pageUuid} pageIndex={idx} />,
    };
    const ocr: PaneConfig = {
      id: "ocr",
      label: "OCR (Arabic)",
      node: (
        <OcrPane
          pageUuid={pageUuid}
          pageIndex={idx}
          projectUuid={projectUuid}
          editable={editMode}
        />
      ),
    };
    const translation: PaneConfig = {
      id: "translation",
      label: "Translation",
      node: (
        <TranslationPane
          pageUuid={pageUuid}
          pageIndex={idx}
          projectUuid={projectUuid}
          editable={editMode}
          styleControlsEnabled={
            comparisonMode === "single_fullscreen" && singlePaneSelection === "translation"
          }
        />
      ),
    };

    switch (comparisonMode) {
      case "original_ocr":
        return [original, ocr];
      case "original_translation":
        return [original, translation];
      case "ocr_translation":
        return [ocr, translation];
      case "triple":
        return [original, ocr, translation];
      case "single_fullscreen": {
        const map: Record<SinglePane, PaneConfig> = {
          original,
          ocr,
          translation,
        };
        return [map[singlePaneSelection]];
      }
    }
  }, [comparisonMode, editMode, singlePaneSelection, pageUuid, pageQ.data, projectUuid]);

  return (
    <div className="grid h-full min-h-0 grid-cols-1 gap-4 xl:grid-cols-[20rem_minmax(0,1fr)]">
      <aside className="flex min-h-0 flex-col overflow-hidden rounded-[2rem] border border-border/80 bg-card/95 shadow-sm">
        <div className="border-b border-border/80 px-4 py-4">
          <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
            Project
          </div>
          <div className="mt-2 truncate text-lg font-semibold text-[#1d221d]">
            {projectQ.data?.name ?? "Loading…"}
          </div>
          <div className="mt-3">
            <DifficultyBadge scope="project" uuid={projectUuid} projectUuid={projectUuid} />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button size="sm" variant="outline" className="rounded-xl" onClick={() => setUploadOpen(true)}>
              Upload book, document, image, or archive
            </Button>
            <Button size="sm" variant="outline" className="rounded-xl" onClick={() => setExportOpen(true)}>
              OCR text
            </Button>
            <Button size="sm" className="rounded-xl" onClick={() => setTranslateExportOpen(true)}>
              Translate &amp; export
            </Button>
            <Button size="sm" variant="outline" className="rounded-xl" asChild>
              <Link to={`/projects/${projectUuid}/audit`}>Audit</Link>
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="rounded-xl text-destructive border-destructive/40 hover:bg-destructive/10"
              onClick={() => setDeleteOpen(true)}
              title="Hide this project from your projects list. Server-side this is inactivation (H-5); data is preserved."
            >
              Delete
            </Button>
          </div>
          <div className="mt-2">
            <OcrAutoRunPanel projectUuid={projectUuid} />
          </div>
        </div>
        <ReleaseGatePanel projectUuid={projectUuid} />
        <GuidedReviewPanel projectUuid={projectUuid} />
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
        defaultPageRange={logicalPages.map((p) => p.page_index)}
      />
      <TranslationExportDialog
        open={translateExportOpen}
        onOpenChange={setTranslateExportOpen}
        projectUuid={projectUuid}
        projectName={projectQ.data?.name ?? "Waraq Export"}
      />
      <DeleteProjectDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        projectUuid={projectUuid}
        projectName={projectQ.data?.name ?? "this project"}
      />

      <main className="flex min-h-0 flex-col overflow-hidden rounded-[2rem] border border-border/80 bg-card/95 shadow-sm">
        {pageUuid === undefined && (
          <div className="flex h-full items-center justify-center text-center p-12">
            <div className="max-w-md space-y-2">
              <h2 className="text-lg font-medium">No page selected</h2>
              {pagesQ.data && logicalPages.length === 0 && (
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
          <>
            <OcrReviewBar
              page={pageQ.data}
              projectUuid={projectUuid}
              viewMode={editMode ? "edit" : "compare"}
              onViewModeChange={(m) => setEditMode(m === "edit")}
            />
            <div className="flex flex-wrap items-center gap-3 border-b border-border/80 bg-muted/20 px-4 py-3">
              <ComparisonModeSelector
                mode={comparisonMode}
                onModeChange={setComparisonMode}
                singlePane={singlePaneSelection}
                onSinglePaneChange={setSinglePaneSelection}
              />
              <Button
                type="button"
                size="sm"
                variant={dpiCompareOpen ? "default" : "outline"}
                onClick={() => {
                  setDpiCompareOpen((v) => !v);
                  if (tocOpen) setTocOpen(false);
                  if (bookPreviewOpen) setBookPreviewOpen(false);
                }}
                className="text-xs"
                title="Render this page at low + high DPI side-by-side"
              >
                {dpiCompareOpen ? "Close DPI compare" : "DPI compare"}
              </Button>
              <Button
                type="button"
                size="sm"
                variant={tocOpen ? "default" : "outline"}
                onClick={() => {
                  setTocOpen((v) => !v);
                  if (dpiCompareOpen) setDpiCompareOpen(false);
                  if (bookPreviewOpen) setBookPreviewOpen(false);
                }}
                className="text-xs"
                title="Show the project's auto-detected table of contents"
              >
                {tocOpen ? "Close TOC" : "TOC"}
              </Button>
              <Button
                type="button"
                size="sm"
                variant={bookPreviewOpen ? "default" : "outline"}
                onClick={() => {
                  setBookPreviewOpen((v) => !v);
                  if (dpiCompareOpen) setDpiCompareOpen(false);
                  if (tocOpen) setTocOpen(false);
                }}
                className="text-xs"
                title="Preview the project as a styled book before export"
              >
                {bookPreviewOpen ? "Close book preview" : "Book preview"}
              </Button>
              <DifficultyBadge scope="page" uuid={pageUuid} projectUuid={projectUuid} />
              <PageTranslationPanel projectUuid={projectUuid} pageUuid={pageUuid} />
              <span className="text-[10px] text-muted-foreground ml-auto">
                {editMode ? "Edit mode" : "Read mode"} ·{" "}
                {comparisonModeLabel(comparisonMode, singlePaneSelection)}
              </span>
            </div>
            <div className="flex-1 min-h-0">
              {bookPreviewOpen ? (
                <BookPreview
                  projectUuid={projectUuid}
                  projectName={projectQ.data?.name ?? "Waraq Export"}
                />
              ) : dpiCompareOpen ? (
                <DpiCompareView pageUuid={pageUuid} projectUuid={projectUuid} />
              ) : tocOpen ? (
                <TocPanel projectUuid={projectUuid} />
              ) : (
                <MultiPaneView panes={panes} />
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}

function dedupePagesByIndex<T extends { page_index: number }>(pages: T[]): T[] {
  const seen = new Set<number>();
  return pages.filter((page) => {
    if (seen.has(page.page_index)) return false;
    seen.add(page.page_index);
    return true;
  });
}
