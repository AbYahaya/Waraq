/**
 * Shared sentence-row component used by both `OcrPane` + `TranslationPane`.
 *
 * Per §3.7:
 *   - Sentence ID `[AR-047-003]` displayed at the head of each row.
 *   - Click on sentence → all windows jump to that location.
 *
 * The row carries `data-satz-uuid` so cross-pane jump handlers can
 * locate it via `querySelector`.
 */

import { forwardRef, type HTMLAttributes, useEffect, useRef } from "react";

import {
  emitSentenceJump,
  formatSentenceId,
  onSentenceJump,
} from "@/lib/sentence-id";
import { cn } from "@/lib/utils";

export interface SentenceRowProps extends HTMLAttributes<HTMLDivElement> {
  satzUuid: string;
  pageIndex: number;
  sentenceIndexInPage: number;
  /** Origin pane id — used to ignore self-emitted jumps. */
  origin: string;
  /** Pane content (the AR or DE text). */
  children: React.ReactNode;
}

export const SentenceRow = forwardRef<HTMLDivElement, SentenceRowProps>(
  function SentenceRow(
    { satzUuid, pageIndex, sentenceIndexInPage, origin, children, className, ...rest },
    forwardedRef,
  ): JSX.Element {
    const localRef = useRef<HTMLDivElement | null>(null);

    // Subscribe to cross-pane jump events.
    useEffect(() => {
      const unsubscribe = onSentenceJump((detail) => {
        if (detail.origin === origin) return; // ignore self
        if (detail.satzUuid !== satzUuid) return;
        const el = localRef.current;
        if (el === null) return;
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      });
      return unsubscribe;
    }, [satzUuid, origin]);

    const onJump = (): void => {
      emitSentenceJump({ satzUuid, origin });
    };

    return (
      <div
        ref={(el) => {
          localRef.current = el;
          if (typeof forwardedRef === "function") forwardedRef(el);
          else if (forwardedRef !== null) forwardedRef.current = el;
        }}
        data-satz-uuid={satzUuid}
        className={cn("px-3 py-3 border-b last:border-b-0", className)}
        {...rest}
      >
        <button
          type="button"
          onClick={onJump}
          className="text-[10px] font-mono text-muted-foreground hover:text-primary uppercase tracking-wide"
          title="Click to sync all panes to this sentence"
        >
          {formatSentenceId(pageIndex, sentenceIndexInPage)}
        </button>
        <div className="mt-1">{children}</div>
      </div>
    );
  },
);
