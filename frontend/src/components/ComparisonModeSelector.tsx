/**
 * §3.7 — 5-mode comparison view selector.
 *
 * Per Dokument 1 §3.7:
 *
 *   1. Original book / OCR
 *   2. Original book / Translation
 *   3. OCR / Translation (default)
 *   4. Triple view
 *   5. Single view fullscreen
 */

import { cn } from "@/lib/utils";

export type ComparisonMode =
  | "original_ocr"
  | "original_translation"
  | "ocr_translation"
  | "triple"
  | "single_fullscreen";

export const COMPARISON_MODES: ReadonlyArray<{
  id: ComparisonMode;
  label: string;
  short: string;
}> = [
  { id: "original_ocr", label: "Original / OCR", short: "Orig|OCR" },
  { id: "original_translation", label: "Original / Translation", short: "Orig|DE" },
  { id: "ocr_translation", label: "OCR / Translation", short: "OCR|DE" },
  { id: "triple", label: "Triple view", short: "Triple" },
  { id: "single_fullscreen", label: "Single view fullscreen", short: "Solo" },
];

export interface ComparisonModeSelectorProps {
  mode: ComparisonMode;
  onModeChange: (mode: ComparisonMode) => void;
  className?: string;
}

export function ComparisonModeSelector({
  mode,
  onModeChange,
  className,
}: ComparisonModeSelectorProps): JSX.Element {
  return (
    <div
      className={cn("inline-flex rounded border bg-background overflow-hidden", className)}
      role="tablist"
    >
      {COMPARISON_MODES.map((m, i) => (
        <button
          key={m.id}
          type="button"
          role="tab"
          aria-selected={mode === m.id}
          title={m.label}
          onClick={() => onModeChange(m.id)}
          className={cn(
            "px-3 py-1 text-xs whitespace-nowrap",
            i > 0 && "border-l",
            mode === m.id
              ? "bg-accent text-accent-foreground"
              : "hover:bg-accent/50",
          )}
        >
          {m.short}
        </button>
      ))}
    </div>
  );
}
