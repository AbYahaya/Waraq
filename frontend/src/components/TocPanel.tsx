/**
 * TOC / IVZ structural review station.
 *
 * The backend currently detects TOC entries from heading blocks and persists
 * heading text edits. This screen wraps that data in the full review workflow:
 * source scan, editable OCR lines, structured table, issue resolution,
 * release gate, export settings, and heading-only style controls.
 */

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Check,
  FileSearch,
  Link2,
  Lock,
  Minus,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  Split,
  ZoomIn,
  ZoomOut,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError, api, apiPath } from "@/lib/api";
import { qk, queries, type TocEntryDto, type TocOcrLineDto } from "@/lib/queries";
import type { ProjectStyleProfile } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

export interface TocPanelProps {
  projectUuid: string;
  className?: string;
}

type ReviewPhase = "structure" | "translation";
type EntryStatus = "verified" | "missing" | "verify" | "mismatch" | "fallback";
type ExportSettings = {
  headerLevel: number;
  chapterLevel: number;
  tocPosition: "front" | "back";
  displayArabic: boolean;
  navigationDepth: number;
};

const BASE_EXPORT_SETTINGS: ExportSettings = {
  headerLevel: 1,
  chapterLevel: 1,
  tocPosition: "front",
  displayArabic: true,
  navigationDepth: 3,
};

const BASE_HEADING_STYLE = {
  heading_font_size_px: 25,
  heading_line_height: 1.35,
  heading_paragraph_spacing_px: 24,
  docx_heading_font_size_pt: 16,
  arabic_font_family: "Amiri",
  docx_arabic_font_family: "Amiri",
};

export function TocPanel({ projectUuid, className }: TocPanelProps): JSX.Element {
  const q = useQuery(queries.projectToc(projectUuid));
  const styleQ = useQuery(queries.projectStyleProfile(projectUuid));
  const qc = useQueryClient();
  const [phase, setPhase] = useState<ReviewPhase>("structure");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [ocrLines, setOcrLines] = useState<EditableTocLine[]>([]);
  const [draftLine, setDraftLine] = useState("");
  const [lineEditing, setLineEditing] = useState(false);
  const [exportSettings, setExportSettings] = useState<ExportSettings>(BASE_EXPORT_SETTINGS);
  const [settingsSaved, setSettingsSaved] = useState<string | null>(null);
  const [redetectMessage, setRedetectMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!q.data) return;
    const entryByLine = new Map(q.data.entries.map((entry) => [entry.line_key, entry]));
    const sourceLines = q.data.ocr_lines.length > 0 ? q.data.ocr_lines : q.data.entries.map(entryToLine);
    const next = sourceLines.map((line) => ({
      key: line.line_key,
      pageUuid: line.page_uuid,
      pageIndex: line.page_index,
      lineNo: line.line_no,
      text: line.text,
      isTocEntry: line.is_toc_entry,
      manual: line.manual,
      protected: line.protected,
      entry: entryByLine.get(line.line_key) ?? null,
    }));
    setOcrLines(next);
    setSelectedKey((current) => current ?? next[0]?.key ?? null);
  }, [q.data]);

  const selectedLine = ocrLines.find((line) => line.key === selectedKey) ?? ocrLines[0] ?? null;
  const selectedEntry = selectedLine?.entry ?? q.data?.entries[0] ?? null;
  const selectedIndex = selectedLine
    ? Math.max(0, ocrLines.findIndex((line) => line.key === selectedLine.key))
    : 0;
  const issueSummary = useMemo(() => {
    if (!q.data) return { blocking: 0, warnings: 0, statuses: new Map<string, EntryStatus>() };
    const statuses = new Map<string, EntryStatus>();
    let blocking = 0;
    let warnings = 0;
    q.data.entries.forEach((entry, index) => {
      const status = entryStatus(entry, q.data.fallback_kind);
      statuses.set(tocEntryKey(entry, index), status);
      statuses.set(entry.line_key, status);
      if (status === "missing" || status === "mismatch") blocking += 1;
      if (status === "verify" || status === "fallback") warnings += 1;
    });
    return { blocking, warnings, statuses };
  }, [q.data]);

  const confirmMutation = useMutation({
    mutationFn: () =>
      api.post<{ decision_event_uuid: string; workflow_state: string }>(
        `/projects/${projectUuid}/toc/confirm`,
        { note: "Confirmed from TOC / IVZ review screen." },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.projectToc(projectUuid) });
    },
  });

  const styleMutation = useMutation({
    mutationFn: (patch: Partial<ProjectStyleProfile>) =>
      api.put<ProjectStyleProfile>(`/projects/${projectUuid}/style-profile`, patch),
    onSuccess: () => {
      setSettingsSaved("Heading style saved to the project export profile.");
      void qc.invalidateQueries({ queryKey: qk.projectStyleProfile(projectUuid) });
    },
  });

  const lineDecisionMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      api.post<{ decision_event_uuid: string; workflow_state: string }>(
        `/projects/${projectUuid}/toc/line-decision`,
        payload,
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.projectToc(projectUuid) });
    },
  });

  const entryDecisionMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      api.post<{ decision_event_uuid: string; workflow_state: string }>(
        `/projects/${projectUuid}/toc/entry-decision`,
        payload,
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.projectToc(projectUuid) });
    },
  });

  const exportSettingsMutation = useMutation({
    mutationFn: (settings: ExportSettings) =>
      api.put<{ decision_event_uuid: string; workflow_state: string }>(
        `/projects/${projectUuid}/toc/export-settings`,
        {
          toc_position: settings.tocPosition,
          header_heading_level: settings.headerLevel,
          chapter_break_heading_level: settings.chapterLevel,
          display_arabic_chapter_headings: settings.displayArabic,
          navigation_depth: settings.navigationDepth,
        },
      ),
    onSuccess: () => {
      setSettingsSaved("TOC export settings saved to the project.");
      void qc.invalidateQueries({ queryKey: qk.projectToc(projectUuid) });
    },
  });

  const redetectMutation = useMutation({
    mutationFn: () =>
      api.post<{ decision_event_uuid: string; workflow_state: string }>(
        `/projects/${projectUuid}/toc/redetect`,
        {},
      ),
    onSuccess: () => {
      setRedetectMessage(
        "Re-detect suggestions refreshed. Manual OCR corrections and confirmed decisions were preserved.",
      );
      void qc.invalidateQueries({ queryKey: qk.projectToc(projectUuid) });
    },
  });

  if (q.isLoading || styleQ.isLoading) {
    return <p className={cn("p-3 text-sm text-muted-foreground", className)}>Loading TOC review...</p>;
  }
  if (q.isError || q.data === undefined) {
    return <p className={cn("p-3 text-sm text-destructive", className)}>Could not load TOC.</p>;
  }

  const canConfirm =
    q.data.page_count > 0 &&
    q.data.confirmation_state !== "confirmed" &&
    issueSummary.blocking === 0;

  const styleProfile = styleQ.data ?? null;

  return (
    <div className={cn("flex h-full min-h-0 flex-col bg-background", className)}>
      <header className="border-b bg-[#fbfaf6] px-4 py-3">
        <div className="flex flex-wrap items-start gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded bg-muted px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                {selectedEntry ? `Page ${selectedEntry.page_index}` : "TOC"}
              </span>
              <h2 className="text-lg font-semibold">TOC / IVZ review</h2>
            </div>
            <p className="mt-1 max-w-3xl text-xs text-muted-foreground">
              Confirm the manuscript structure before translation. Final translated headings
              are reviewed in Step 2 after translation.
            </p>
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <ReleaseBadge blocking={issueSummary.blocking} warnings={issueSummary.warnings} />
            <Button
              size="sm"
              onClick={() => confirmMutation.mutate()}
              disabled={!canConfirm || confirmMutation.isPending}
              title={
                issueSummary.blocking > 0
                  ? "Resolve blocking TOC issues before confirming."
                  : undefined
              }
            >
              <Check className="mr-1 h-4 w-4" />
              {confirmMutation.isPending ? "Confirming..." : "Confirm & Proceed"}
            </Button>
          </div>
        </div>

        <div className="mt-3 grid gap-2 md:grid-cols-2">
          <PhaseCard
            active={phase === "structure"}
            complete={issueSummary.blocking === 0}
            index={1}
            title="Step 1: Structural TOC confirmation"
            detail="Verify OCR accuracy, heading levels, and page links."
            onClick={() => setPhase("structure")}
          />
          <PhaseCard
            active={phase === "translation"}
            complete={q.data.confirmation_state === "confirmed"}
            locked={q.data.confirmation_state !== "confirmed"}
            index={2}
            title="Step 2: Final TOC review"
            detail="Post-translation heading review and manual tweaks."
            onClick={() => setPhase("translation")}
          />
        </div>
      </header>

      <main className="grid min-h-0 flex-1 grid-cols-1 overflow-hidden xl:grid-cols-[minmax(16rem,0.95fr)_minmax(17rem,0.82fr)_minmax(28rem,1.55fr)]">
        <ScanPanel
          selectedEntry={selectedEntry}
          selectedIndex={selectedIndex}
          total={ocrLines.length}
          onPrev={() => setSelectedKey(ocrLines[Math.max(0, selectedIndex - 1)]?.key ?? selectedKey)}
          onNext={() =>
            setSelectedKey(
              ocrLines[Math.min(ocrLines.length - 1, selectedIndex + 1)]?.key ?? selectedKey,
            )
          }
          onRerun={() =>
            redetectMutation.mutate()
          }
          onAreaOcr={() => {
            if (!selectedLine) return;
            window.location.href = `/projects/${projectUuid}?page=${selectedLine.pageUuid}&panel=dpi`;
          }}
        />
        <OcrLinesPanel
          lines={ocrLines}
          selectedKey={selectedLine?.key ?? null}
          draftLine={draftLine}
          editing={lineEditing}
          onSelect={(line) => {
            setSelectedKey(line.key);
            setDraftLine(line.text);
            setLineEditing(false);
          }}
          onDraftChange={setDraftLine}
          onStartEdit={() => {
            if (selectedLine) setDraftLine(selectedLine.text);
            setLineEditing(true);
          }}
          onSave={() => {
            if (!selectedLine) return;
            lineDecisionMutation.mutate({
              action: "correct",
              line_key: selectedLine.key,
              text: draftLine,
            });
            setLineEditing(false);
          }}
          onCancel={() => {
            setDraftLine(selectedLine?.text ?? "");
            setLineEditing(false);
          }}
          onSplit={() => {
            if (!selectedLine) return;
            const midpoint = Math.max(1, Math.floor(selectedLine.text.length / 2));
            const first = selectedLine.text.slice(0, midpoint).trim();
            const second = selectedLine.text.slice(midpoint).trim();
            lineDecisionMutation.mutate({
              action: "split",
              line_key: selectedLine.key,
              first_text: first || selectedLine.text,
              second_text: second,
              new_line_key: `${selectedLine.key}:split:${Date.now()}`,
            });
          }}
          onMerge={() => {
            if (!selectedLine) return;
            const next = ocrLines[selectedIndex + 1];
            if (!next) return;
            lineDecisionMutation.mutate({
              action: "merge_next",
              line_key: selectedLine.key,
            });
          }}
          onToggleToc={(isTocEntry) => {
            if (!selectedLine) return;
            lineDecisionMutation.mutate({
              action: isTocEntry ? "mark_toc" : "mark_not_toc",
              line_key: selectedLine.key,
            });
          }}
          busy={lineDecisionMutation.isPending}
        />
        <StructuredPanel
          projectUuid={projectUuid}
          entries={q.data.entries}
          selectedEntry={selectedEntry}
          selectedLine={selectedLine}
          selectedKey={selectedLine?.key ?? null}
          statuses={issueSummary.statuses}
          fallbackKind={q.data.fallback_kind}
          onSelect={(entry, index) => setSelectedKey(tocEntryKey(entry, index))}
          onAddEntry={(line) =>
            entryDecisionMutation.mutate({
              action: "add_from_source",
              line_key: line.key,
              level: 1,
              ar_text: line.text,
              target_page_index: line.pageIndex,
              target_page_uuid: line.pageUuid,
            })
          }
          onConfirmMatch={(entry) =>
            entryDecisionMutation.mutate({
              action: "confirm_match",
              line_key: entry.line_key,
            })
          }
          onRelinkPage={(entry, pageIndex) =>
            entryDecisionMutation.mutate({
              action: "relink_page",
              line_key: entry.line_key,
              target_page_index: pageIndex,
            })
          }
          onSetLevel={(entry, level) =>
            entryDecisionMutation.mutate({
              action: "set_level",
              line_key: entry.line_key,
              level,
            })
          }
          busy={entryDecisionMutation.isPending}
          redetectMessage={redetectMessage}
          phase={phase}
        />
      </main>

      <footer className="grid border-t bg-[#fbfaf6] lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <ExportSettingsPanel
          settings={exportSettings}
          onChange={setExportSettings}
          onSave={() => exportSettingsMutation.mutate(exportSettings)}
          saving={exportSettingsMutation.isPending}
        />
        <HeadingStylePanel
          profile={styleProfile}
          saving={styleMutation.isPending}
          savedMessage={settingsSaved}
          error={styleMutation.error}
          onSave={(patch) => styleMutation.mutate(patch)}
          onReset={() => styleMutation.mutate(BASE_HEADING_STYLE)}
        />
      </footer>
    </div>
  );
}

interface EditableTocLine {
  key: string;
  pageUuid: string;
  pageIndex: number;
  lineNo: number;
  text: string;
  isTocEntry: boolean;
  manual: boolean;
  protected: boolean;
  entry: TocEntryDto | null;
}

function PhaseCard({
  active,
  complete,
  locked,
  index,
  title,
  detail,
  onClick,
}: {
  active: boolean;
  complete: boolean;
  locked?: boolean;
  index: number;
  title: string;
  detail: string;
  onClick: () => void;
}): JSX.Element {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center gap-3 rounded border p-3 text-left",
        active ? "border-[#0b4a36] bg-white" : "border-border bg-white/60",
      )}
    >
      <span
        className={cn(
          "grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-semibold",
          complete ? "bg-[#0b4a36] text-white" : "bg-muted text-muted-foreground",
        )}
      >
        {locked ? <Lock className="h-3.5 w-3.5" /> : index}
      </span>
      <span>
        <span className="block text-sm font-medium">{title}</span>
        <span className="block text-xs text-muted-foreground">{detail}</span>
      </span>
    </button>
  );
}

function ScanPanel({
  selectedEntry,
  selectedIndex,
  total,
  onPrev,
  onNext,
  onRerun,
  onAreaOcr,
}: {
  selectedEntry: TocEntryDto | null;
  selectedIndex: number;
  total: number;
  onPrev: () => void;
  onNext: () => void;
  onRerun: () => void;
  onAreaOcr: () => void;
}): JSX.Element {
  const [zoom, setZoom] = useState(100);
  const image = useRenderedPage(selectedEntry?.page_uuid ?? null, 160);
  return (
    <section className="flex min-h-0 flex-col border-r">
      <PanelHeader title="Original TOC scan">
        <IconButton label="Zoom out" onClick={() => setZoom((v) => Math.max(70, v - 10))}>
          <ZoomOut className="h-3.5 w-3.5" />
        </IconButton>
        <IconButton label="Zoom in" onClick={() => setZoom((v) => Math.min(180, v + 10))}>
          <ZoomIn className="h-3.5 w-3.5" />
        </IconButton>
      </PanelHeader>
      <div className="min-h-0 flex-1 overflow-auto bg-[#f5f1e8] p-3">
        <div className="mx-auto w-full max-w-sm bg-white p-5 shadow-sm" style={{ width: `${zoom}%` }}>
          {image.error ? (
            <p className="text-xs text-destructive">{image.error}</p>
          ) : image.blobUrl ? (
            <div className="relative">
              <img src={image.blobUrl} alt="TOC source page" className="w-full rounded border" />
              <div
                className="absolute left-2 right-2 rounded border border-[#0b4a36] bg-[#0b4a36]/10"
                style={{ top: `${20 + (selectedIndex % 8) * 8}%`, height: "7%" }}
              />
            </div>
          ) : (
            <p className="p-4 text-center text-xs text-muted-foreground">Rendering scan...</p>
          )}
        </div>
      </div>
      <div className="flex items-center justify-between gap-2 border-t p-2 text-xs">
        <Button size="sm" variant="outline" onClick={onPrev} disabled={selectedIndex <= 0}>
          Previous
        </Button>
        <span className="text-muted-foreground">
          {total === 0 ? "No lines" : `Line ${selectedIndex + 1} of ${total}`}
        </span>
        <Button size="sm" variant="outline" onClick={onNext} disabled={selectedIndex >= total - 1}>
          Next
        </Button>
      </div>
      <div className="flex gap-2 border-t p-2">
        <Button size="sm" variant="outline" onClick={onRerun} className="flex-1">
          <RefreshCw className="mr-1 h-4 w-4" />
          Re-detect TOC
        </Button>
        <Button size="sm" variant="outline" onClick={onAreaOcr} disabled={!selectedEntry}>
          Area OCR
        </Button>
      </div>
    </section>
  );
}

function OcrLinesPanel({
  lines,
  selectedKey,
  draftLine,
  editing,
  onSelect,
  onDraftChange,
  onStartEdit,
  onSave,
  onCancel,
  onSplit,
  onMerge,
  onToggleToc,
  busy,
}: {
  lines: EditableTocLine[];
  selectedKey: string | null;
  draftLine: string;
  editing: boolean;
  onSelect: (line: EditableTocLine) => void;
  onDraftChange: (text: string) => void;
  onStartEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
  onSplit: () => void;
  onMerge: () => void;
  onToggleToc: (isTocEntry: boolean) => void;
  busy: boolean;
}): JSX.Element {
  const selected = lines.find((line) => line.key === selectedKey) ?? null;
  return (
    <section className="flex min-h-0 flex-col border-r">
      <PanelHeader title="OCR text (editable)">
        <span className="text-[10px] text-muted-foreground">Sync</span>
      </PanelHeader>
      <div className="min-h-0 flex-1 overflow-auto">
        {lines.map((line) => (
          <button
            key={line.key}
            type="button"
            onClick={() => onSelect(line)}
            className={cn(
              "grid w-full grid-cols-[2.5rem_minmax(0,1fr)_2rem] items-center gap-2 border-b px-2 py-2 text-left text-sm",
              line.key === selectedKey ? "bg-[#e7f0ef]" : "hover:bg-muted/50",
            )}
          >
            <span className="text-xs font-medium text-muted-foreground">{line.lineNo}</span>
            <span dir="rtl" lang="ar" className="truncate font-arabic">
              {line.text}
            </span>
            <span className="text-[10px] text-muted-foreground">
              {line.protected ? "lock" : line.isTocEntry ? "toc" : "-"}
            </span>
          </button>
        ))}
      </div>
      <div className="border-t p-2">
        {editing ? (
          <>
            <textarea
              dir="rtl"
              lang="ar"
              value={draftLine}
              onChange={(e) => onDraftChange(e.target.value)}
              className="h-20 w-full resize-none rounded border bg-background p-2 text-right font-arabic text-sm"
            />
            <div className="mt-2 flex flex-wrap gap-2">
              <Button size="sm" onClick={onSave} disabled={busy}>
                <Save className="mr-1 h-4 w-4" />
                {busy ? "Saving..." : "Save correction"}
              </Button>
              <Button size="sm" variant="outline" onClick={onCancel}>
                Cancel
              </Button>
            </div>
          </>
        ) : (
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={onStartEdit} disabled={!selected || busy}>
              <Pencil className="mr-1 h-4 w-4" />
              Edit line
            </Button>
            <Button size="sm" variant="outline" onClick={onSplit} disabled={!selected || busy}>
              <Split className="mr-1 h-4 w-4" />
              Split
            </Button>
            <Button size="sm" variant="outline" onClick={onMerge} disabled={!selected || busy}>
              <Minus className="mr-1 h-4 w-4" />
              Merge next
            </Button>
            <Button size="sm" variant="outline" onClick={() => onToggleToc(true)} disabled={!selected || busy}>
              Mark TOC
            </Button>
            <Button size="sm" variant="outline" onClick={() => onToggleToc(false)} disabled={!selected || busy}>
              Not TOC
            </Button>
          </div>
        )}
        <p className="mt-2 text-[10px] text-muted-foreground">
          Manual corrections are protected from re-detect overwrite.
        </p>
      </div>
    </section>
  );
}

function StructuredPanel({
  projectUuid,
  entries,
  selectedEntry,
  selectedLine,
  selectedKey,
  statuses,
  fallbackKind,
  redetectMessage,
  phase,
  onSelect,
  onAddEntry,
  onConfirmMatch,
  onRelinkPage,
  onSetLevel,
  busy,
}: {
  projectUuid: string;
  entries: TocEntryDto[];
  selectedEntry: TocEntryDto | null;
  selectedLine: EditableTocLine | null;
  selectedKey: string | null;
  statuses: Map<string, EntryStatus>;
  fallbackKind: string;
  redetectMessage: string | null;
  phase: ReviewPhase;
  onSelect: (entry: TocEntryDto, index: number) => void;
  onAddEntry: (line: EditableTocLine) => void;
  onConfirmMatch: (entry: TocEntryDto) => void;
  onRelinkPage: (entry: TocEntryDto, pageIndex: number) => void;
  onSetLevel: (entry: TocEntryDto, level: number) => void;
  busy: boolean;
}): JSX.Element {
  return (
    <section className="flex min-h-0 flex-col">
      <PanelHeader title="Structured TOC table">
        <span className="text-[10px] text-emerald-700">{entries.length} detected</span>
        <Button
          size="sm"
          variant="outline"
          disabled={!selectedLine || selectedLine.isTocEntry || busy}
          onClick={() => selectedLine && onAddEntry(selectedLine)}
          title="Create a structured TOC entry from the selected OCR line."
        >
          <Plus className="mr-1 h-4 w-4" />
          Add entry
        </Button>
      </PanelHeader>
      {phase === "translation" && (
        <p className="border-b bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
          Final translated TOC review is available after structural confirmation and translation output.
        </p>
      )}
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full border-collapse text-xs">
          <thead className="sticky top-0 z-10 bg-muted text-left text-[10px] uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-2 py-2">Level</th>
              <th className="px-2 py-2">P.</th>
              <th className="px-2 py-2">Arabic OCR</th>
              <th className="px-2 py-2">Target</th>
              <th className="px-2 py-2">Status</th>
              <th className="px-2 py-2">Translation preview</th>
              <th className="px-2 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry, index) => {
              const key = tocEntryKey(entry, index);
              const status = statuses.get(key) ?? entryStatus(entry, fallbackKind);
              return (
                <tr
                  key={key}
                  className={cn(
                    "border-b",
                    selectedKey === key ? "bg-[#eef5f2]" : "hover:bg-muted/40",
                  )}
                >
                  <td className="px-2 py-2 font-medium">H{entry.level}</td>
                  <td className="px-2 py-2">{entry.target_page_index ?? entry.page_index}</td>
                  <td className="px-2 py-2" dir="rtl" lang="ar">
                    {entry.ar_text || "(empty)"}
                  </td>
                  <td className="px-2 py-2">{entry.page_index}</td>
                  <td className="px-2 py-2">
                    <StatusPill status={status} />
                  </td>
                  <td className="px-2 py-2">{entry.de_text || "(no translation)"}</td>
                  <td className="px-2 py-2">
                    <div className="flex gap-1">
                      <IconButton label="Select row" onClick={() => onSelect(entry, index)}>
                        <FileSearch className="h-3.5 w-3.5" />
                      </IconButton>
                      <EditHeadingButton entry={entry} projectUuid={projectUuid} />
                      <IconButton label="Relink page" onClick={() => onSelect(entry, index)}>
                        <Link2 className="h-3.5 w-3.5" />
                      </IconButton>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <IssueResolutionPanel
        entry={selectedEntry}
        status={selectedEntry ? statuses.get(selectedKey ?? "") ?? entryStatus(selectedEntry, fallbackKind) : null}
        redetectMessage={redetectMessage}
        onConfirmMatch={onConfirmMatch}
        onRelinkPage={onRelinkPage}
        onSetLevel={onSetLevel}
        busy={busy}
      />
    </section>
  );
}

function EditHeadingButton({
  entry,
  projectUuid,
}: {
  entry: TocEntryDto;
  projectUuid: string;
}): JSX.Element {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [arText, setArText] = useState(entry.ar_text);
  const [deText, setDeText] = useState(entry.de_text);
  const mutation = useMutation({
    mutationFn: () =>
      api.put<{ rev_uuid: string; satz_uuid: string }>(`/toc/entries/${entry.satz_uuid}`, {
        ar_text: arText,
        de_text: deText,
      }),
    onSuccess: () => {
      setEditing(false);
      void qc.invalidateQueries({ queryKey: qk.projectToc(projectUuid) });
    },
  });
  if (!editing) {
    return (
      <IconButton label="Edit heading" onClick={() => setEditing(true)} disabled={entry.satz_uuid === null}>
        <Pencil className="h-3.5 w-3.5" />
      </IconButton>
    );
  }
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/30 p-4">
      <div className="w-full max-w-lg rounded border bg-background p-4 shadow-lg">
        <h3 className="text-sm font-semibold">Edit TOC heading</h3>
        <label className="mt-3 block text-xs">
          <span className="text-muted-foreground">Arabic heading</span>
          <input
            dir="rtl"
            value={arText}
            onChange={(e) => setArText(e.target.value)}
            className="mt-1 w-full rounded border bg-background px-2 py-1 text-right font-arabic"
          />
        </label>
        <label className="mt-3 block text-xs">
          <span className="text-muted-foreground">Translation heading preview</span>
          <input
            value={deText}
            onChange={(e) => setDeText(e.target.value)}
            className="mt-1 w-full rounded border bg-background px-2 py-1"
          />
        </label>
        {mutation.error && (
          <p className="mt-2 text-xs text-destructive">
            {mutation.error instanceof ApiError ? mutation.error.detail : "Save failed"}
          </p>
        )}
        <div className="mt-4 flex justify-end gap-2">
          <Button size="sm" variant="outline" onClick={() => setEditing(false)}>
            Cancel
          </Button>
          <Button size="sm" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            {mutation.isPending ? "Saving..." : "Save heading"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function IssueResolutionPanel({
  entry,
  status,
  redetectMessage,
  onConfirmMatch,
  onRelinkPage,
  onSetLevel,
  busy,
}: {
  entry: TocEntryDto | null;
  status: EntryStatus | null;
  redetectMessage: string | null;
  onConfirmMatch: (entry: TocEntryDto) => void;
  onRelinkPage: (entry: TocEntryDto, pageIndex: number) => void;
  onSetLevel: (entry: TocEntryDto, level: number) => void;
  busy: boolean;
}): JSX.Element {
  const [targetPage, setTargetPage] = useState(entry?.target_page_index ?? entry?.page_index ?? 1);
  const [level, setLevel] = useState(entry?.level ?? 1);

  useEffect(() => {
    setTargetPage(entry?.target_page_index ?? entry?.page_index ?? 1);
    setLevel(entry?.level ?? 1);
  }, [entry?.target_page_index, entry?.page_index, entry?.line_key, entry?.level]);

  return (
    <div className="border-t bg-[#fbfaf6] p-3 text-xs">
      <div className="rounded border bg-background p-3">
        <div className="mb-2 flex items-center gap-2">
          <span className="grid h-6 w-6 place-items-center rounded-full border text-muted-foreground">i</span>
          <span className="font-medium">
            {status === "verified" ? "Issue resolution: match verified" : "Issue resolution"}
          </span>
          <span className="ml-auto text-muted-foreground">
            {status ? statusLabel(status) : "No row selected"}
          </span>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <EvidenceBox label="Source evidence (TOC)" text={entry?.ar_text || "(no source text)"} rtl />
          <EvidenceBox
            label={`Target evidence (page ${entry?.target_page_index ?? entry?.page_index ?? "?"} heading)`}
            text={entry?.target_heading || entry?.de_text || "(no translated heading yet)"}
          />
        </div>
        <p className="mt-2 text-muted-foreground">
          {resolutionCopy(status)}
        </p>
        {redetectMessage && (
          <p className="mt-2 rounded border border-emerald-200 bg-emerald-50 p-2 text-emerald-900">
            {redetectMessage}
          </p>
        )}
        <div className="mt-3 flex flex-wrap justify-end gap-2">
          <Button size="sm" variant="outline">Edit heading</Button>
          <label className="flex items-center gap-2 text-muted-foreground">
            Target page
            <input
              type="number"
              min={1}
              value={targetPage}
              onChange={(e) => setTargetPage(Math.max(1, Number(e.target.value)))}
              className="h-8 w-20 rounded border bg-background px-2 text-foreground"
              disabled={!entry || busy}
            />
          </label>
          <label className="flex items-center gap-2 text-muted-foreground">
            Level
            <select
              value={level}
              onChange={(e) => setLevel(Number(e.target.value))}
              className="h-8 rounded border bg-background px-2 text-foreground"
              disabled={!entry || busy}
            >
              {[1, 2, 3, 4, 5, 6].map((item) => (
                <option key={item} value={item}>H{item}</option>
              ))}
            </select>
          </label>
          <Button
            size="sm"
            variant="outline"
            disabled={!entry || busy}
            onClick={() => entry && onSetLevel(entry, level)}
          >
            Save level
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={!entry || busy}
            onClick={() => entry && onRelinkPage(entry, targetPage)}
          >
            Relink page
          </Button>
          <Button size="sm" disabled={!entry || busy} onClick={() => entry && onConfirmMatch(entry)}>
            Confirm match
          </Button>
        </div>
      </div>
    </div>
  );
}

function ExportSettingsPanel({
  settings,
  onChange,
  onSave,
  saving,
}: {
  settings: ExportSettings;
  onChange: (settings: ExportSettings) => void;
  onSave: () => void;
  saving: boolean;
}): JSX.Element {
  return (
    <section className="border-r p-4">
      <div className="mb-3 text-xs font-semibold uppercase tracking-wide">TOC & heading export settings</div>
      <div className="grid gap-3 text-xs md:grid-cols-2">
        <SelectField
          label="Which level appears in running headers?"
          value={settings.headerLevel}
          onChange={(value) => onChange({ ...settings, headerLevel: Number(value) })}
          options={[1, 2, 3, 4, 5, 6].map((level) => ({ value: level, label: `H${level}` }))}
        />
        <SelectField
          label="Navigation depth (bookmarks)"
          value={settings.navigationDepth}
          onChange={(value) => onChange({ ...settings, navigationDepth: Number(value) })}
          options={[1, 2, 3, 4, 5, 6].map((level) => ({ value: level, label: `Up to H${level}` }))}
        />
        <SegmentedLevel
          label="Which level marks chapters?"
          value={settings.chapterLevel}
          onChange={(chapterLevel) => onChange({ ...settings, chapterLevel })}
        />
        <div>
          <div className="mb-1 text-muted-foreground">TOC position</div>
          <div className="grid grid-cols-2 rounded border p-1">
            {(["front", "back"] as const).map((position) => (
              <button
                key={position}
                type="button"
                onClick={() => onChange({ ...settings, tocPosition: position })}
                className={cn(
                  "rounded px-2 py-1",
                  settings.tocPosition === position ? "bg-[#0b4a36] text-white" : "text-muted-foreground",
                )}
              >
                {position === "front" ? "Front" : "Back"}
              </button>
            ))}
          </div>
        </div>
        <label className="flex items-center justify-between gap-3 rounded border p-2 md:col-span-2">
          <span>
            <span className="block font-medium">Include Arabic headings in body text</span>
            <span className="text-muted-foreground">Parallel layout for headings</span>
          </span>
          <input
            type="checkbox"
            checked={settings.displayArabic}
            onChange={(e) => onChange({ ...settings, displayArabic: e.target.checked })}
          />
        </label>
      </div>
      <Button size="sm" className="mt-3" onClick={onSave} disabled={saving}>
        {saving ? "Saving..." : "Save to export profile"}
      </Button>
    </section>
  );
}

function HeadingStylePanel({
  profile,
  saving,
  savedMessage,
  error,
  onSave,
  onReset,
}: {
  profile: ProjectStyleProfile | null;
  saving: boolean;
  savedMessage: string | null;
  error: unknown;
  onSave: (patch: Partial<ProjectStyleProfile>) => void;
  onReset: () => void;
}): JSX.Element {
  const [level, setLevel] = useState(1);
  const [headingSize, setHeadingSize] = useState(profile?.heading_font_size_px ?? 25);
  const [arabicSize, setArabicSize] = useState(profile?.arabic_font_size_px ?? 24);
  const [headingGap, setHeadingGap] = useState(profile?.heading_paragraph_spacing_px ?? 24);

  useEffect(() => {
    if (!profile) return;
    setHeadingSize(profile.heading_font_size_px);
    setArabicSize(profile.arabic_font_size_px);
    setHeadingGap(profile.heading_paragraph_spacing_px);
  }, [profile]);

  return (
    <section className="p-4">
      <div className="mb-3 flex items-center gap-2">
        <div className="text-xs font-semibold uppercase tracking-wide">Heading style customization</div>
        <span className="ml-auto text-[10px] text-muted-foreground">Affects TOC preview, Book Preview, DOCX, and PDF export</span>
      </div>
      <div className="mb-3 grid grid-cols-6 rounded border p-1 text-xs">
        {[1, 2, 3, 4, 5, 6].map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setLevel(item)}
            className={cn("rounded px-2 py-1", level === item ? "bg-[#0b4a36] text-white" : "text-muted-foreground")}
          >
            H{item}
          </button>
        ))}
      </div>
      <div className="grid gap-3 text-xs md:grid-cols-2">
        <StyleInput label="Translation heading size" value={headingSize} onChange={setHeadingSize} suffix="px" />
        <StyleInput label="Arabic heading size" value={arabicSize} onChange={setArabicSize} suffix="px" />
        <StyleInput label="Heading spacing" value={headingGap} onChange={setHeadingGap} suffix="px" />
        <div className="rounded border p-2">
          <div className="mb-1 text-muted-foreground">Preview</div>
          <p style={{ fontSize: headingSize, marginBottom: headingGap / 2 }}>Chapter heading</p>
          <p dir="rtl" lang="ar" style={{ fontSize: arabicSize }} className="font-arabic">
            عنوان الباب
          </p>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button
          size="sm"
          onClick={() =>
            onSave({
              heading_font_size_px: headingSize,
              heading_paragraph_spacing_px: headingGap,
              docx_heading_font_size_pt: Math.max(11, Math.min(24, Math.round(headingSize * 0.65))),
              arabic_font_size_px: arabicSize,
            })
          }
          disabled={saving}
        >
          {saving ? "Saving..." : "Save heading style"}
        </Button>
        <Button size="sm" variant="outline" onClick={onReset} disabled={saving}>
          Reset to baseline
        </Button>
        {savedMessage && <span className="self-center text-xs text-emerald-700">{savedMessage}</span>}
        {error !== null && error !== undefined && (
          <span className="self-center text-xs text-destructive">
            {error instanceof ApiError ? error.detail : "Could not save style"}
          </span>
        )}
      </div>
    </section>
  );
}

function PanelHeader({
  title,
  children,
}: {
  title: string;
  children?: React.ReactNode;
}): JSX.Element {
  return (
    <div className="flex min-h-10 items-center gap-2 border-b bg-muted/30 px-3 py-2">
      <span className="text-xs font-semibold uppercase tracking-wide">{title}</span>
      <span className="ml-auto flex items-center gap-1">{children}</span>
    </div>
  );
}

function IconButton({
  label,
  onClick,
  disabled,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  children: React.ReactNode;
}): JSX.Element {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      disabled={disabled}
      className="grid h-7 w-7 place-items-center rounded border bg-background text-muted-foreground hover:text-foreground disabled:opacity-40"
    >
      {children}
    </button>
  );
}

function EvidenceBox({ label, text, rtl }: { label: string; text: string; rtl?: boolean }): JSX.Element {
  return (
    <div>
      <div className="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div dir={rtl ? "rtl" : "ltr"} lang={rtl ? "ar" : undefined} className="rounded border bg-muted/30 p-2">
        {text}
      </div>
    </div>
  );
}

function ReleaseBadge({ blocking, warnings }: { blocking: number; warnings: number }): JSX.Element {
  const ready = blocking === 0;
  return (
    <div className={cn("rounded border px-3 py-2 text-xs", ready ? "bg-emerald-50 text-emerald-900" : "bg-amber-50 text-amber-900")}>
      <div className="font-semibold">{ready ? "Verified" : "Needs review"}</div>
      <div>{blocking} blocking · {warnings} warning</div>
    </div>
  );
}

function StatusPill({ status }: { status: EntryStatus }): JSX.Element {
  const tone =
    status === "verified"
      ? "bg-emerald-100 text-emerald-900"
      : status === "missing" || status === "mismatch"
        ? "bg-red-100 text-red-900"
        : "bg-amber-100 text-amber-900";
  return <span className={cn("rounded-full px-2 py-1 text-[10px] font-medium", tone)}>{statusLabel(status)}</span>;
}

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string | number;
  options: { value: string | number; label: string }[];
  onChange: (value: string | number) => void;
}): JSX.Element {
  return (
    <label>
      <span className="mb-1 block text-muted-foreground">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 w-full rounded border bg-background px-2"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function SegmentedLevel({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}): JSX.Element {
  return (
    <div>
      <div className="mb-1 text-muted-foreground">{label}</div>
      <div className="grid grid-cols-6 rounded border p-1">
        {[1, 2, 3, 4, 5, 6].map((level) => (
          <button
            key={level}
            type="button"
            onClick={() => onChange(level)}
            className={cn("rounded px-1 py-1", value === level ? "bg-[#0b4a36] text-white" : "text-muted-foreground")}
          >
            H{level}
          </button>
        ))}
      </div>
    </div>
  );
}

function StyleInput({
  label,
  value,
  suffix,
  onChange,
}: {
  label: string;
  value: number;
  suffix: string;
  onChange: (value: number) => void;
}): JSX.Element {
  return (
    <label>
      <span className="mb-1 block text-muted-foreground">{label}</span>
      <div className="flex rounded border">
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="h-9 min-w-0 flex-1 bg-background px-2"
        />
        <span className="grid w-10 place-items-center border-l text-muted-foreground">{suffix}</span>
      </div>
    </label>
  );
}

function useRenderedPage(pageUuid: string | null, dpi: number): { blobUrl: string | null; error: string | null } {
  const token = useAuthStore((s) => s.token);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!pageUuid) {
      setBlobUrl(null);
      setError(null);
      return;
    }
    let revoke: string | null = null;
    let cancelled = false;
    setError(null);
    setBlobUrl(null);
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    fetch(apiPath(`/pages/${pageUuid}/render-png?dpi=${dpi}`), { headers })
      .then(async (resp) => {
        if (!resp.ok) throw new Error(await resp.text());
        return resp.blob();
      })
      .then((blob) => {
        if (cancelled) return;
        const url = URL.createObjectURL(blob);
        revoke = url;
        setBlobUrl(url);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
      if (revoke) URL.revokeObjectURL(revoke);
    };
  }, [pageUuid, dpi, token]);
  return { blobUrl, error };
}

function tocEntryKey(entry: TocEntryDto, index: number): string {
  return entry.line_key || `${entry.page_uuid}:${entry.satz_uuid ?? "fallback"}:${index}`;
}

function entryToLine(entry: TocEntryDto, index: number): TocOcrLineDto {
  return {
    line_key: tocEntryKey(entry, index),
    page_index: entry.page_index,
    page_uuid: entry.page_uuid,
    line_no: index + 1,
    text: entry.ar_text || entry.de_text || `Page ${entry.page_index}`,
    is_toc_entry: entry.is_toc_entry,
    manual: entry.manual,
    protected: entry.protected,
    satz_uuid: entry.satz_uuid,
    block_uuid: entry.block_uuid,
    source_kind: "entry",
  };
}

function entryStatus(entry: TocEntryDto, fallbackKind: string): EntryStatus {
  if (fallbackKind === "page_by_page") return "fallback";
  if (entry.status) return entry.status;
  if (!entry.ar_text.trim()) return "missing";
  if (!entry.de_text.trim()) return "verify";
  return "verified";
}

function statusLabel(status: EntryStatus): string {
  switch (status) {
    case "verified":
      return "Verified";
    case "missing":
      return "Missing";
    case "verify":
      return "Verify";
    case "mismatch":
      return "Mismatch";
    case "fallback":
      return "Fallback";
  }
}

function resolutionCopy(status: EntryStatus | null): string {
  switch (status) {
    case "verified":
      return "The TOC source and target heading are present. Confirm the match or edit the heading if the wording is wrong.";
    case "missing":
      return "The TOC source is missing Arabic text. Correct the OCR line or mark it as not a TOC entry.";
    case "verify":
      return "The Arabic heading is present, but translated heading text is not available yet. This can be finalized in Step 2.";
    case "fallback":
      return "No dedicated TOC heading was detected. Waraq is using page-by-page fallback entries.";
    case "mismatch":
      return "The detected source and target evidence do not align. Relink the target page or edit the heading.";
    default:
      return "Select a TOC row to inspect source evidence, target evidence, and available resolution actions.";
  }
}
