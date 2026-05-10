/**
 * §2.1 Phase 3 — difficulty report mini-display.
 *
 * Compact badge that renders a difficulty score + a tooltip-on-hover
 * breakdown. Used in the project sidebar (project-aggregate) and the
 * page header (per-page).
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { qk, type DifficultyReportDto } from "@/lib/queries";
import { cn } from "@/lib/utils";

export interface DifficultyBadgeProps {
  scope: "page" | "project";
  uuid: string;
  className?: string;
}

function scoreToTone(score: number): string {
  if (score === 0) return "bg-emerald-100 text-emerald-800 border-emerald-300";
  if (score < 10) return "bg-amber-100 text-amber-800 border-amber-300";
  return "bg-destructive/15 text-destructive border-destructive/30";
}

export function DifficultyBadge({
  scope,
  uuid,
  className,
}: DifficultyBadgeProps): JSX.Element {
  const path = scope === "page" ? `/pages/${uuid}/difficulty` : `/projects/${uuid}/difficulty`;
  const queryKey = scope === "page" ? qk.pageDifficulty(uuid) : qk.projectDifficulty(uuid);
  const q = useQuery<DifficultyReportDto>({
    queryKey,
    queryFn: () => api.get<DifficultyReportDto>(path),
  });

  if (q.isLoading) {
    return (
      <span className={cn("text-[10px] text-muted-foreground", className)}>
        difficulty…
      </span>
    );
  }
  if (q.isError || q.data === undefined) {
    return (
      <span className={cn("text-[10px] text-muted-foreground", className)}>
        difficulty —
      </span>
    );
  }

  const data = q.data;
  return (
    <span
      title={summarizeBreakdown(data)}
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-medium",
        scoreToTone(data.score),
        className,
      )}
    >
      <span>Difficulty</span>
      <span className="font-semibold">{data.score.toFixed(0)}</span>
    </span>
  );
}

function summarizeBreakdown(r: DifficultyReportDto): string {
  const b = r.breakdown;
  const parts: string[] = [];
  if (b.audit_kritisch) parts.push(`${b.audit_kritisch}× audit kritisch`);
  if (b.audit_hoch) parts.push(`${b.audit_hoch}× audit hoch`);
  if (b.audit_mittel) parts.push(`${b.audit_mittel}× audit mittel`);
  if (b.konsistenz_kritisch) parts.push(`${b.konsistenz_kritisch}× Konsistenz kritisch`);
  if (b.konsistenz_other) parts.push(`${b.konsistenz_other}× Konsistenz`);
  if (b.hadith_h_2) parts.push(`${b.hadith_h_2}× Hadith H-2`);
  if (b.hadith_h_1) parts.push(`${b.hadith_h_1}× Hadith H-1`);
  if (b.ocr_error_kritisch) parts.push(`${b.ocr_error_kritisch}× OCR kritisch`);
  if (b.ocr_error_hoch) parts.push(`${b.ocr_error_hoch}× OCR hoch`);
  if (b.ocr_error_mittel) parts.push(`${b.ocr_error_mittel}× OCR mittel`);
  if (b.locked_segment_manual_local + b.locked_segment_manual_editorial > 0) {
    const n = b.locked_segment_manual_local + b.locked_segment_manual_editorial;
    parts.push(`${n}× lock`);
  }
  if (parts.length === 0) return "No findings";
  return `Score ${r.score.toFixed(1)} (${r.segment_count} segments) — ${parts.join(", ")}`;
}
