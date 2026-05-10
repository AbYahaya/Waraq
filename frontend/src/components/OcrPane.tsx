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

import { useQueries, useQuery } from "@tanstack/react-query";

import { ClickableArabic } from "@/components/MorphologyPopover";
import { SentenceRow } from "@/components/SentenceRow";
import { queries, type SegmentHistoryDto } from "@/lib/queries";
import type { Segment } from "@/lib/types";

export interface OcrPaneProps {
  pageUuid: string;
  pageIndex: number;
}

const ORIGIN = "ocr";

export function OcrPane({ pageUuid, pageIndex }: OcrPaneProps): JSX.Element {
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
}

function OcrRow({
  segment,
  history,
  pageIndex,
  sentenceIndexInPage,
}: OcrRowProps): JSX.Element {
  const source =
    history?.revisions[0]?.after_text ?? segment.text_content ?? "";
  return (
    <SentenceRow
      satzUuid={segment.satz_uuid}
      pageIndex={pageIndex}
      sentenceIndexInPage={sentenceIndexInPage}
      origin={ORIGIN}
    >
      <p dir="rtl" className="font-arabic text-base leading-relaxed">
        <ClickableArabic text={source} />
      </p>
    </SentenceRow>
  );
}
