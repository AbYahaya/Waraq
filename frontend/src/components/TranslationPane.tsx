/**
 * §3.7 Translation pane — German (target-language) text with canonical
 * Sentence IDs.
 *
 * Reads the page's segments + each segment's history and shows the
 * LATEST `change_source = "re_translate"` revision's `after_text` as
 * the translation. When a segment hasn't been translated yet the row
 * shows a muted placeholder. Click-to-jump synchronizes other panes.
 */

import { useEffect, useState } from "react";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";

import { SentenceRow } from "@/components/SentenceRow";
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
import { queries, type SegmentHistoryDto } from "@/lib/queries";
import type { Segment } from "@/lib/types";
import {
  getLatestProtectedReference,
  getLatestSourceRevision,
  getLatestTranslationRevision,
  isTranslationStale,
} from "@/lib/segment-history";
import { qk } from "@/lib/queries";
import { cn } from "@/lib/utils";

export interface TranslationPaneProps {
  pageUuid: string;
  pageIndex: number;
  editable?: boolean;
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

  if (segmentsQ.isLoading) {
    return <p className="text-sm text-muted-foreground p-3">Loading…</p>;
  }
  if (segmentsQ.isError) {
    return <p className="text-sm text-destructive p-3">Failed to load segments.</p>;
  }
  if (!segmentsQ.data || segmentsQ.data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground p-3">No segments yet on this page.</p>
    );
  }

  return (
    <ol>
      {segmentsQ.data.map((seg, i) => {
        const history = histories[i]?.data;
        return (
          <TranslationRow
            key={seg.satz_uuid}
            segment={seg}
            history={history}
            pageIndex={pageIndex}
            sentenceIndexInPage={i + 1}
            pageUuid={pageUuid}
            editable={editable}
          />
        );
      })}
    </ol>
  );
}

interface TranslationRowProps {
  segment: Segment;
  history: SegmentHistoryDto | undefined;
  pageIndex: number;
  sentenceIndexInPage: number;
  pageUuid: string;
  editable: boolean;
}

function TranslationRow({
  segment,
  history,
  pageIndex,
  sentenceIndexInPage,
  pageUuid,
  editable,
}: TranslationRowProps): JSX.Element {
  const qc = useQueryClient();
  const translationRevision = getLatestTranslationRevision(history);
  const sourceRevision = getLatestSourceRevision(history);
  const protectedReference = getLatestProtectedReference(history);
  const stale = isTranslationStale(history);
  const translation = translationRevision?.text ?? "";
  const canOpenProtectedReference = Boolean(protectedReference && translation);
  const [editing, setEditing] = useState(false);
  const [referenceOpen, setReferenceOpen] = useState(false);
  const [draft, setDraft] = useState(translation);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!editing) setDraft(translation);
  }, [translation, editing]);

  const saveMutation = useMutation({
    mutationFn: (after_text: string) =>
      api.put<Segment>(`/segments/${segment.satz_uuid}/translation-text`, { after_text }),
    onSuccess: async () => {
      setEditing(false);
      setError(null);
      await Promise.all([
        qc.invalidateQueries({ queryKey: qk.pageSegments(pageUuid) }),
        qc.invalidateQueries({ queryKey: ["segments", segment.satz_uuid, "history"] }),
      ]);
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Save failed"),
  });

  return (
    <SentenceRow
      satzUuid={segment.satz_uuid}
      pageIndex={pageIndex}
      sentenceIndexInPage={sentenceIndexInPage}
      origin={ORIGIN}
    >
      <div className="space-y-2">
        {editing ? (
          <div className="space-y-2">
            <Textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="min-h-[112px] text-sm leading-relaxed"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <Button size="sm" variant="ghost" onClick={() => {
                setEditing(false);
                setDraft(translation);
                setError(null);
              }}>
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  setError(null);
                  saveMutation.mutate(draft);
                }}
                disabled={saveMutation.isPending}
              >
                {saveMutation.isPending ? "Saving…" : "Save translation"}
              </Button>
            </div>
          </div>
        ) : translation ? (
          <p
            className={cn(
              "text-sm leading-relaxed",
              stale && "text-amber-900",
              editable && "cursor-text",
              canOpenProtectedReference && "cursor-pointer underline decoration-dotted underline-offset-4",
            )}
            title={protectedReference?.hoverText}
            onClick={() => {
              if (canOpenProtectedReference) setReferenceOpen(true);
            }}
            onDoubleClick={() => {
              if (editable && !canOpenProtectedReference) setEditing(true);
            }}
          >
            {translation}
          </p>
        ) : (
          <p className="text-sm text-muted-foreground italic">
            No translation yet.
          </p>
        )}

        <div className="flex flex-wrap items-center gap-2 text-[11px]">
          {editable && !editing && (
            <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
              {translation ? "Edit translation" : "Add translation"}
            </Button>
          )}
          {protectedReference && translation && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setReferenceOpen(true)}
              title={protectedReference.hoverText}
            >
              {protectedReference.badgeLabel}
            </Button>
          )}
          {sourceRevision && (
            <span className="rounded-full bg-muted px-2 py-0.5 text-muted-foreground">
              Source available
            </span>
          )}
          {stale && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-800">
              OCR changed after translation. Update this sentence or rerun this page.
            </span>
          )}
        </div>

        {error && <p className="text-xs text-destructive">{error}</p>}

        {protectedReference && (
          <Dialog open={referenceOpen} onOpenChange={setReferenceOpen}>
            <DialogContent className="max-w-xl">
              <DialogHeader>
                <DialogTitle>{protectedReference.title}</DialogTitle>
                <DialogDescription>
                  {protectedReference.subtitle ?? "Attached from the latest translation provenance."}
                </DialogDescription>
              </DialogHeader>
              {protectedReference.sources.length > 0 ? (
                <ul className="space-y-2 text-sm leading-relaxed text-foreground">
                  {protectedReference.sources.map((sourceLine) => (
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
        )}
      </div>
    </SentenceRow>
  );
}
