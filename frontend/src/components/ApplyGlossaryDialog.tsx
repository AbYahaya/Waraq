/**
 * Apply glossary to a segment — RULE_BINDING surface.
 *
 * The user supplies candidate surface forms (one per line). The backend
 * resolves each via `glossary.lookup` (canonical sole entrypoint per
 * R-S2-08). For every match:
 *   - unlocked Segment → writes a RULE_BINDING-PO via PROVENANCE-Kern
 *   - locked Segment   → detect_conflict creates a `conflict_instance`
 *     row that the row's conflict badge will surface for resolution.
 *
 * The dialog reports `applied` vs `conflict_detected` outcomes after
 * the call.
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
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import { qk } from "@/lib/queries";

interface RuleBindingResponse {
  outcome: "applied" | "conflict_detected";
  matched_concept_ids: string[];
  conflict_uuid: string | null;
  rule_binding_po_uuid: string | null;
}

export interface ApplyGlossaryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  satzUuid: string;
}

export function ApplyGlossaryDialog({
  open,
  onOpenChange,
  satzUuid,
}: ApplyGlossaryDialogProps): JSX.Element {
  const qc = useQueryClient();
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RuleBindingResponse | null>(null);

  const mutation = useMutation({
    mutationFn: (candidates: string[]) =>
      api.post<RuleBindingResponse>(`/segments/${satzUuid}/rule-binding`, {
        candidate_surface_forms: candidates,
      }),
    onSuccess: (r) => {
      setResult(r);
      void qc.invalidateQueries({ queryKey: qk.segmentConflicts(satzUuid) });
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.detail : "Failed to apply glossary"),
  });

  const onSubmit = (): void => {
    setError(null);
    setResult(null);
    const candidates = text
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    if (candidates.length === 0) {
      setError("Provide at least one surface form");
      return;
    }
    mutation.mutate(candidates);
  };

  const onReset = (): void => {
    setText("");
    setError(null);
    setResult(null);
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) onReset();
        onOpenChange(o);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Apply glossary to segment</DialogTitle>
          <DialogDescription>
            Enter candidate surface forms (one per line). Each is looked
            up via the canonical `glossary.lookup`; matches either write
            a RULE_BINDING-PO (unlocked) or detect a conflict_instance
            for resolution (locked, per H-6).
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-1">
          <Label htmlFor="surface-forms">Candidate surface forms</Label>
          <Textarea
            id="surface-forms"
            placeholder={"hadith\nsalat\nsunnah"}
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={6}
          />
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        {result && (
          <div className="rounded border p-3 text-sm space-y-1">
            <p>
              <span className="text-muted-foreground">Outcome:</span>{" "}
              <span className="font-medium">{result.outcome}</span>
            </p>
            <p>
              <span className="text-muted-foreground">Matched concepts:</span>{" "}
              {result.matched_concept_ids.length}
            </p>
            {result.outcome === "conflict_detected" && (
              <p className="text-amber-700">
                Conflict detected — resolve via the row's conflict badge.
              </p>
            )}
            {result.outcome === "applied" && result.rule_binding_po_uuid && (
              <p className="text-emerald-700">RULE_BINDING-PO written.</p>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button onClick={onSubmit} disabled={mutation.isPending}>
            {mutation.isPending ? "Applying…" : "Apply"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
