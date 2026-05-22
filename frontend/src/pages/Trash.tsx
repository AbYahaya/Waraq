import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RotateCcw, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, api } from "@/lib/api";
import { qk, queries } from "@/lib/queries";
import type { Project, TrashedProject } from "@/lib/types";

export function TrashPage(): JSX.Element {
  const qc = useQueryClient();
  const trashQ = useQuery(queries.projectTrash());

  const restoreMutation = useMutation({
    mutationFn: (projectUuid: string) =>
      api.post<Project>(`/projects/${projectUuid}/restore`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.projects() });
      void qc.invalidateQueries({ queryKey: qk.projectTrash() });
    },
  });

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <section className="rounded-[2rem] border border-border/80 bg-card p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-100 text-amber-800">
            <Trash2 className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
              Project recovery
            </p>
            <h2 className="mt-2 text-3xl font-semibold text-[#1d221d]">Trash</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
              Deleted projects are hidden from the dashboard but can be restored for
              10 days. OCR, translations, provenance, and UUIDs remain preserved.
            </p>
          </div>
        </div>
      </section>

      {trashQ.isLoading && (
        <p className="text-sm text-muted-foreground">Loading trash…</p>
      )}
      {trashQ.isError && (
        <p className="text-sm text-destructive">
          {trashQ.error instanceof ApiError
            ? trashQ.error.detail
            : "Failed to load trash"}
        </p>
      )}

      {trashQ.data && trashQ.data.length === 0 && (
        <Card className="rounded-[1.75rem] border-border/80">
          <CardContent className="py-10 text-center">
            <p className="text-sm text-muted-foreground">Trash is empty.</p>
            <Button asChild variant="outline" className="mt-4 rounded-xl">
              <Link to="/">Back to dashboard</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {trashQ.data && trashQ.data.length > 0 && (
        <div className="grid gap-4">
          {trashQ.data.map((project) => (
            <TrashProjectCard
              key={project.project_uuid}
              project={project}
              busy={
                restoreMutation.isPending &&
                restoreMutation.variables === project.project_uuid
              }
              onRestore={() => restoreMutation.mutate(project.project_uuid)}
            />
          ))}
        </div>
      )}

      {restoreMutation.isError && (
        <p className="rounded-xl border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
          {restoreMutation.error instanceof ApiError
            ? restoreMutation.error.detail
            : "Restore failed"}
        </p>
      )}
    </div>
  );
}

function TrashProjectCard({
  project,
  busy,
  onRestore,
}: {
  project: TrashedProject;
  busy: boolean;
  onRestore: () => void;
}): JSX.Element {
  return (
    <Card className="rounded-[1.75rem] border-border/80 bg-[#fcfaf5] shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle className="text-xl text-[#1d221d]">{project.name}</CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              Deleted {formatDate(project.deleted_at)} · project {project.project_uuid}
            </p>
          </div>
          <span className="w-fit rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
            {project.restorable
              ? `${project.days_remaining} day${project.days_remaining === 1 ? "" : "s"} left`
              : "Restore expired"}
          </span>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground">
          Restore window closes {formatDate(project.restore_until)}.
        </p>
        <Button
          onClick={onRestore}
          disabled={!project.restorable || busy}
          className="rounded-xl"
        >
          <RotateCcw className="h-4 w-4" />
          {busy ? "Restoring…" : "Restore project"}
        </Button>
      </CardContent>
    </Card>
  );
}

function formatDate(value: string | null): string {
  if (!value) return "unknown";
  return new Date(value).toLocaleString();
}
