/**
 * Project-level release-gate badge + Start-translation action.
 *
 * Lives at the top of the workspace left rail. Shows the canonical
 * three-state outcome (uebersetzungsreif / uebersetzbar_mit_warnung /
 * blockiert) plus the action to write the `uebersetzungsstart`
 * Decision Event — the only path that lets a translation Job start
 * (DBB §B Abkürzung 5: no auto-trigger).
 */

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import { qk, queries } from "@/lib/queries";
import type { ReleaseGate } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATE_LABEL: Record<ReleaseGate["state"], string> = {
  uebersetzungsreif: "ready",
  uebersetzbar_mit_warnung: "ready (warnings)",
  blockiert: "blocked",
  nicht_erreichbar: "n/a",
  freigabeschranken_pruefung: "checking",
};

const STATE_TONE: Record<ReleaseGate["state"], string> = {
  uebersetzungsreif: "bg-emerald-100 text-emerald-800",
  uebersetzbar_mit_warnung: "bg-amber-100 text-amber-800",
  blockiert: "bg-destructive/10 text-destructive",
  nicht_erreichbar: "bg-muted text-muted-foreground",
  freigabeschranken_pruefung: "bg-blue-100 text-blue-800",
};

export interface ReleaseGatePanelProps {
  projectUuid: string;
}

export function ReleaseGatePanel({ projectUuid }: ReleaseGatePanelProps): JSX.Element {
  const qc = useQueryClient();
  const gateQ = useQuery(queries.releaseGate(projectUuid));
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [startOpen, setStartOpen] = useState(false);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const confirmWarningMutation = useMutation({
    mutationFn: (note: string) =>
      api.post<{ decision_event_uuid: string }>(
        `/projects/${projectUuid}/release-gate/confirm-warning`,
        { note },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.releaseGate(projectUuid) });
      setConfirmOpen(false);
      setNote("");
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Failed"),
  });

  const startTranslationMutation = useMutation({
    mutationFn: (note: string) =>
      api.post<{ decision_event_uuid: string }>(
        `/projects/${projectUuid}/release-gate/start-translation`,
        { note },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.releaseGate(projectUuid) });
      setStartOpen(false);
      setNote("");
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Failed"),
  });

  return (
    <div className="px-3 py-3 border-b">
      <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
        Release gate
      </div>

      {gateQ.isLoading && (
        <p className="text-sm text-muted-foreground">Evaluating…</p>
      )}
      {gateQ.isError && (
        <p className="text-sm text-destructive">
          {gateQ.error instanceof ApiError ? gateQ.error.detail : "Failed"}
        </p>
      )}
      {gateQ.data && (
        <>
          <span
            className={cn(
              "text-xs px-2 py-0.5 rounded-full font-medium",
              STATE_TONE[gateQ.data.state],
            )}
          >
            {STATE_LABEL[gateQ.data.state]}
          </span>
          {gateQ.data.blocking_reasons.length > 0 && (
            <ul className="text-xs text-destructive mt-2 space-y-1 list-disc pl-4">
              {gateQ.data.blocking_reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
          {gateQ.data.warnings.length > 0 && (
            <ul className="text-xs text-amber-700 mt-2 space-y-1 list-disc pl-4">
              {gateQ.data.warnings.slice(0, 3).map((w) => (
                <li key={w}>{w}</li>
              ))}
              {gateQ.data.warnings.length > 3 && (
                <li className="list-none">
                  +{gateQ.data.warnings.length - 3} more…
                </li>
              )}
            </ul>
          )}

          <div className="flex flex-col gap-2 mt-3">
            {gateQ.data.requires_confirmation && (
              <Button size="sm" onClick={() => setConfirmOpen(true)}>
                Confirm warnings
              </Button>
            )}
            {(gateQ.data.state === "uebersetzungsreif" ||
              gateQ.data.state === "uebersetzbar_mit_warnung") && (
              <Button size="sm" variant="outline" onClick={() => setStartOpen(true)}>
                Start translation
              </Button>
            )}
          </div>
        </>
      )}

      {error && <p className="text-xs text-destructive mt-2">{error}</p>}

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm warnings</DialogTitle>
            <DialogDescription>
              Writes a `freigabe_mit_warnung` Decision Event so the gate
              clears to `uebersetzbar_mit_warnung`. The warnings stay in
              the audit trail; this only acknowledges them.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            placeholder="Optional note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => confirmWarningMutation.mutate(note)}
              disabled={confirmWarningMutation.isPending}
            >
              {confirmWarningMutation.isPending ? "Confirming…" : "Confirm"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={startOpen} onOpenChange={setStartOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Start translation</DialogTitle>
            <DialogDescription>
              Writes the `uebersetzungsstart` Decision Event. Per DBB
              Abkürzung 5, this is the ONLY path that authorizes a
              translation Job — the gate has no auto-trigger.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            placeholder="Optional note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setStartOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => startTranslationMutation.mutate(note)}
              disabled={startTranslationMutation.isPending}
            >
              {startTranslationMutation.isPending ? "Writing…" : "Authorize"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
