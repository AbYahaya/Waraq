/**
 * §3.7 Translation pane — German (target-language) text with canonical
 * Sentence IDs.
 *
 * Reads the page's segments + each segment's history and shows the
 * LATEST `change_source = "re_translate"` revision's `after_text` as
 * the translation. When a segment hasn't been translated yet the row
 * shows a muted placeholder. Click-to-jump synchronizes other panes.
 */

import { useQueries, useQuery } from "@tanstack/react-query";

import { SentenceRow } from "@/components/SentenceRow";
import { queries, type SegmentHistoryDto } from "@/lib/queries";
import type { Segment } from "@/lib/types";

export interface TranslationPaneProps {
  pageUuid: string;
  pageIndex: number;
}

const ORIGIN = "translation";

export function TranslationPane({
  pageUuid,
  pageIndex,
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
}

function TranslationRow({
  segment,
  history,
  pageIndex,
  sentenceIndexInPage,
}: TranslationRowProps): JSX.Element {
  const translationRev = history?.revisions
    .filter((r) => r.change_source === "re_translate")
    .at(-1);
  const translation = translationRev?.after_text ?? null;
  return (
    <SentenceRow
      satzUuid={segment.satz_uuid}
      pageIndex={pageIndex}
      sentenceIndexInPage={sentenceIndexInPage}
      origin={ORIGIN}
    >
      {translation ? (
        <p className="text-sm leading-relaxed">{translation}</p>
      ) : (
        <p className="text-sm text-muted-foreground italic">No translation yet.</p>
      )}
    </SentenceRow>
  );
}
