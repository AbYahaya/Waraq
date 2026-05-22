/**
 * Translation pane — page-style target text with protected source popups.
 *
 * The visible workspace is document-like, while the underlying segment
 * UUIDs stay attached as quiet anchors for history, stale-source checks,
 * protected Quran/Hadith provenance, and cross-pane synchronization.
 */

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import { queries, qk, type SegmentHistoryDto } from "@/lib/queries";
import {
  emitSentenceJump,
  formatSentenceId,
  onSentenceJump,
} from "@/lib/sentence-id";
import {
  getLatestProtectedReference,
  getLatestSourceRevision,
  getLatestTranslationRevision,
  isTranslationStale,
  type ProtectedReferenceSummary,
} from "@/lib/segment-history";
import type { Segment } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface TranslationPaneProps {
  pageUuid: string;
  pageIndex: number;
  editable?: boolean;
}

interface TranslationPageEntry {
  segment: Segment;
  history: SegmentHistoryDto | undefined;
  translation: string;
  sourceAvailable: boolean;
  stale: boolean;
  protectedReference: ProtectedReferenceSummary | null;
  sentenceIndexInPage: number;
}

const ORIGIN = "translation";

export function TranslationPane({
  pageUuid,
  pageIndex,
  editable = false,
}: TranslationPaneProps): JSX.Element {
  const segmentsQ = useQuery(queries.pageSegments(pageUuid));
  const histories = useQueries({
    queries: (segmentsQ.data ?? []).map((s) => ({
      ...queries.segmentHistory(s.satz_uuid),
    })),
  });

  const entries = useMemo<TranslationPageEntry[]>(
    () =>
      (segmentsQ.data ?? []).map((segment, i) => {
        const history = histories[i]?.data;
        const translationRevision = getLatestTranslationRevision(history);
        return {
          segment,
          history,
          translation: translationRevision?.text ?? "",
          sourceAvailable: Boolean(getLatestSourceRevision(history)),
          stale: isTranslationStale(history),
          protectedReference: getLatestProtectedReference(history),
          sentenceIndexInPage: i + 1,
        };
      }),
    [histories, segmentsQ.data],
  );

  if (segmentsQ.isLoading) {
    return <p className="text-sm text-muted-foreground p-3">Loading translation page…</p>;
  }
  if (segmentsQ.isError) {
    return <p className="text-sm text-destructive p-3">Failed to load translation.</p>;
  }
  if (!segmentsQ.data || segmentsQ.data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground p-3">
        No OCR anchors yet on this page. Run OCR before translating.
      </p>
    );
  }

  if (editable) {
    return (
      <TranslationPageEditor
        pageUuid={pageUuid}
        pageIndex={pageIndex}
        entries={entries}
      />
    );
  }

  return <TranslationPageReadView pageIndex={pageIndex} entries={entries} />;
}

interface TranslationPageViewProps {
  pageIndex: number;
  entries: TranslationPageEntry[];
}

function TranslationPageReadView({
  pageIndex,
  entries,
}: TranslationPageViewProps): JSX.Element {
  const staleCount = entries.filter((entry) => entry.stale).length;

  return (
    <div className="h-full overflow-auto bg-[#f4efe6] px-3 py-4">
      <article className="mx-auto min-h-full max-w-[54rem] rounded-[1.75rem] border border-[#e7decf] bg-[#fffdf8] px-6 py-8 shadow-sm sm:px-10 sm:py-12">
        <TranslationPageHeader
          pageIndex={pageIndex}
          entries={entries}
          staleCount={staleCount}
          mode="read"
        />

        <div className="mt-8 space-y-5 whitespace-pre-wrap text-left text-[1.03rem] leading-[1.95] text-[#252820]">
          {entries.map((entry) => (
            <TranslationPageAnchor
              key={entry.segment.satz_uuid}
              entry={entry}
              pageIndex={pageIndex}
            >
              <TranslationText entry={entry} />
            </TranslationPageAnchor>
          ))}
        </div>
      </article>
    </div>
  );
}

interface TranslationPageEditorProps {
  pageUuid: string;
  pageIndex: number;
  entries: TranslationPageEntry[];
}

function TranslationPageEditor({
  pageUuid,
  pageIndex,
  entries,
}: TranslationPageEditorProps): JSX.Element {
  const qc = useQueryClient();
  const pageText = useMemo(
    () => entries.map((entry) => entry.translation).join("\n\n"),
    [entries],
  );
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
          api.put<Segment>(`/segments/${entry.segment.satz_uuid}/translation-text`, {
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
        <TranslationPageHeader
          pageIndex={pageIndex}
          entries={entries}
          staleCount={staleCount}
          mode="edit"
        />

        {isLegacyMultiSegment && (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-900">
            This older page still has {entries.length} internal translation anchors. Keep one
            blank line between those text blocks when saving so Waraq can preserve history links.
          </div>
        )}

        <Textarea
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            setError(null);
          }}
          spellCheck
          className="mt-5 min-h-[58vh] flex-1 resize-y rounded-[1.25rem] border-[#d8cdbb] bg-[#fffaf0] px-5 py-5 text-left text-[1rem] leading-[1.9] text-[#252820] shadow-inner"
          aria-label={`Editable translation text for page ${pageIndex}`}
        />

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            onClick={() => saveMutation.mutate(draft)}
            disabled={saveMutation.isPending || draft === pageText}
          >
            {saveMutation.isPending ? "Saving…" : "Save translation page"}
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
            Protected Quran/Hadith source badges remain visible in read mode after saving.
          </span>
        </div>

        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </article>
    </div>
  );
}

interface TranslationPageHeaderProps {
  pageIndex: number;
  entries: TranslationPageEntry[];
  staleCount: number;
  mode: "read" | "edit";
}

function TranslationPageHeader({
  pageIndex,
  entries,
  staleCount,
  mode,
}: TranslationPageHeaderProps): JSX.Element {
  const translatedCount = entries.filter((entry) => entry.translation.trim()).length;
  const protectedCount = entries.filter(
    (entry) => entry.translation.trim() && entry.protectedReference,
  ).length;

  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[#eee5d6] pb-4">
      <div>
        <p className="text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          Translation
        </p>
        <h3 className="mt-1 text-xl font-semibold text-[#1d221d]">Page {pageIndex}</h3>
      </div>
      <div className="flex flex-wrap justify-end gap-2 text-[11px]">
        <span className="rounded-full bg-muted px-2.5 py-1 text-muted-foreground">
          {translatedCount}/{entries.length} translated
        </span>
        {protectedCount > 0 && (
          <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-emerald-800">
            {protectedCount} protected source{protectedCount === 1 ? "" : "s"}
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

interface TranslationPageAnchorProps {
  entry: TranslationPageEntry;
  pageIndex: number;
  children: ReactNode;
}

function TranslationPageAnchor({
  entry,
  pageIndex,
  children,
}: TranslationPageAnchorProps): JSX.Element {
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
        "group relative rounded-xl px-2 py-1 transition-colors hover:bg-emerald-50/50",
        entry.stale && "bg-amber-50/60",
      )}
    >
      <button
        type="button"
        onClick={() => emitSentenceJump({ satzUuid: entry.segment.satz_uuid, origin: ORIGIN })}
        className="absolute -left-1 top-1 rounded-full bg-[#fffaf0] px-2 py-0.5 font-mono text-[9px] uppercase tracking-wide text-muted-foreground opacity-0 shadow-sm transition-opacity hover:text-primary group-hover:opacity-100"
        title="Click to sync all panes to this translation anchor"
      >
        {formatSentenceId(pageIndex, entry.sentenceIndexInPage)}
      </button>
      {children}
    </section>
  );
}

function TranslationText({ entry }: { entry: TranslationPageEntry }): JSX.Element {
  const [referenceOpen, setReferenceOpen] = useState(false);
  const canOpenProtectedReference = Boolean(entry.protectedReference && entry.translation);

  if (!entry.translation) {
    return (
      <p className="text-sm italic text-muted-foreground">
        No translation yet.
      </p>
    );
  }

  return (
    <>
      <p
        className={cn(
          "leading-[1.95]",
          entry.stale && "text-amber-950",
          canOpenProtectedReference &&
            "cursor-pointer underline decoration-dotted underline-offset-4",
        )}
        title={entry.protectedReference?.hoverText}
        onClick={() => {
          if (canOpenProtectedReference) setReferenceOpen(true);
        }}
      >
        {entry.translation}
      </p>

      <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px]">
        {entry.protectedReference && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => setReferenceOpen(true)}
            title={entry.protectedReference.hoverText}
          >
            {entry.protectedReference.badgeLabel}
          </Button>
        )}
        {entry.sourceAvailable && (
          <span className="rounded-full bg-muted px-2 py-0.5 text-muted-foreground">
            Source available
          </span>
        )}
        {entry.stale && (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-800">
            OCR changed after translation
          </span>
        )}
      </div>

      {entry.protectedReference && (
        <ProtectedReferenceDialog
          reference={entry.protectedReference}
          open={referenceOpen}
          onOpenChange={setReferenceOpen}
        />
      )}
    </>
  );
}

interface ProtectedReferenceDialogProps {
  reference: ProtectedReferenceSummary;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function ProtectedReferenceDialog({
  reference,
  open,
  onOpenChange,
}: ProtectedReferenceDialogProps): JSX.Element {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{reference.title}</DialogTitle>
          <DialogDescription>
            {reference.subtitle ?? "Attached from the latest translation provenance."}
          </DialogDescription>
        </DialogHeader>
        {reference.sources.length > 0 ? (
          <ul className="space-y-2 text-sm leading-relaxed text-foreground">
            {reference.sources.map((sourceLine) => (
              <li key={sourceLine} className="rounded-md border bg-muted/30 px-3 py-2">
                {sourceLine}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">
            No protected reference sources were recorded on this translation.
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
}

function splitDraftForSegments(draft: string, expectedCount: number): string[] {
  if (expectedCount <= 1) return [draft];
  const chunks = draft.split(/\n\s*\n/g);
  if (chunks.length !== expectedCount) {
    throw new Error(
      `This page has ${expectedCount} internal translation anchors. Keep exactly one blank line between each block before saving, or rerun OCR/translation so the page becomes one full-page translation block.`,
    );
  }
  return chunks;
}
