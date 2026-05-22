/**
 * §2.1 Phase 3 — difficulty report mini-display.
 *
 * Compact badge that opens a difficulty panel. Used in the project
 * sidebar (project-aggregate) and the page header (per-page).
 */

import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { qk, type DifficultyReportDto } from "@/lib/queries";
import { cn } from "@/lib/utils";

export interface DifficultyBadgeProps {
  scope: "page" | "project";
  uuid: string;
  projectUuid?: string;
  className?: string;
}

function scoreToTone(score: number): { badge: string; label: string; panel: string } {
  if (score === 0) {
    return {
      badge: "bg-emerald-100 text-emerald-800 border-emerald-300",
      label: "Clear",
      panel: "border-emerald-200 bg-emerald-50 text-emerald-950",
    };
  }
  if (score < 10) {
    return {
      badge: "bg-amber-100 text-amber-800 border-amber-300",
      label: "Review helpful",
      panel: "border-amber-200 bg-amber-50 text-amber-950",
    };
  }
  return {
    badge: "bg-destructive/15 text-destructive border-destructive/30",
    label: "Needs attention",
    panel: "border-destructive/20 bg-destructive/5 text-destructive",
  };
}

export function DifficultyBadge({
  scope,
  uuid,
  projectUuid,
  className,
}: DifficultyBadgeProps): JSX.Element {
  const [open, setOpen] = useState(false);
  const anchorRef = useRef<HTMLSpanElement | null>(null);
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
  const tone = scoreToTone(data.score);
  const reasons = difficultyReasons(data);
  const riskCards = difficultyRiskCards(data);
  const targetProjectUuid = projectUuid ?? (scope === "project" ? uuid : undefined);
  const workspaceHref =
    scope === "page" && targetProjectUuid !== undefined
      ? `/projects/${targetProjectUuid}/pages/${uuid}`
      : targetProjectUuid !== undefined
        ? `/projects/${targetProjectUuid}`
        : undefined;
  const dpiHref =
    scope === "page" && targetProjectUuid !== undefined
      ? `/projects/${targetProjectUuid}/pages/${uuid}?panel=dpi`
      : undefined;
  const auditHref =
    targetProjectUuid !== undefined ? `/projects/${targetProjectUuid}/audit` : undefined;
  const anchorRect = open ? anchorRef.current?.getBoundingClientRect() : undefined;
  const panelStyle =
    anchorRect !== undefined
      ? {
          left: Math.max(12, Math.min(anchorRect.left, window.innerWidth - 400)),
          top: anchorRect.bottom + 8,
        }
      : undefined;

  return (
    <span ref={anchorRef} className={cn("relative inline-flex", className)}>
      <button
        type="button"
        title={summarizeBreakdown(data)}
        onClick={() => setOpen((prev) => !prev)}
        className={cn(
          "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium transition hover:shadow-sm",
          tone.badge,
        )}
      >
        <span>Difficulty</span>
        <span className="font-semibold">{data.score.toFixed(0)}</span>
      </button>
      {open ? (
        <div
          className="fixed z-50 w-[min(24rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-border bg-card text-left shadow-2xl"
          style={panelStyle}
        >
          <div className={cn("border-b px-4 py-3", tone.panel)}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] opacity-70">
                  {scope === "page" ? "Page difficulty" : "Project difficulty"}
                </p>
                <p className="mt-1 text-2xl font-semibold">{data.score.toFixed(0)}</p>
              </div>
              <span className="rounded-full border border-current/20 px-2 py-1 text-[10px] uppercase tracking-wide">
                {tone.label}
              </span>
            </div>
            <p className="mt-2 text-xs opacity-80">
              Based on {data.segment_count} active segment
              {data.segment_count === 1 ? "" : "s"} and unresolved review signals.
            </p>
          </div>

          <div className="space-y-3 p-4">
            <div className="grid grid-cols-2 gap-2">
              {riskCards.map((card) => (
                <RiskCard key={card.label} {...card} />
              ))}
            </div>

            <div>
              <p className="text-xs font-semibold text-[#1d221d]">Main contributors</p>
              {reasons.length === 0 ? (
                <p className="mt-1 rounded-xl bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
                  No unresolved difficulty signals are currently counted.
                </p>
              ) : (
                <ul className="mt-1 space-y-1">
                  {reasons.slice(0, 5).map((reason) => (
                    <li
                      key={reason.label}
                      className="flex items-center justify-between gap-3 rounded-xl bg-muted/40 px-3 py-2 text-xs"
                    >
                      <span>{reason.label}</span>
                      <span className="font-semibold">{reason.count}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="flex flex-wrap gap-2 border-t pt-3">
              {auditHref !== undefined ? (
                <Button size="sm" variant="outline" asChild>
                  <Link to={auditHref}>Open Audit</Link>
                </Button>
              ) : null}
              {workspaceHref !== undefined ? (
                <Button size="sm" variant="outline" asChild>
                  <Link to={workspaceHref}>Open workspace</Link>
                </Button>
              ) : null}
              {dpiHref !== undefined ? (
                <Button size="sm" asChild>
                  <Link to={dpiHref}>Open DPI recovery</Link>
                </Button>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </span>
  );
}

interface DifficultyReason {
  label: string;
  count: number;
}

interface RiskCardProps {
  label: string;
  value: string;
  tone: "green" | "amber" | "red" | "muted";
}

function RiskCard({ label, value, tone }: RiskCardProps): JSX.Element {
  return (
    <div
      className={cn(
        "rounded-2xl border px-3 py-2",
        tone === "green" && "border-emerald-200 bg-emerald-50 text-emerald-900",
        tone === "amber" && "border-amber-200 bg-amber-50 text-amber-950",
        tone === "red" && "border-destructive/20 bg-destructive/5 text-destructive",
        tone === "muted" && "border-border bg-muted/30 text-muted-foreground",
      )}
    >
      <p className="text-[10px] uppercase tracking-wide opacity-70">{label}</p>
      <p className="mt-1 text-xs font-semibold">{value}</p>
    </div>
  );
}

function difficultyReasons(r: DifficultyReportDto): DifficultyReason[] {
  const b = r.breakdown;
  return [
    { label: "Critical audit findings", count: b.audit_kritisch },
    { label: "High audit findings", count: b.audit_hoch },
    { label: "Medium audit findings", count: b.audit_mittel },
    { label: "Critical consistency findings", count: b.konsistenz_kritisch },
    { label: "Other consistency findings", count: b.konsistenz_other },
    { label: "Hadith H-2 blocking references", count: b.hadith_h_2 },
    { label: "Hadith H-1 review references", count: b.hadith_h_1 },
    { label: "Critical OCR errors", count: b.ocr_error_kritisch },
    { label: "High OCR errors", count: b.ocr_error_hoch },
    { label: "Medium OCR errors", count: b.ocr_error_mittel },
    { label: "Manual local locks", count: b.locked_segment_manual_local },
    { label: "Editorial locks", count: b.locked_segment_manual_editorial },
  ]
    .filter((reason) => reason.count > 0)
    .sort((a, bReason) => bReason.count - a.count);
}

function difficultyRiskCards(r: DifficultyReportDto): RiskCardProps[] {
  const b = r.breakdown;
  const ocrRisk = b.ocr_error_kritisch + b.ocr_error_hoch + b.ocr_error_mittel;
  const religiousRisk = b.hadith_h_2 + b.hadith_h_1;
  const editorialRisk = b.locked_segment_manual_local + b.locked_segment_manual_editorial;
  const auditRisk = b.audit_kritisch + b.audit_hoch + b.audit_mittel;
  const consistencyRisk = b.konsistenz_kritisch + b.konsistenz_other;

  return [
    {
      label: "OCR confidence",
      value: ocrRisk === 0 ? "Clear" : `${ocrRisk} OCR signal${ocrRisk === 1 ? "" : "s"}`,
      tone: b.ocr_error_kritisch > 0 ? "red" : ocrRisk > 0 ? "amber" : "green",
    },
    {
      label: "Engine agreement",
      value:
        ocrRisk === 0
          ? "No active disagreement"
          : "Review OCR alternatives",
      tone: ocrRisk > 0 ? "amber" : "green",
    },
    {
      label: "Religious text",
      value:
        religiousRisk === 0
          ? "No open flags"
          : `${religiousRisk} source check${religiousRisk === 1 ? "" : "s"}`,
      tone: b.hadith_h_2 > 0 ? "red" : religiousRisk > 0 ? "amber" : "green",
    },
    {
      label: "Layout / small print",
      value:
        auditRisk + ocrRisk === 0
          ? "No active signal"
          : "Inspect scan/OCR",
      tone: auditRisk + ocrRisk > 0 ? "amber" : "green",
    },
    {
      label: "Consistency",
      value:
        consistencyRisk === 0
          ? "Clear"
          : `${consistencyRisk} cross-page signal${consistencyRisk === 1 ? "" : "s"}`,
      tone: b.konsistenz_kritisch > 0 ? "red" : consistencyRisk > 0 ? "amber" : "green",
    },
    {
      label: "Locks",
      value:
        editorialRisk === 0
          ? "None"
          : `${editorialRisk} locked segment${editorialRisk === 1 ? "" : "s"}`,
      tone: editorialRisk > 0 ? "muted" : "green",
    },
  ];
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
