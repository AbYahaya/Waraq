/**
 * §2.1 Phase 4 — TOC handling: AR/DE comparison + chapter heading
 * adjustment.
 *
 * Reads the auto-detected TOC from `GET /projects/{u}/toc` and
 * renders entries side-by-side (AR | DE) with inline-editable text.
 * Save writes through the `PUT /toc/entries/{satz_uuid}` endpoint
 * (auto-normalized server-side). Fallback page-by-page entries
 * (`fallback_kind === "page_by_page"`) are read-only — no segment
 * exists to attach the edit to. v1.0 does not support manual TOC
 * definition (canon §2.1: "not part of this version").
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";
import { qk, queries, type TocEntryDto } from "@/lib/queries";
import { cn } from "@/lib/utils";

export interface TocPanelProps {
  projectUuid: string;
  className?: string;
}

export function TocPanel({ projectUuid, className }: TocPanelProps): JSX.Element {
  const q = useQuery(queries.projectToc(projectUuid));
  const qc = useQueryClient();
  const confirmMutation = useMutation({
    mutationFn: () =>
      api.post<{ decision_event_uuid: string; workflow_state: string }>(
        `/projects/${projectUuid}/toc/confirm`,
        { note: "Confirmed from TOC panel." },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.projectToc(projectUuid) });
    },
  });

  if (q.isLoading) {
    return <p className={cn("text-sm text-muted-foreground p-3", className)}>Loading TOC…</p>;
  }
  if (q.isError || q.data === undefined) {
    return (
      <p className={cn("text-sm text-destructive p-3", className)}>
        Could not load TOC.
      </p>
    );
  }

  const isFallback = q.data.fallback_kind === "page_by_page";
  const canConfirm = q.data.page_count > 0 && q.data.confirmation_state !== "confirmed";

  return (
    <div className={cn("flex flex-col h-full min-h-0", className)}>
      <div className="border-b bg-muted/30 px-3 py-3">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="font-medium">Table of contents</span>
          <WorkflowBadge state={q.data.workflow_state} />
          {q.data.confirmation_state === "confirmed" && (
            <span className="rounded-full border border-emerald-300 bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-800">
              Final review confirmed
            </span>
          )}
          <span className="text-[10px] text-muted-foreground">
            {q.data.detected_heading_count} heading
            {q.data.detected_heading_count === 1 ? "" : "s"} detected ·{" "}
            {q.data.page_count} page{q.data.page_count === 1 ? "" : "s"}
          </span>
        </div>

        <div className="mt-3 rounded-xl border bg-background/80 p-3 text-xs leading-relaxed">
          <p className="font-medium text-[#1d221d]">
            {workflowTitle(q.data.workflow_state)}
          </p>
          <p className="mt-1 text-muted-foreground">
            {workflowDescription(q.data.workflow_state)}
          </p>
          {q.data.attention_reasons.length > 0 && (
            <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-2 text-amber-900">
              {q.data.attention_reasons.map((reason) => (
                <p key={reason}>{reason}</p>
              ))}
            </div>
          )}
          {isFallback && q.data.page_count > 0 && (
            <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-2 text-amber-900">
              This is a fallback structure, not a detected chapter list. Confirm it only if
              page-by-page export is acceptable for this book.
            </p>
          )}
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <ExportSetting label="TOC position" value={q.data.export_settings_summary.toc_position} />
            <ExportSetting label="Header level" value={q.data.export_settings_summary.header_heading_level} />
            <ExportSetting label="Chapter break level" value={q.data.export_settings_summary.chapter_break_heading_level} />
            <ExportSetting label="Arabic headings" value={q.data.export_settings_summary.display_arabic_chapter_headings} />
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              onClick={() => confirmMutation.mutate()}
              disabled={!canConfirm || confirmMutation.isPending}
              title={
                q.data.confirmation_state === "confirmed"
                  ? "This TOC state is already confirmed."
                  : undefined
              }
            >
              {confirmMutation.isPending ? "Confirming…" : "Confirm final TOC review"}
            </Button>
            {q.data.confirmed_at && (
              <span className="text-[11px] text-muted-foreground">
                Confirmed {new Date(q.data.confirmed_at).toLocaleString()}
              </span>
            )}
            {confirmMutation.error && (
              <span className="text-xs text-destructive">
                {confirmMutation.error instanceof ApiError
                  ? confirmMutation.error.detail
                  : "Confirmation failed"}
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="flex-1 min-h-0 overflow-auto divide-y">
        {q.data.entries.length === 0 && (
          <p className="text-sm text-muted-foreground p-3">
            No pages in this project yet.
          </p>
        )}
        {q.data.entries.map((entry, idx) => (
          <TocRow
            key={`${entry.page_uuid}-${entry.satz_uuid ?? "fallback"}-${idx}`}
            entry={entry}
            projectUuid={projectUuid}
            readOnly={entry.satz_uuid === null}
          />
        ))}
      </div>
    </div>
  );
}

function WorkflowBadge({ state }: { state: string }): JSX.Element {
  const tone =
    state === "final_review_confirmed"
      ? "border-emerald-300 bg-emerald-100 text-emerald-800"
      : state === "toc_requires_attention" || state === "no_toc_detected"
        ? "border-amber-300 bg-amber-100 text-amber-800"
        : "border-blue-200 bg-blue-50 text-blue-800";
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium", tone)}>
      {workflowTitle(state)}
    </span>
  );
}

function workflowTitle(state: string): string {
  switch (state) {
    case "no_pages":
      return "No pages";
    case "no_toc_detected":
      return "No TOC detected";
    case "toc_requires_attention":
      return "TOC requires attention";
    case "final_review_confirmed":
      return "Final TOC review";
    case "toc_detected":
    default:
      return "TOC detected";
  }
}

function workflowDescription(state: string): string {
  switch (state) {
    case "no_pages":
      return "Upload pages before Waraq can detect or synthesize a table of contents.";
    case "no_toc_detected":
      return "No heading blocks were detected, so Waraq is showing the canonical page-by-page fallback.";
    case "toc_requires_attention":
      return "A TOC-like heading structure exists, but some heading data should be reviewed before export.";
    case "final_review_confirmed":
      return "The current TOC/fallback state has been explicitly confirmed for export planning.";
    case "toc_detected":
    default:
      return "Detected heading blocks are listed below. Review Arabic and translated titles, then confirm final review.";
  }
}

function ExportSetting({
  label,
  value,
}: {
  label: string;
  value: string | number | boolean | undefined;
}): JSX.Element {
  return (
    <div className="rounded-lg border bg-muted/30 px-2 py-1.5">
      <span className="block text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <span className="text-[11px] text-[#1d221d]">{String(value ?? "Not configured")}</span>
    </div>
  );
}

interface TocRowProps {
  entry: TocEntryDto;
  projectUuid: string;
  readOnly: boolean;
}

function TocRow({ entry, projectUuid, readOnly }: TocRowProps): JSX.Element {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [arText, setArText] = useState(entry.ar_text);
  const [deText, setDeText] = useState(entry.de_text);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      api.put<{ rev_uuid: string; satz_uuid: string }>(
        `/toc/entries/${entry.satz_uuid}`,
        { ar_text: arText, de_text: deText },
      ),
    onSuccess: () => {
      setEditing(false);
      setError(null);
      void qc.invalidateQueries({ queryKey: qk.projectToc(projectUuid) });
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Save failed"),
  });

  const indentClass = entry.level === 1 ? "" : "pl-6";

  return (
    <div className={cn("px-3 py-2", indentClass)}>
      <div className="text-[10px] text-muted-foreground mb-1 flex items-center gap-2">
        <span>p.{entry.page_index}</span>
        <span>·</span>
        <span>level {entry.level}</span>
        {readOnly && (
          <span className="text-amber-700">· read-only (fallback)</span>
        )}
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-0.5">
            AR
          </div>
          {editing && !readOnly ? (
            <input
              dir="rtl"
              value={arText}
              onChange={(e) => setArText(e.target.value)}
              className="w-full px-2 py-1 border rounded font-arabic text-base leading-relaxed bg-background"
            />
          ) : (
            <p
              dir="rtl"
              className="font-arabic text-base leading-relaxed truncate"
              title={entry.ar_text}
            >
              {entry.ar_text || (
                <span className="italic text-muted-foreground">(empty)</span>
              )}
            </p>
          )}
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-0.5">
            DE
          </div>
          {editing && !readOnly ? (
            <input
              value={deText}
              onChange={(e) => setDeText(e.target.value)}
              className="w-full px-2 py-1 border rounded text-sm leading-relaxed bg-background"
            />
          ) : (
            <p className="text-sm leading-relaxed truncate" title={entry.de_text}>
              {entry.de_text || (
                <span className="italic text-muted-foreground">(no translation)</span>
              )}
            </p>
          )}
        </div>
      </div>
      {!readOnly && (
        <div className="mt-2 flex items-center gap-2">
          {editing ? (
            <>
              <Button
                size="sm"
                onClick={() => mutation.mutate()}
                disabled={mutation.isPending}
              >
                {mutation.isPending ? "Saving…" : "Save"}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setEditing(false);
                  setArText(entry.ar_text);
                  setDeText(entry.de_text);
                  setError(null);
                }}
              >
                Cancel
              </Button>
            </>
          ) : (
            <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
              Edit
            </Button>
          )}
          {error && <span className="text-xs text-destructive">{error}</span>}
        </div>
      )}
    </div>
  );
}
