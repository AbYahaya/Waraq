/**
 * OCR pane — page-style Arabic source text with quiet internal anchors.
 *
 * The OCR workspace should read like a scanned page, not a compressed
 * segment table. We still keep each segment UUID attached to its text so
 * history, stale-translation detection, and cross-pane jump sync continue
 * to work.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";

import { ClickableArabic } from "@/components/MorphologyPopover";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import { queries, qk, type SegmentHistoryDto } from "@/lib/queries";
import {
  emitSentenceJump,
  formatSentenceId,
  onSentenceJump,
} from "@/lib/sentence-id";
import {
  getLatestSourceRevision,
  getLatestTranslationRevision,
  isTranslationStale,
} from "@/lib/segment-history";
import type { Segment } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface OcrPaneProps {
  pageUuid: string;
  pageIndex: number;
  editable?: boolean;
}

interface OcrPageEntry {
  segment: Segment;
  history: SegmentHistoryDto | undefined;
  source: string;
  hasTranslation: boolean;
  stale: boolean;
  sentenceIndexInPage: number;
}

const ORIGIN = "ocr";

export function OcrPane({
  pageUuid,
  pageIndex,
  editable = false,
}: OcrPaneProps): JSX.Element {
  const segmentsQ = useQuery(queries.pageSegments(pageUuid));
  const histories = useQueries({
    queries: (segmentsQ.data ?? []).map((s) => ({
      ...queries.segmentHistory(s.satz_uuid),
    })),
  });

  const entries = useMemo<OcrPageEntry[]>(
    () =>
      (segmentsQ.data ?? []).map((segment, i) => {
        const history = histories[i]?.data;
        const sourceRevision = getLatestSourceRevision(history);
        return {
          segment,
          history,
          source: sourceRevision?.text ?? segment.text_content ?? "",
          hasTranslation: Boolean(getLatestTranslationRevision(history)),
          stale: isTranslationStale(history),
          sentenceIndexInPage: i + 1,
        };
      }),
    [histories, segmentsQ.data],
  );

  if (segmentsQ.isLoading) {
    return <p className="text-sm text-muted-foreground p-3">Loading OCR page…</p>;
  }
  if (segmentsQ.isError) {
    return <p className="text-sm text-destructive p-3">Failed to load OCR text.</p>;
  }
  if (!segmentsQ.data || segmentsQ.data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground p-3">
        No OCR text yet on this page. Run OCR to populate it.
      </p>
    );
  }

  if (editable) {
    return <OcrPageEditor pageUuid={pageUuid} pageIndex={pageIndex} entries={entries} />;
  }

  return <OcrPageReadView pageIndex={pageIndex} entries={entries} />;
}

interface OcrPageViewProps {
  pageIndex: number;
  entries: OcrPageEntry[];
}

function OcrPageReadView({ pageIndex, entries }: OcrPageViewProps): JSX.Element {
  const staleCount = entries.filter((entry) => entry.stale).length;

  return (
    <div className="h-full overflow-auto bg-[#f4efe6] px-3 py-4">
      <article className="mx-auto min-h-full max-w-[54rem] rounded-[1.75rem] border border-[#e7decf] bg-[#fffdf8] px-6 py-8 shadow-sm sm:px-10 sm:py-12">
        <OcrPageHeader
          pageIndex={pageIndex}
          entries={entries}
          staleCount={staleCount}
          mode="read"
        />
        <div
          dir="rtl"
          className="mt-8 space-y-5 whitespace-pre-wrap text-right font-arabic text-[1.35rem] leading-[2.35] text-[#1d221d]"
        >
          {entries.map((entry) => (
            <OcrPageAnchor
              key={entry.segment.satz_uuid}
              entry={entry}
              pageIndex={pageIndex}
            >
              <ClickableArabic text={entry.source} />
            </OcrPageAnchor>
          ))}
        </div>
      </article>
    </div>
  );
}

interface OcrPageEditorProps {
  pageUuid: string;
  pageIndex: number;
  entries: OcrPageEntry[];
}

function OcrPageEditor({ pageUuid, pageIndex, entries }: OcrPageEditorProps): JSX.Element {
  const qc = useQueryClient();
  const pageText = useMemo(() => entries.map((entry) => entry.source).join("\n\n"), [entries]);
  const staleCount = entries.filter((entry) => entry.stale).length;
  const [draft, setDraft] = useState(pageText);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDraft(pageText);
    setError(null);
  }, [pageText, pageUuid]);

  const saveMutation = useMutation({
    mutationFn: async (nextText: string) => {
      const chunks = splitDraftForSegments(nextText, entries.length);
      await Promise.all(
        entries.map((entry, i) =>
          api.put<Segment>(`/segments/${entry.segment.satz_uuid}/text`, {
            after_text: chunks[i] ?? "",
          }),
        ),
      );
    },
    onSuccess: async () => {
      setError(null);
      await Promise.all([
        qc.invalidateQueries({ queryKey: qk.pageSegments(pageUuid) }),
        ...entries.map((entry) =>
          qc.invalidateQueries({
            queryKey: ["segments", entry.segment.satz_uuid, "history"],
          }),
        ),
      ]);
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : "Save failed");
      if (err instanceof ApiError) setError(err.detail);
    },
  });

  const isLegacyMultiSegment = entries.length > 1;

  return (
    <div className="h-full overflow-auto bg-[#f4efe6] px-3 py-4">
      <article className="mx-auto flex min-h-full max-w-[54rem] flex-col rounded-[1.75rem] border border-[#e7decf] bg-[#fffdf8] px-4 py-5 shadow-sm sm:px-8 sm:py-8">
        <OcrPageHeader
          pageIndex={pageIndex}
          entries={entries}
          staleCount={staleCount}
          mode="edit"
        />

        {isLegacyMultiSegment && (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-900">
            This older page still has {entries.length} internal OCR anchors. Keep one blank
            line between those text blocks when saving so Waraq can preserve history links.
          </div>
        )}

        <Textarea
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            setError(null);
          }}
          dir="rtl"
          spellCheck={false}
          className="mt-5 min-h-[58vh] flex-1 resize-y rounded-[1.25rem] border-[#d8cdbb] bg-[#fffaf0] px-5 py-5 text-right font-arabic text-[1.3rem] leading-[2.2] text-[#1d221d] shadow-inner"
          aria-label={`Editable OCR text for page ${pageIndex}`}
        />

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            onClick={() => saveMutation.mutate(draft)}
            disabled={saveMutation.isPending || draft === pageText}
          >
            {saveMutation.isPending ? "Saving…" : "Save OCR page"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setDraft(pageText);
              setError(null);
            }}
            disabled={saveMutation.isPending || draft === pageText}
          >
            Reset changes
          </Button>
          <span className="text-xs text-muted-foreground">
            Editing OCR marks existing translation on this page as outdated.
          </span>
        </div>

        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </article>
    </div>
  );
}

interface OcrPageHeaderProps {
  pageIndex: number;
  entries: OcrPageEntry[];
  staleCount: number;
  mode: "read" | "edit";
}

function OcrPageHeader({
  pageIndex,
  entries,
  staleCount,
  mode,
}: OcrPageHeaderProps): JSX.Element {
  const translatedCount = entries.filter((entry) => entry.hasTranslation).length;

  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[#eee5d6] pb-4">
      <div>
        <p className="text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          OCR source
        </p>
        <h3 className="mt-1 text-xl font-semibold text-[#1d221d]">Page {pageIndex}</h3>
      </div>
      <div className="flex flex-wrap justify-end gap-2 text-[11px]">
        <span className="rounded-full bg-muted px-2.5 py-1 text-muted-foreground">
          {entries.length} internal anchor{entries.length === 1 ? "" : "s"}
        </span>
        {translatedCount > 0 && (
          <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-emerald-800">
            {translatedCount} translated
          </span>
        )}
        {staleCount > 0 && (
          <span className="rounded-full bg-amber-100 px-2.5 py-1 text-amber-900">
            {staleCount} outdated translation{staleCount === 1 ? "" : "s"}
          </span>
        )}
        <span className="rounded-full bg-[#113f2b] px-2.5 py-1 text-white">
          {mode === "edit" ? "Page edit" : "Page view"}
        </span>
      </div>
    </header>
  );
}

interface OcrPageAnchorProps {
  entry: OcrPageEntry;
  pageIndex: number;
  children: React.ReactNode;
}

function OcrPageAnchor({ entry, pageIndex, children }: OcrPageAnchorProps): JSX.Element {
  const localRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const unsubscribe = onSentenceJump((detail) => {
      if (detail.origin === ORIGIN) return;
      if (detail.satzUuid !== entry.segment.satz_uuid) return;
      localRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    return unsubscribe;
  }, [entry.segment.satz_uuid]);

  return (
    <section
      ref={localRef}
      data-satz-uuid={entry.segment.satz_uuid}
      className={cn(
        "group relative rounded-xl px-2 py-1 transition-colors hover:bg-amber-50/70",
        entry.stale && "bg-amber-50/50",
      )}
    >
      <button
        type="button"
        onClick={() => emitSentenceJump({ satzUuid: entry.segment.satz_uuid, origin: ORIGIN })}
        className="absolute -left-1 top-1 rounded-full bg-[#fffaf0] px-2 py-0.5 font-mono text-[9px] uppercase tracking-wide text-muted-foreground opacity-0 shadow-sm transition-opacity hover:text-primary group-hover:opacity-100"
        title="Click to sync all panes to this OCR anchor"
      >
        {formatSentenceId(pageIndex, entry.sentenceIndexInPage)}
      </button>
      {children}
    </section>
  );
}

function splitDraftForSegments(draft: string, expectedCount: number): string[] {
  if (expectedCount <= 1) return [draft];
  const chunks = draft.split(/\n\s*\n/g);
  if (chunks.length !== expectedCount) {
    throw new Error(
      `This page has ${expectedCount} internal OCR anchors. Keep exactly one blank line between each block before saving, or rerun OCR so the page becomes one full-page OCR block.`,
    );
  }
  return chunks;
}
