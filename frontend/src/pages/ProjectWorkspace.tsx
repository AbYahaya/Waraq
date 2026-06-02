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

import { Navigate, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo } from "react";

import {
  ComparisonModeSelector,
  comparisonModeLabel,
  type ComparisonMode,
  type SinglePane,
} from "@/components/ComparisonModeSelector";
import { BookPreview } from "@/components/BookPreview";
import { DpiCompareView } from "@/components/DpiCompareView";
import { MultiPaneView, type PaneConfig } from "@/components/MultiPaneView";
import { OcrPane } from "@/components/OcrPane";
import { OcrReviewBar } from "@/components/OcrReviewBar";
import { PageTranslationPanel } from "@/components/PageTranslationPanel";
import { OriginalPane } from "@/components/OriginalPane";
import { ProjectWorkspaceSidebar } from "@/components/ProjectWorkspaceSidebar";
import { TocPanel } from "@/components/TocPanel";
import { TranslationPane } from "@/components/TranslationPane";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ApiError } from "@/lib/api";
import { queries } from "@/lib/queries";
import { rememberWorkspaceUrl } from "@/lib/workspace-memory";

export function ProjectWorkspacePage(): JSX.Element {
  const { projectUuid, pageUuid } = useParams<{
    projectUuid: string;
    pageUuid?: string;
  }>();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();

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

  const comparisonMode = parseComparisonMode(searchParams.get("view"));
  const singlePaneSelection = parseSinglePane(searchParams.get("pane"));
  const editMode = searchParams.get("edit") === "1";
  const activePanel = searchParams.get("panel");
  const dpiCompareOpen = activePanel === "dpi";
  const tocOpen = activePanel === "toc";
  const bookPreviewOpen = activePanel === "book";

  const updateWorkspaceSearch = (updates: Record<string, string | null>): void => {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(updates)) {
      setOrDelete(next, key, value);
    }
    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true });
    }
  };

  const setComparisonMode = (mode: ComparisonMode): void => {
    updateWorkspaceSearch({
      view: mode === "ocr_translation" ? null : mode,
      pane: mode === "single_fullscreen" ? singlePaneSelection : null,
    });
  };

  const setSinglePaneSelection = (pane: SinglePane): void => {
    updateWorkspaceSearch({
      view: "single_fullscreen",
      pane,
    });
  };

  const setEditMode = (nextEditMode: boolean): void => {
    updateWorkspaceSearch({ edit: nextEditMode ? "1" : null });
  };

  const setActivePanel = (panel: "book" | "dpi" | "toc" | null): void => {
    updateWorkspaceSearch({ panel });
  };

  // Sub-batch O — the bulk OCR mutation is replaced by OcrAutoRunPanel,
  // which polls the new BackgroundTask-driven /ocr/ocr-jobs/{u} endpoint
  // for live progress, survives page refresh, and exposes a Cancel button.

  // Auto-redirect to first page when none is selected.
  useEffect(() => {
    if (pageUuid === undefined && logicalPages.length > 0) {
      const qs = searchParams.toString();
      navigate(
        `/projects/${projectUuid}/pages/${logicalPages[0].page_uuid}${qs ? `?${qs}` : ""}`,
        { replace: true },
      );
    }
  }, [pageUuid, logicalPages, projectUuid, navigate, searchParams]);

  useEffect(() => {
    rememberWorkspaceUrl(`${location.pathname}${location.search}`);
  }, [location.pathname, location.search]);

  const attentionReturnUrl = useMemo(() => {
    if (searchParams.get("from") !== "attention") return null;
    const focus = searchParams.get("focus");
    const params = new URLSearchParams();
    params.set("tab", "active");
    if (focus) params.set("focus", focus);
    return `/projects/${projectUuid}/audit?${params.toString()}`;
  }, [projectUuid, searchParams]);
  const attentionFocus = searchParams.get("focus");
  const attentionIssue = searchParams.get("issue");
  const attentionIssueUuid = searchParams.get("issue_uuid");

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
            editMode && comparisonMode === "single_fullscreen" && singlePaneSelection === "translation"
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
    <div className="flex h-full min-h-0 flex-col gap-4 overflow-y-auto">
      <ProjectWorkspaceSidebar
        projectUuid={projectUuid}
        activePageUuid={pageUuid}
        className="h-[42rem] max-h-[calc(100vh-8rem)] lg:hidden"
      />

      <main className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[2rem] border border-border/80 bg-card/95 shadow-sm">
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
              attentionReturnUrl={attentionReturnUrl}
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
                onClick={() => setActivePanel(dpiCompareOpen ? null : "dpi")}
                className="text-xs"
                title="Render this page at low + high DPI side-by-side"
              >
                {dpiCompareOpen ? "Close DPI compare" : "DPI compare"}
              </Button>
              <Button
                type="button"
                size="sm"
                variant={tocOpen ? "default" : "outline"}
                onClick={() => setActivePanel(tocOpen ? null : "toc")}
                className="text-xs"
                title="Show the project's auto-detected table of contents"
              >
                {tocOpen ? "Close TOC" : "TOC"}
              </Button>
              <Button
                type="button"
                size="sm"
                variant={bookPreviewOpen ? "default" : "outline"}
                onClick={() => setActivePanel(bookPreviewOpen ? null : "book")}
                className="text-xs"
                title="Preview the project as a styled book before export"
              >
                {bookPreviewOpen ? "Close book preview" : "Book preview"}
              </Button>
              <PageTranslationPanel
                projectUuid={projectUuid}
                pageUuid={pageUuid}
                pageOcrStatus={pageQ.data?.ocr_status}
              />
              <span className="text-[10px] text-muted-foreground ml-auto">
                {editMode ? "Edit mode" : "Read mode"} ·{" "}
                {comparisonModeLabel(comparisonMode, singlePaneSelection)}
              </span>
            </div>
            <div className="flex-1 min-h-0 overflow-hidden">
              {bookPreviewOpen ? (
                <BookPreview
                  projectUuid={projectUuid}
                  projectName={projectQ.data?.name ?? "Waraq Export"}
                />
              ) : dpiCompareOpen ? (
                <DpiCompareView
                  pageUuid={pageUuid}
                  projectUuid={projectUuid}
                  sourceIssueLabel={attentionIssue}
                  sourceIssueRef={attentionFocus}
                  sourceIssueUuid={attentionIssueUuid}
                  attentionReturnUrl={attentionReturnUrl}
                />
              ) : tocOpen ? (
                <TocPanel projectUuid={projectUuid} />
              ) : (
                <MultiPaneView panes={panes} className="h-full min-h-0" />
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

function parseComparisonMode(value: string | null): ComparisonMode {
  switch (value) {
    case "original_ocr":
    case "original_translation":
    case "ocr_translation":
    case "triple":
    case "single_fullscreen":
      return value;
    default:
      return "ocr_translation";
  }
}

function parseSinglePane(value: string | null): SinglePane {
  switch (value) {
    case "original":
    case "ocr":
    case "translation":
      return value;
    default:
      return "ocr";
  }
}

function setOrDelete(params: URLSearchParams, key: string, value: string | null): void {
  if (value === null || value === "") {
    params.delete(key);
    return;
  }
  params.set(key, value);
}
