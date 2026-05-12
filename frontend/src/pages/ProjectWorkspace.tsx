/**
 * Project workspace — sidebar (pages) + mode-driven main area.
 *
 * Per Dokument 1 §3.7 the main area honors the 5 canonical comparison
 * modes (`<ComparisonModeSelector>`) wired to the `<MultiPaneView>`
 * primitive. The previous "Edit" workspace mode is preserved as a
 * separate toggle that replaces the comparison area with the
 * existing per-segment editor — clicking a sentence ID in the
 * comparison panes broadcasts a cross-pane scroll-sync event.
 */

import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import {
  COMPARISON_MODES,
  ComparisonModeSelector,
  type ComparisonMode,
} from "@/components/ComparisonModeSelector";
import { DifficultyBadge } from "@/components/DifficultyBadge";
import { DpiCompareView } from "@/components/DpiCompareView";
import { GuidedReviewPanel } from "@/components/GuidedReviewPanel";
import { MultiPaneView, type PaneConfig } from "@/components/MultiPaneView";
import { OcrAutoRunPanel } from "@/components/OcrAutoRunPanel";
import { OcrExportDialog } from "@/components/OcrExportDialog";
import { OcrPane } from "@/components/OcrPane";
import { OcrReviewBar } from "@/components/OcrReviewBar";
import { OriginalPane } from "@/components/OriginalPane";
import { PageList } from "@/components/PageList";
import { ReleaseGatePanel } from "@/components/ReleaseGatePanel";
import { SegmentEditor } from "@/components/SegmentEditor";
import { TocPanel } from "@/components/TocPanel";
import { TranslationExportDialog } from "@/components/TranslationExportDialog";
import { TranslationPane } from "@/components/TranslationPane";
import { UploadPdfDialog } from "@/components/UploadPdfDialog";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ApiError } from "@/lib/api";
import { queries } from "@/lib/queries";
import { cn } from "@/lib/utils";

type SinglePane = "original" | "ocr" | "translation";

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

  const [comparisonMode, setComparisonMode] = useState<ComparisonMode>("ocr_translation");
  const [singlePaneSelection, setSinglePaneSelection] = useState<SinglePane>("ocr");
  const [editMode, setEditMode] = useState<boolean>(false);
  const [dpiCompareOpen, setDpiCompareOpen] = useState<boolean>(false);
  const [tocOpen, setTocOpen] = useState<boolean>(false);

  const [uploadOpen, setUploadOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [translateExportOpen, setTranslateExportOpen] = useState(false);
  // Sub-batch O — the bulk OCR mutation is replaced by OcrAutoRunPanel,
  // which polls the new BackgroundTask-driven /ocr/ocr-jobs/{u} endpoint
  // for live progress, survives page refresh, and exposes a Cancel button.

  // Auto-redirect to first page when none is selected.
  useEffect(() => {
    if (pageUuid === undefined && pagesQ.data && pagesQ.data.length > 0) {
      navigate(`/projects/${projectUuid}/pages/${pagesQ.data[0].page_uuid}`, {
        replace: true,
      });
    }
  }, [pageUuid, pagesQ.data, projectUuid, navigate]);

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
      node: <OcrPane pageUuid={pageUuid} pageIndex={idx} />,
    };
    const translation: PaneConfig = {
      id: "translation",
      label: "Translation (German)",
      node: <TranslationPane pageUuid={pageUuid} pageIndex={idx} />,
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
  }, [comparisonMode, singlePaneSelection, pageUuid, pageQ.data]);

  return (
    <div className="-mx-4 -my-8 grid h-[calc(100vh-3.5rem)] grid-cols-[16rem_1fr]">
      <aside className="border-r bg-card overflow-y-auto flex flex-col">
        <div className="px-3 py-3 border-b">
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            Project
          </div>
          <div className="font-medium truncate">{projectQ.data?.name ?? "Loading…"}</div>
          <div className="mt-2">
            <DifficultyBadge scope="project" uuid={projectUuid} />
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            <Button size="sm" variant="outline" onClick={() => setUploadOpen(true)}>
              Upload book, document, image, or archive
            </Button>
            <Button size="sm" variant="outline" onClick={() => setExportOpen(true)}>
              OCR text
            </Button>
            <Button size="sm" onClick={() => setTranslateExportOpen(true)}>
              Translate &amp; export
            </Button>
            <Button size="sm" variant="outline" asChild>
              <Link to={`/projects/${projectUuid}/audit`}>Audit</Link>
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
        defaultPageRange={(pagesQ.data ?? []).map((p) => p.page_index)}
      />
      <TranslationExportDialog
        open={translateExportOpen}
        onOpenChange={setTranslateExportOpen}
        projectUuid={projectUuid}
        projectName={projectQ.data?.name ?? "Waraq Export"}
      />

      <main className="flex flex-col min-h-0">
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
          <>
            <OcrReviewBar
              page={pageQ.data}
              projectUuid={projectUuid}
              viewMode={editMode ? "edit" : "compare"}
              onViewModeChange={(m) => setEditMode(m === "edit")}
            />
            {!editMode && (
              <div className="px-3 py-2 border-b flex flex-wrap items-center gap-3 bg-muted/30">
                <ComparisonModeSelector
                  mode={comparisonMode}
                  onModeChange={setComparisonMode}
                />
                {comparisonMode === "single_fullscreen" && (
                  <SinglePaneSubSelector
                    value={singlePaneSelection}
                    onChange={setSinglePaneSelection}
                  />
                )}
                <Button
                  type="button"
                  size="sm"
                  variant={dpiCompareOpen ? "default" : "outline"}
                  onClick={() => {
                    setDpiCompareOpen((v) => !v);
                    if (tocOpen) setTocOpen(false);
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
                  }}
                  className="text-xs"
                  title="Show the project's auto-detected TOC (AR | DE)"
                >
                  {tocOpen ? "Close TOC" : "TOC"}
                </Button>
                <DifficultyBadge scope="page" uuid={pageUuid} />
                <span className="text-[10px] text-muted-foreground ml-auto">
                  {COMPARISON_MODES.find((m) => m.id === comparisonMode)?.label}
                </span>
              </div>
            )}
            <div className="flex-1 min-h-0">
              {editMode ? (
                <SegmentEditor pageUuid={pageUuid} />
              ) : dpiCompareOpen ? (
                <DpiCompareView pageUuid={pageUuid} />
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

interface SinglePaneSubSelectorProps {
  value: SinglePane;
  onChange: (v: SinglePane) => void;
}

function SinglePaneSubSelector({
  value,
  onChange,
}: SinglePaneSubSelectorProps): JSX.Element {
  const opts: ReadonlyArray<{ id: SinglePane; label: string }> = [
    { id: "original", label: "Original" },
    { id: "ocr", label: "OCR" },
    { id: "translation", label: "Translation" },
  ];
  return (
    <div className="inline-flex rounded border bg-background overflow-hidden" role="tablist">
      {opts.map((o, i) => (
        <button
          key={o.id}
          type="button"
          role="tab"
          aria-selected={value === o.id}
          onClick={() => onChange(o.id)}
          className={cn(
            "px-2 py-1 text-xs",
            i > 0 && "border-l",
            value === o.id ? "bg-accent text-accent-foreground" : "hover:bg-accent/50",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
