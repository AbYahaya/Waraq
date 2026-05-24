/**
 * §3.7 — Multi-pane viewer with draggable separators.
 *
 * Per Dokument 1 §3.7:
 *
 *   "Triple view: draggable separators 15–70%, double-click = 33/33/33%."
 *
 * The same primitive backs the canonical 5 comparison modes:
 *   1 pane  — single view fullscreen (mode 5)
 *   2 panes — original / ocr | original / translation | ocr / translation (modes 1-3)
 *   3 panes — triple view (mode 4)
 *
 * Panes are rendered in the order supplied. Separators apply the
 * canonical 15–70% clamp. Double-click resets to even split (50/50 for
 * 2 panes, 33/33/34 for 3).
 *
 * State is local — the layout is workspace-scoped, not project-scoped,
 * so reload reverts to default split (acceptable v1.0 behavior).
 */

import { Fragment, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

const MIN_PCT = 15;
const MAX_PCT = 70;

export interface PaneConfig {
  /** Stable key used as React key + for testing. */
  id: string;
  /** Pane label rendered above the content. */
  label: string;
  /** Pane content. */
  node: React.ReactNode;
}

export interface MultiPaneViewProps {
  panes: PaneConfig[];
  className?: string;
}

function defaultSplits(n: number): number[] {
  if (n <= 1) return [100];
  if (n === 2) return [50, 50];
  // n=3 — first two get 33, last gets remainder for round-trip stability.
  return [33, 33, 34];
}

export function MultiPaneView({ panes, className }: MultiPaneViewProps): JSX.Element {
  const [splits, setSplits] = useState<number[]>(() => defaultSplits(panes.length));
  const containerRef = useRef<HTMLDivElement>(null);

  // Reset splits when pane count changes (mode switch).
  useEffect(() => {
    setSplits(defaultSplits(panes.length));
  }, [panes.length]);

  if (panes.length === 0) return <div className={className} />;

  if (panes.length === 1) {
    const only = panes[0];
    return (
      <div ref={containerRef} className={cn("flex h-full min-h-0", className)}>
        <Pane label={only.label} className="flex-1 min-w-0">
          {only.node}
        </Pane>
      </div>
    );
  }

  const onSeparatorPointerDown = (sepIndex: number) => (e: React.PointerEvent) => {
    e.preventDefault();
    const container = containerRef.current;
    if (!container) return;
    const rect = container.getBoundingClientRect();

    // Pointer move handler — recompute the split at sepIndex from the cursor.
    const onMove = (ev: PointerEvent): void => {
      const x = ev.clientX - rect.left;
      const pct = (x / rect.width) * 100;
      setSplits((prev) => clampedAdjust(prev, sepIndex, pct));
    };

    const onUp = (): void => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  };

  const onSeparatorDoubleClick = (): void => {
    setSplits(defaultSplits(panes.length));
  };

  return (
    <div
      ref={containerRef}
      className={cn("flex h-full min-h-0", className)}
      role="group"
    >
      {panes.map((pane, i) => (
        <Fragment key={pane.id}>
          <Pane
            label={pane.label}
            style={{ width: `${splits[i] ?? 0}%` }}
            className="min-w-0"
          >
            {pane.node}
          </Pane>
          {i < panes.length - 1 && (
            <Separator
              onPointerDown={onSeparatorPointerDown(i)}
              onDoubleClick={onSeparatorDoubleClick}
            />
          )}
        </Fragment>
      ))}
    </div>
  );
}

interface PaneProps {
  label: string;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

function Pane({ label, children, className, style }: PaneProps): JSX.Element {
  return (
    <div
      className={cn("flex flex-col h-full min-h-0 overflow-hidden", className)}
      style={style}
    >
      <div className="px-3 py-1.5 border-b text-[10px] uppercase tracking-wide text-muted-foreground bg-muted/40">
        {label}
      </div>
      <div className="flex-1 min-h-0 overflow-hidden">{children}</div>
    </div>
  );
}

interface SeparatorProps {
  onPointerDown: (e: React.PointerEvent) => void;
  onDoubleClick: () => void;
}

function Separator({ onPointerDown, onDoubleClick }: SeparatorProps): JSX.Element {
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      onPointerDown={onPointerDown}
      onDoubleClick={onDoubleClick}
      className="w-1 bg-border hover:bg-primary/40 cursor-col-resize transition-colors flex-shrink-0"
      title="Drag to resize · double-click to reset"
    />
  );
}

/**
 * Apply a new percentage to the boundary at `sepIndex` (between panes
 * `sepIndex` and `sepIndex+1`), keeping the §3.7 15-70% clamp + the
 * other panes' relative widths.
 *
 * The cursor's percentage is interpreted as the right edge of pane
 * `sepIndex` (== left edge of pane `sepIndex+1`). We clamp each
 * affected pane to [MIN, MAX] independently, giving the canonical
 * 15-70% behavior even when other panes are at their limits.
 */
function clampedAdjust(prev: number[], sepIndex: number, cursorPct: number): number[] {
  const next = [...prev];
  // Cumulative left edge of pane sepIndex.
  let leftEdge = 0;
  for (let i = 0; i < sepIndex; i++) leftEdge += next[i]!;

  let leftSize = cursorPct - leftEdge;
  let rightSize = next[sepIndex]! + next[sepIndex + 1]! - leftSize;

  // Apply 15-70% clamp to both affected panes.
  if (leftSize < MIN_PCT) {
    leftSize = MIN_PCT;
    rightSize = next[sepIndex]! + next[sepIndex + 1]! - leftSize;
  } else if (leftSize > MAX_PCT) {
    leftSize = MAX_PCT;
    rightSize = next[sepIndex]! + next[sepIndex + 1]! - leftSize;
  }
  if (rightSize < MIN_PCT) {
    rightSize = MIN_PCT;
    leftSize = next[sepIndex]! + next[sepIndex + 1]! - rightSize;
  } else if (rightSize > MAX_PCT) {
    rightSize = MAX_PCT;
    leftSize = next[sepIndex]! + next[sepIndex + 1]! - rightSize;
  }

  next[sepIndex] = leftSize;
  next[sepIndex + 1] = rightSize;
  return next;
}
