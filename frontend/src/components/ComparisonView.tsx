/**
 * Side-by-side AR | DE comparison view.
 *
 * Source (AR) is the FIRST revision in the segment's history (the OCR
 * baseline). Translation (DE) is the LAST revision with
 * `change_source = re_translate` if any, else the segment's current
 * `text_content` (which after a translation pass equals the same).
 *
 * For segments that haven't been translated yet, the right column
 * shows a muted "no translation yet" placeholder. We deliberately
 * don't infer language from script — the canonical signal is the
 * revision chain's `change_source`.
 */

import { useQueries, useQuery } from "@tanstack/react-query";

import { ClickableArabic } from "@/components/MorphologyPopover";
import { queries, type SegmentHistoryDto } from "@/lib/queries";
import type { Segment } from "@/lib/types";

export interface ComparisonViewProps {
  pageUuid: string;
}

export function ComparisonView({ pageUuid }: ComparisonViewProps): JSX.Element {
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
      <p className="text-sm text-muted-foreground p-3">
        No segments yet on this page.
      </p>
    );
  }

  return (
    <ol className="divide-y">
      {segmentsQ.data.map((s, i) => {
        const history = histories[i]?.data;
        return (
          <ComparisonRow
            key={s.satz_uuid}
            segment={s}
            history={history}
          />
        );
      })}
    </ol>
  );
}

interface ComparisonRowProps {
  segment: Segment;
  history: SegmentHistoryDto | undefined;
}

function ComparisonRow({ segment, history }: ComparisonRowProps): JSX.Element {
  // Source = oldest revision's after_text; fall back to current text.
  const source = history?.revisions[0]?.after_text ?? segment.text_content ?? "";

  // Translation = newest re_translate revision; otherwise null.
  const translationRev = history?.revisions
    .filter((r) => r.change_source === "re_translate")
    .at(-1);
  const translation = translationRev?.after_text ?? null;

  return (
    <li className="px-3 py-3">
      <div className="text-xs text-muted-foreground mb-2">#{segment.satz_index}</div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">
            AR (source)
          </div>
          <p
            dir="rtl"
            className="font-arabic text-base leading-relaxed"
          >
            <ClickableArabic text={source} />
          </p>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">
            DE (translation)
          </div>
          {translation ? (
            <p className="text-sm leading-relaxed">{translation}</p>
          ) : (
            <p className="text-sm text-muted-foreground italic">
              No translation yet.
            </p>
          )}
        </div>
      </div>
    </li>
  );
}
