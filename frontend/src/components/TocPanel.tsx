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

  return (
    <div className={cn("flex flex-col h-full min-h-0", className)}>
      <div className="px-3 py-2 border-b text-xs flex items-center gap-2 bg-muted/30">
        <span className="font-medium">Table of contents</span>
        {isFallback ? (
          <span
            title="Canonical §2.1 fallback — no heading blocks detected, generating one entry per page."
            className="inline-flex items-center px-2 py-0.5 rounded-full border text-[10px] font-medium bg-amber-100 text-amber-800 border-amber-300"
          >
            Page-by-page fallback
          </span>
        ) : (
          <span className="text-[10px] text-muted-foreground">
            {q.data.detected_heading_count} heading
            {q.data.detected_heading_count === 1 ? "" : "s"} detected
            {" · "}
            {q.data.page_count} page{q.data.page_count === 1 ? "" : "s"}
          </span>
        )}
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
