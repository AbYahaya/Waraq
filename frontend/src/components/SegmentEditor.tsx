/**
 * Editable segment list. Each row supports:
 *  - inline manual text edit (PUT /segments/{uuid}/text → manual revision)
 *  - lock controls (set manual_local / set manual_editorial / release)
 *  - conflict surfacing — opens ConflictResolutionDialog when open
 *    conflict_instances exist for the segment.
 *
 * Locked segments refuse automatic writes (H-1 / H-2). Manual edits via
 * this UI are routed through `create_revision` with
 * `operation_mode=manual_with_confirmation`, which the INVARIANT-Guard
 * does NOT refuse. Cancellation reverts the local edit state.
 */

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Lock, MoreVertical, ShieldAlert } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import { qk, queries } from "@/lib/queries";
import type { Conflict, LockResponse, Segment } from "@/lib/types";
import { cn } from "@/lib/utils";

import { ApplyGlossaryDialog } from "@/components/ApplyGlossaryDialog";
import { ClickableArabic } from "@/components/MorphologyPopover";
import { ConflictResolutionDialog } from "@/components/ConflictResolutionDialog";

export interface SegmentEditorProps {
  pageUuid: string;
}

export function SegmentEditor({ pageUuid }: SegmentEditorProps): JSX.Element {
  const segmentsQ = useQuery(queries.pageSegments(pageUuid));

  if (segmentsQ.isLoading) {
    return <p className="text-sm text-muted-foreground p-3">Loading segments…</p>;
  }
  if (segmentsQ.isError) {
    return <p className="text-sm text-destructive p-3">Failed to load segments.</p>;
  }
  if (!segmentsQ.data || segmentsQ.data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground p-3">
        No segments yet. Run OCR on this page to populate them.
      </p>
    );
  }

  return (
    <ol className="divide-y">
      {segmentsQ.data.map((s) => (
        <SegmentRow key={s.satz_uuid} segment={s} pageUuid={pageUuid} />
      ))}
    </ol>
  );
}

interface SegmentRowProps {
  segment: Segment;
  pageUuid: string;
}

function SegmentRow({ segment, pageUuid }: SegmentRowProps): JSX.Element {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(segment.text_content ?? "");
  const [error, setError] = useState<string | null>(null);
  const [conflictOpen, setConflictOpen] = useState(false);
  const [glossaryOpen, setGlossaryOpen] = useState(false);

  // Reset draft when the upstream segment changes (e.g. another tab edits).
  useEffect(() => {
    if (!editing) setDraft(segment.text_content ?? "");
  }, [segment.text_content, editing]);

  const conflictsQ = useQuery({
    ...queries.segmentConflicts(segment.satz_uuid),
    refetchInterval: false,
  });
  const openConflicts: Conflict[] = (conflictsQ.data ?? []).filter(
    (c) => c.state === "offen",
  );

  const invalidate = (): void => {
    void qc.invalidateQueries({ queryKey: qk.pageSegments(pageUuid) });
    void qc.invalidateQueries({ queryKey: qk.segmentConflicts(segment.satz_uuid) });
  };

  const saveMutation = useMutation({
    mutationFn: (after_text: string) =>
      api.put<Segment>(`/segments/${segment.satz_uuid}/text`, { after_text }),
    onSuccess: () => {
      setEditing(false);
      invalidate();
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Save failed"),
  });

  const setLockMutation = useMutation({
    mutationFn: (level: "manual_local" | "manual_editorial") =>
      api.post<LockResponse>(`/segments/${segment.satz_uuid}/lock`, { level }),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Lock failed"),
  });

  const releaseLockMutation = useMutation({
    mutationFn: (note: string | null) =>
      api.delete<LockResponse>(`/segments/${segment.satz_uuid}/lock`, { note }),
    onSuccess: invalidate,
    onError: (err) =>
      setError(err instanceof ApiError ? err.detail : "Release failed"),
  });

  const onCancel = (): void => {
    setEditing(false);
    setDraft(segment.text_content ?? "");
    setError(null);
  };

  const onSave = (): void => {
    setError(null);
    saveMutation.mutate(draft);
  };

  return (
    <li className="px-3 py-3 group">
      <div className="flex items-baseline justify-between gap-2 mb-1">
        <span className="text-xs text-muted-foreground">#{segment.satz_index}</span>
        <div className="flex items-center gap-2">
          {openConflicts.length > 0 && (
            <button
              type="button"
              onClick={() => setConflictOpen(true)}
              className="flex items-center gap-1 text-xs text-amber-700 hover:underline"
            >
              <ShieldAlert className="h-3 w-3" />
              {openConflicts.length} conflict{openConflicts.length === 1 ? "" : "s"}
            </button>
          )}
          {segment.lock_flag !== "none" && (
            <span className="flex items-center gap-1 text-xs text-amber-700">
              <Lock className="h-3 w-3" />
              {segment.lock_flag === "manual_local" ? "local" : "editorial"}
            </span>
          )}
          <SegmentActionsMenu
            segment={segment}
            onSetLock={(level) => setLockMutation.mutate(level)}
            onReleaseLock={(note) => releaseLockMutation.mutate(note)}
            onEdit={() => setEditing(true)}
            onApplyGlossary={() => setGlossaryOpen(true)}
            disabled={
              setLockMutation.isPending ||
              releaseLockMutation.isPending ||
              saveMutation.isPending
            }
          />
        </div>
      </div>

      {!editing && (
        <p
          dir="rtl"
          className={cn(
            "font-arabic text-lg leading-relaxed cursor-text",
            !segment.text_content && "text-muted-foreground italic",
          )}
          onDoubleClick={() => setEditing(true)}
        >
          <ClickableArabic text={segment.text_content} />
        </p>
      )}

      {editing && (
        <div className="space-y-2">
          <Textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            dir="rtl"
            className="font-arabic text-lg leading-relaxed min-h-[80px]"
            autoFocus
          />
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
            <Button size="sm" onClick={onSave} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? "Saving…" : "Save revision"}
            </Button>
          </div>
        </div>
      )}

      {error && <p className="text-xs text-destructive mt-1">{error}</p>}

      <ConflictResolutionDialog
        open={conflictOpen}
        onOpenChange={setConflictOpen}
        conflicts={openConflicts}
        segment={segment}
      />

      <ApplyGlossaryDialog
        open={glossaryOpen}
        onOpenChange={setGlossaryOpen}
        satzUuid={segment.satz_uuid}
      />
    </li>
  );
}

interface SegmentActionsMenuProps {
  segment: Segment;
  onSetLock: (level: "manual_local" | "manual_editorial") => void;
  onReleaseLock: (note: string | null) => void;
  onEdit: () => void;
  onApplyGlossary: () => void;
  disabled: boolean;
}

function SegmentActionsMenu({
  segment,
  onSetLock,
  onReleaseLock,
  onEdit,
  onApplyGlossary,
  disabled,
}: SegmentActionsMenuProps): JSX.Element {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 opacity-50 group-hover:opacity-100"
          disabled={disabled}
          aria-label="Segment actions"
        >
          <MoreVertical className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={onEdit}>Edit text</DropdownMenuItem>
        <DropdownMenuItem onClick={onApplyGlossary}>Apply glossary…</DropdownMenuItem>
        <DropdownMenuSeparator />
        {segment.lock_flag !== "manual_local" && (
          <DropdownMenuItem onClick={() => onSetLock("manual_local")}>
            Lock (manual_local)
          </DropdownMenuItem>
        )}
        {segment.lock_flag !== "manual_editorial" && (
          <DropdownMenuItem onClick={() => onSetLock("manual_editorial")}>
            Lock (manual_editorial)
          </DropdownMenuItem>
        )}
        {segment.lock_flag !== "none" && (
          <DropdownMenuItem
            onClick={() => {
              const note =
                segment.lock_flag === "manual_editorial"
                  ? prompt(
                      "Editorial release requires a confirmation note. Enter why:",
                      "",
                    )
                  : null;
              // Cancel from the prompt → don't call.
              if (segment.lock_flag === "manual_editorial" && note === null) return;
              onReleaseLock(note);
            }}
          >
            Release lock
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
