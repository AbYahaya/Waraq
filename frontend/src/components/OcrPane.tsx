/**
 * §3.7 OCR pane — Arabic source text with canonical Sentence IDs.
 *
 * Reads the page's segments + each segment's history and shows the
 * OLDEST `change_source != "re_translate"` revision's `after_text` as
 * the OCR baseline (mirrors the existing `<ComparisonView>` source
 * resolution). Each row carries the sentence ID via `<SentenceRow>`,
 * so click-to-jump synchronizes the translation pane and any future
 * pane that listens to the bus.
 */

import { useEffect, useState } from "react";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";

import { ClickableArabic } from "@/components/MorphologyPopover";
import { SentenceRow } from "@/components/SentenceRow";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import { queries, type SegmentHistoryDto } from "@/lib/queries";
import type { Segment } from "@/lib/types";
import {
  getLatestSourceRevision,
  getLatestTranslationRevision,
  isTranslationStale,
} from "@/lib/segment-history";
import { qk } from "@/lib/queries";
import { cn } from "@/lib/utils";

export interface OcrPaneProps {
  pageUuid: string;
  pageIndex: number;
  editable?: boolean;
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
          <OcrRow
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

interface OcrRowProps {
  segment: Segment;
  history: SegmentHistoryDto | undefined;
  pageIndex: number;
  sentenceIndexInPage: number;
  pageUuid: string;
  editable: boolean;
}

function OcrRow({
  segment,
  history,
  pageIndex,
  sentenceIndexInPage,
  pageUuid,
  editable,
}: OcrRowProps): JSX.Element {
  const qc = useQueryClient();
  const sourceRevision = getLatestSourceRevision(history);
  const translationRevision = getLatestTranslationRevision(history);
  const stale = isTranslationStale(history);
  const source = sourceRevision?.text ?? segment.text_content ?? "";
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(source);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!editing) setDraft(source);
  }, [source, editing]);

  const saveMutation = useMutation({
    mutationFn: (after_text: string) =>
      api.put<Segment>(`/segments/${segment.satz_uuid}/text`, { after_text }),
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
              dir="rtl"
              className="font-arabic text-base leading-relaxed min-h-[112px]"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <Button size="sm" variant="ghost" onClick={() => {
                setEditing(false);
                setDraft(source);
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
                {saveMutation.isPending ? "Saving…" : "Save OCR"}
              </Button>
            </div>
          </div>
        ) : (
          <p
            dir="rtl"
            className={cn(
              "font-arabic text-base leading-relaxed",
              editable && "cursor-text",
            )}
            onDoubleClick={() => {
              if (editable) setEditing(true);
            }}
          >
            <ClickableArabic text={source} />
          </p>
        )}

        <div className="flex flex-wrap items-center gap-2 text-[11px]">
          {editable && !editing && (
            <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
              Edit OCR
            </Button>
          )}
          {translationRevision && (
            <span className="rounded-full bg-muted px-2 py-0.5 text-muted-foreground">
              Translation present
            </span>
          )}
          {stale && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-800">
              Translation outdated for this sentence
            </span>
          )}
        </div>

        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
    </SentenceRow>
  );
}
