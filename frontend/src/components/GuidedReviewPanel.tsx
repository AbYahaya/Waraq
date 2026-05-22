/**
 * §2.1 Phase 3 — Guided review walker.
 *
 * Renders the canonical priority-ordered queue from
 * `/projects/{u}/guided-review/queue`. The user steps through with
 * Prev / Next; clicking the segment-link emits a sentence-jump event
 * so the OCR / Translation panes scroll to the offending row.
 *
 * v1.0 is informational — actual finding resolution still flows
 * through the existing per-finding services (audit / consistency /
 * OCR-review / hadith preflight). This panel surfaces the queue for
 * the user to walk; "Resolve" navigates to the relevant resolver.
 */

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { queries, type GuidedReviewItemDto } from "@/lib/queries";
import { emitSentenceJump } from "@/lib/sentence-id";
import { cn } from "@/lib/utils";

const TIER_LABEL: Record<string, string> = {
  p_03_blocking: "P-03 blocking",
  p_04_blocking: "P-04 blocking",
  warning: "Warning",
};

const TIER_TONE: Record<string, string> = {
  p_03_blocking: "bg-destructive/15 text-destructive border-destructive/30",
  p_04_blocking: "bg-amber-100 text-amber-800 border-amber-300",
  warning: "bg-blue-100 text-blue-800 border-blue-300",
};

const KIND_LABEL: Record<string, string> = {
  audit_befund: "Audit Befund",
  konsistenz_befund: "Konsistenz",
  ocr_error: "OCR error",
  hadith: "Hadith",
};

export interface GuidedReviewPanelProps {
  projectUuid: string;
  className?: string;
}

export function GuidedReviewPanel({
  projectUuid,
  className,
}: GuidedReviewPanelProps): JSX.Element {
  const q = useQuery(queries.guidedReviewQueue(projectUuid));
  const [cursor, setCursor] = useState(0);

  // Reset cursor if the queue shrank.
  useEffect(() => {
    if (q.data && cursor >= q.data.items.length) setCursor(0);
  }, [q.data, cursor]);

  if (q.isLoading) {
    return <p className={cn("text-sm text-muted-foreground p-3", className)}>Loading…</p>;
  }
  if (q.isError || q.data === undefined) {
    return (
      <p className={cn("text-sm text-destructive p-3", className)}>
        Could not load review queue.
      </p>
    );
  }

  if (q.data.items.length === 0) {
    return (
      <div className={cn("p-3", className)}>
        <p className="text-sm text-emerald-700">All findings resolved — nothing to review.</p>
      </div>
    );
  }

  const item: GuidedReviewItemDto = q.data.items[cursor]!;

  return (
    <div className={cn("shrink-0 space-y-2 border-t p-2.5", className)}>
      <div className="flex items-baseline justify-between">
        <div className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          Guided review
        </div>
        <div className="text-xs text-muted-foreground">
          {cursor + 1} / {q.data.total}
        </div>
      </div>

      <div className="flex flex-wrap gap-2 text-[10px]">
        {Object.entries(q.data.by_tier).map(([t, n]) => (
          <span
            key={t}
            className={cn(
              "inline-flex items-center gap-1 px-2 py-0.5 rounded-full border font-medium",
              TIER_TONE[t] ?? "bg-muted text-muted-foreground",
            )}
          >
            {TIER_LABEL[t] ?? t}: {n}
          </span>
        ))}
      </div>

      <div className="rounded-xl border p-2 space-y-2">
        <div className="flex items-center gap-2 text-xs">
          <span
            className={cn(
              "inline-flex items-center px-2 py-0.5 rounded-full border font-medium",
              TIER_TONE[item.tier] ?? "bg-muted text-muted-foreground",
            )}
          >
            {TIER_LABEL[item.tier] ?? item.tier}
          </span>
          <span className="text-muted-foreground">
            {KIND_LABEL[item.kind] ?? item.kind} · {item.severity}
          </span>
        </div>
        <div className="text-xs text-muted-foreground font-mono break-all">
          {item.finding_uuid.slice(0, 8)}…
        </div>
        {item.satz_uuid !== null && (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() =>
              emitSentenceJump({ satzUuid: item.satz_uuid as string, origin: "guided-review" })
            }
            className="text-xs"
          >
            Jump to segment
          </Button>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Button
          type="button"
          size="sm"
          className="h-8 text-xs"
          variant="outline"
          onClick={() => setCursor((c) => Math.max(0, c - 1))}
          disabled={cursor === 0}
        >
          Prev
        </Button>
        <Button
          type="button"
          size="sm"
          className="h-8 text-xs"
          onClick={() => setCursor((c) => Math.min(q.data.items.length - 1, c + 1))}
          disabled={cursor >= q.data.items.length - 1}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
