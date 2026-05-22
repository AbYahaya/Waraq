/**
 * Sub-batch P (out-of-phase, 2026-05-13) — delete-project confirmation dialog.
 *
 * Per H-5 the backend treats delete as inactivation (`active=false`),
 * not a hard row delete. The Project UUID survives forever; the row
 * just becomes unreachable through the API (every ownership helper
 * 404s on inactive projects).
 *
 * On success: invalidates the project list query and navigates the
 * user back to the projects index (`/`). Any in-flight `ocr_auto_run`
 * or `translation` Job on this project gets a cancel flag set
 * server-side; the runner cooperatively bails on its next iteration.
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ApiError, api } from "@/lib/api";
import { qk } from "@/lib/queries";

export interface DeleteProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectUuid: string;
  projectName: string;
}

export function DeleteProjectDialog({
  open,
  onOpenChange,
  projectUuid,
  projectName,
}: DeleteProjectDialogProps): JSX.Element {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const deleteMutation = useMutation({
    mutationFn: () => api.delete<null>(`/projects/${projectUuid}`),
    onSuccess: () => {
      // Project list lost an entry; in-flight job polls should stop.
      void qc.invalidateQueries({ queryKey: qk.projects() });
      void qc.invalidateQueries({ queryKey: qk.projectTrash() });
      // Drop any cached page/segment data scoped to this project so a
      // back-button can't show a stale workspace.
      qc.removeQueries({ queryKey: qk.project(projectUuid) });
      qc.removeQueries({ queryKey: qk.projectPages(projectUuid) });
      onOpenChange(false);
      navigate("/", { replace: true });
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.detail : "Delete failed"),
  });

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!deleteMutation.isPending) {
          setError(null);
          onOpenChange(next);
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete project?</DialogTitle>
          <DialogDescription>
            <span className="font-medium">{projectName}</span> will be hidden
            from your projects list. Pages, OCR results, translations, and
            provenance history are preserved in the database (H-5: UUIDs
            are immutable). You can restore it from Trash for 10 days. Any
            running OCR or translation job on this project will be cancelled.
          </DialogDescription>
        </DialogHeader>
        {error && (
          <p className="text-xs text-destructive" role="alert">
            {error}
          </p>
        )}
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={deleteMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={() => {
              setError(null);
              deleteMutation.mutate();
            }}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? "Deleting…" : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
