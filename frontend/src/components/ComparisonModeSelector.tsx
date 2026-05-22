/**
 * Workspace view selector.
 *
 * The pane engine still uses the canonical five comparison modes, but
 * the UI groups them into the simpler workflow the user sees:
 * Triple, Double, and Solo.
 */

import { cn } from "@/lib/utils";

export type ComparisonMode =
  | "original_ocr"
  | "original_translation"
  | "ocr_translation"
  | "triple"
  | "single_fullscreen";

export type SinglePane = "original" | "ocr" | "translation";

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

const DOUBLE_MODES: ReadonlyArray<{
  id: Exclude<ComparisonMode, "triple" | "single_fullscreen">;
  label: string;
}> = [
  { id: "original_ocr", label: "Original / OCR" },
  { id: "original_translation", label: "Original / Translation" },
  { id: "ocr_translation", label: "OCR / Translation" },
];

const SOLO_PANES: ReadonlyArray<{ id: SinglePane; label: string }> = [
  { id: "original", label: "Original" },
  { id: "ocr", label: "OCR" },
  { id: "translation", label: "Translation" },
];

type PrimaryMode = "triple" | "double" | "solo";

export interface ComparisonModeSelectorProps {
  mode: ComparisonMode;
  onModeChange: (mode: ComparisonMode) => void;
  singlePane: SinglePane;
  onSinglePaneChange: (pane: SinglePane) => void;
  className?: string;
}

export function ComparisonModeSelector({
  mode,
  onModeChange,
  singlePane,
  onSinglePaneChange,
  className,
}: ComparisonModeSelectorProps): JSX.Element {
  const primaryMode = getPrimaryMode(mode);

  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      <div
        className="inline-flex overflow-hidden rounded-xl border border-border/80 bg-background"
        role="tablist"
        aria-label="Workspace view type"
      >
        {PRIMARY_MODES.map((m, i) => (
          <button
            key={m.id}
            type="button"
            role="tab"
            aria-selected={primaryMode === m.id}
            title={m.description}
            onClick={() => {
              if (m.id === "triple") onModeChange("triple");
              if (m.id === "double") onModeChange(isDoubleMode(mode) ? mode : "ocr_translation");
              if (m.id === "solo") onModeChange("single_fullscreen");
            }}
            className={cn(
              "px-3 py-1.5 text-xs font-medium whitespace-nowrap",
              i > 0 && "border-l border-border/80",
              primaryMode === m.id
                ? "bg-[#113f2b] text-white"
                : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
            )}
          >
            {m.label}
          </button>
        ))}
      </div>

      {primaryMode === "double" && (
        <SegmentedSubSelector
          ariaLabel="Double view panes"
          options={DOUBLE_MODES}
          value={isDoubleMode(mode) ? mode : "ocr_translation"}
          onChange={onModeChange}
        />
      )}

      {primaryMode === "solo" && (
        <SegmentedSubSelector
          ariaLabel="Solo view pane"
          options={SOLO_PANES}
          value={singlePane}
          onChange={onSinglePaneChange}
        />
      )}
    </div>
  );
}

const PRIMARY_MODES: ReadonlyArray<{
  id: PrimaryMode;
  label: string;
  description: string;
}> = [
  { id: "triple", label: "Triple", description: "Show Original, OCR, and Translation" },
  { id: "double", label: "Double", description: "Show two panes side by side" },
  { id: "solo", label: "Solo", description: "Show one pane fullscreen" },
];

function SegmentedSubSelector<T extends string>({
  ariaLabel,
  options,
  value,
  onChange,
}: {
  ariaLabel: string;
  options: ReadonlyArray<{ id: T; label: string }>;
  value: T;
  onChange: (value: T) => void;
}): JSX.Element {
  return (
    <div
      className="inline-flex overflow-hidden rounded-xl border border-border/80 bg-background"
      role="tablist"
      aria-label={ariaLabel}
    >
      {options.map((option, i) => (
        <button
          key={option.id}
          type="button"
          role="tab"
          aria-selected={value === option.id}
          onClick={() => onChange(option.id)}
          className={cn(
            "px-2.5 py-1.5 text-xs whitespace-nowrap",
            i > 0 && "border-l border-border/80",
            value === option.id
              ? "bg-accent text-accent-foreground"
              : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function getPrimaryMode(mode: ComparisonMode): PrimaryMode {
  if (mode === "triple") return "triple";
  if (mode === "single_fullscreen") return "solo";
  return "double";
}

function isDoubleMode(
  mode: ComparisonMode,
): mode is Exclude<ComparisonMode, "triple" | "single_fullscreen"> {
  return mode !== "triple" && mode !== "single_fullscreen";
}

export function comparisonModeLabel(mode: ComparisonMode, singlePane: SinglePane): string {
  if (mode === "triple") return "Triple";
  if (mode === "single_fullscreen") {
    const pane = SOLO_PANES.find((option) => option.id === singlePane);
    return `Solo · ${pane?.label ?? "OCR"}`;
  }
  return DOUBLE_MODES.find((option) => option.id === mode)?.label ?? "Double";
}
