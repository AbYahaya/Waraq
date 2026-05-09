/**
 * Three-path conflict resolution dialog (Sprint 1 §2 / T-5.1.2):
 *  1. lokale_ausnahme       — rule does not apply to this segment
 *  2. glossar_anpassen      — caller adjusted glossary; new concept_id
 *  3. sperrflag_aufheben    — release the lock + carry resolution
 *
 * Per H-6: conflicts must NOT be silently resolved. The user picks one
 * of the three paths, optionally adds a note, and submits. The backend
 * writes the canonical Decision Event (decision_source=conflict_resolution)
 * and stamps the conflict_instance row.
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import { qk } from "@/lib/queries";
import type { Conflict, Segment } from "@/lib/types";
import { cn } from "@/lib/utils";

type Path = "local-exception" | "glossary-change" | "lock-release";

const PATH_LABEL: Record<Path, string> = {
  "local-exception": "Lokale Ausnahme",
  "glossary-change": "Glossar anpassen",
  "lock-release": "Sperrflag aufheben",
};

const PATH_DESCRIPTION: Record<Path, string> = {
  "local-exception":
    "The rule does not apply to this segment. Glossary entry stays unchanged; only this conflict_instance is resolved.",
  "glossary-change":
    "You adjusted the glossary entry separately. Provide the new concept_id; the resolution will reference it.",
  "lock-release":
    "Release the lock on this segment, then resolve the conflict. Editorial-class locks require a confirmation note.",
};

export interface ConflictResolutionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  conflicts: Conflict[];
  segment: Segment;
}

export function ConflictResolutionDialog({
  open,
  onOpenChange,
  conflicts,
  segment,
}: ConflictResolutionDialogProps): JSX.Element | null {
  const qc = useQueryClient();
  const [activeUuid, setActiveUuid] = useState<string | null>(
    conflicts[0]?.conflict_uuid ?? null,
  );
  const [path, setPath] = useState<Path>("local-exception");
  const [note, setNote] = useState("");
  const [confirmationNote, setConfirmationNote] = useState("");
  const [newConceptId, setNewConceptId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const active = conflicts.find((c) => c.conflict_uuid === activeUuid) ?? conflicts[0];

  const resolveMutation = useMutation({
    mutationFn: async (): Promise<Conflict> => {
      if (!active) throw new Error("no conflict selected");
      switch (path) {
        case "local-exception":
          return api.post<Conflict>(
            `/conflicts/${active.conflict_uuid}/resolve/local-exception`,
            { note },
          );
        case "glossary-change":
          return api.post<Conflict>(
            `/conflicts/${active.conflict_uuid}/resolve/glossary-change`,
            { note, new_concept_id: newConceptId },
          );
        case "lock-release":
          return api.post<Conflict>(
            `/conflicts/${active.conflict_uuid}/resolve/lock-release`,
            { note, confirmation_note: confirmationNote },
          );
      }
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.segmentConflicts(segment.satz_uuid) });
      setNote("");
      setConfirmationNote("");
      setNewConceptId("");
      setError(null);
      onOpenChange(false);
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.detail : "Resolution failed"),
  });

  if (conflicts.length === 0) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Resolve open conflict</DialogTitle>
          <DialogDescription>
            Per H-6, every conflict must take one of three explicit paths.
            No silent resolution.
          </DialogDescription>
        </DialogHeader>

        {conflicts.length > 1 && (
          <div className="space-y-1">
            <Label>Conflict</Label>
            <div className="flex flex-wrap gap-1">
              {conflicts.map((c) => (
                <button
                  key={c.conflict_uuid}
                  type="button"
                  onClick={() => setActiveUuid(c.conflict_uuid)}
                  className={cn(
                    "text-xs rounded border px-2 py-1",
                    c.conflict_uuid === active.conflict_uuid
                      ? "bg-accent border-foreground/40"
                      : "hover:bg-accent/50",
                  )}
                >
                  {c.rule_source} · {c.conflict_type}
                </button>
              ))}
            </div>
          </div>
        )}

        {active && (
          <div className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">{active.rule_source}</span>
            {" / "}
            <span>{active.conflict_type}</span>
          </div>
        )}

        <div className="space-y-1">
          <Label>Resolution path</Label>
          <div className="grid grid-cols-3 gap-2">
            {(Object.keys(PATH_LABEL) as Path[]).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setPath(p)}
                className={cn(
                  "rounded border px-3 py-2 text-sm text-left",
                  p === path ? "bg-accent border-foreground/40" : "hover:bg-accent/50",
                )}
              >
                {PATH_LABEL[p]}
              </button>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">{PATH_DESCRIPTION[path]}</p>
        </div>

        {path === "glossary-change" && (
          <div className="space-y-1">
            <Label htmlFor="new-concept-id">New concept_id (UUID)</Label>
            <Input
              id="new-concept-id"
              placeholder="00000000-0000-0000-0000-000000000000"
              value={newConceptId}
              onChange={(e) => setNewConceptId(e.target.value)}
            />
          </div>
        )}

        {path === "lock-release" && segment.lock_flag === "manual_editorial" && (
          <div className="space-y-1">
            <Label htmlFor="confirmation-note">Confirmation note (required)</Label>
            <Input
              id="confirmation-note"
              placeholder="Why is releasing the editorial lock OK here?"
              value={confirmationNote}
              onChange={(e) => setConfirmationNote(e.target.value)}
            />
          </div>
        )}

        <div className="space-y-1">
          <Label htmlFor="resolution-note">Note (optional)</Label>
          <Textarea
            id="resolution-note"
            placeholder="Lands in the Decision-Event content."
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => resolveMutation.mutate()}
            disabled={
              resolveMutation.isPending ||
              (path === "glossary-change" && newConceptId.length < 32) ||
              (path === "lock-release" &&
                segment.lock_flag === "manual_editorial" &&
                confirmationNote.length === 0)
            }
          >
            {resolveMutation.isPending ? "Resolving…" : "Resolve"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
