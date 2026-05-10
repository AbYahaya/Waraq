/**
 * §3.7 Sentence ID format + cross-pane scroll-sync.
 *
 * Per Dokument 1 §3.7:
 *
 *   "Sentence ID in the format [AR-047-003]."
 *   "Click on sentence → all windows jump to that location."
 *
 * The format is `AR-{page_index zero-padded 3}-{sentence_index_in_page
 * zero-padded 3}`. The `AR` prefix anchors the ID to the Arabic source
 * — the same ID is shown in both the OCR pane and the translation pane
 * (the canonical `Sentence-level between OCR and translation` synchronization
 * uses one shared ID per sentence).
 *
 * The sentence index within a page is computed at the call site from
 * the segment list's natural ordering (block_index, satz_index — the
 * `/pages/{u}/segments` endpoint returns them in that order). The
 * frontend enumerates and formats; no backend column needed.
 *
 * Click-to-jump uses a tiny CustomEvent bus keyed by `satz_uuid`.
 * Each pane listens for `waraq:sentence-jump` events and scrolls its
 * own row into view when one matches. Decoupled — panes don't know
 * about each other.
 */

const PAGE_PAD = 3;
const SENTENCE_PAD = 3;

const JUMP_EVENT = "waraq:sentence-jump";

export function formatSentenceId(
  pageIndex: number,
  sentenceIndexInPage: number,
): string {
  const page = String(pageIndex).padStart(PAGE_PAD, "0");
  const sentence = String(sentenceIndexInPage).padStart(SENTENCE_PAD, "0");
  return `[AR-${page}-${sentence}]`;
}

export interface SentenceJumpDetail {
  /** The canonical satz_uuid being jumped to. */
  satzUuid: string;
  /** Origin pane id, so the originating pane doesn't scroll itself. */
  origin?: string;
}

/**
 * Broadcast a "jump to this sentence in all other panes" intent.
 *
 * Use a unique `origin` per pane (e.g., "ocr", "translation",
 * "original") so a pane can ignore its own emissions.
 */
export function emitSentenceJump(detail: SentenceJumpDetail): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent<SentenceJumpDetail>(JUMP_EVENT, { detail }),
  );
}

/**
 * Subscribe to sentence-jump events. Returns an unsubscribe handle.
 * The handler should resolve the row by `satzUuid` and call
 * `scrollIntoView` on it (panes decide block / inline behavior).
 */
export function onSentenceJump(
  handler: (detail: SentenceJumpDetail) => void,
): () => void {
  if (typeof window === "undefined") return () => undefined;
  const wrapped = (e: Event): void => {
    const ce = e as CustomEvent<SentenceJumpDetail>;
    if (ce.detail) handler(ce.detail);
  };
  window.addEventListener(JUMP_EVENT, wrapped);
  return () => window.removeEventListener(JUMP_EVENT, wrapped);
}
