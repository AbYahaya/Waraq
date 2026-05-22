import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, FolderPlus, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api } from "@/lib/api";
import type { Project } from "@/lib/types";
import { useAuthStore } from "@/store/auth";

export function DashboardPage(): JSX.Element {
  const qc = useQueryClient();
  const account = useAuthStore((s) => s.account);
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
  });
  const [name, setName] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const createMutation = useMutation({
    mutationFn: (name: string) => api.post<Project>("/projects", { name }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["projects"] });
      setName("");
      setCreateOpen(false);
    },
    onError: (err) =>
      setCreateError(err instanceof ApiError ? err.detail : "Failed to create project"),
  });

  const onSubmit = (e: FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    setCreateError(null);
    createMutation.mutate(name);
  };

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-8">
      <section className="flex flex-col gap-4 rounded-[2rem] border border-border/80 bg-card/90 p-6 shadow-sm sm:flex-row sm:items-end sm:justify-between sm:p-8">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">
            Dashboard
          </p>
          <h2 className="mt-3 text-4xl font-semibold text-[#1d221d]">
            Welcome back{account?.display_name ? `, ${account.display_name}` : ""}.
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
            Manage translation projects, upload source scans, and move each book from OCR review to export.
          </p>
        </div>
        <Button
          size="lg"
          onClick={() => {
            setCreateError(null);
            setCreateOpen(true);
          }}
          className="rounded-2xl px-6"
        >
          <FolderPlus className="h-4 w-4" />
          New Project
        </Button>
      </section>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="rounded-[2rem] border border-border/80 bg-card/95 p-6 shadow-sm sm:p-8">
          {projectsQuery.data && projectsQuery.data.length === 0 && (
            <div className="flex min-h-[420px] flex-col items-center justify-center text-center">
              <div className="flex h-28 w-28 items-center justify-center rounded-full bg-[#f3eee4] text-primary">
                <BookOpen className="h-12 w-12" strokeWidth={1.5} />
              </div>
              <h3 className="mt-8 text-3xl font-semibold text-[#1d221d]">
                No projects yet
              </h3>
              <p className="mt-4 max-w-md text-sm leading-6 text-muted-foreground">
                Create your first project to start reviewing scans, refining OCR, and exporting a finished translation package.
              </p>
              <Button
                className="mt-8 rounded-2xl px-6"
                onClick={() => {
                  setCreateError(null);
                  setCreateOpen(true);
                }}
              >
                <FolderPlus className="h-4 w-4" />
                Create Project
              </Button>
            </div>
          )}

          {projectsQuery.data && projectsQuery.data.length > 0 && (
            <div className="space-y-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-2xl font-semibold text-[#1d221d]">
                    Your projects
                  </h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    One project per book, with the workspace opening directly into page review.
                  </p>
                </div>
                <div className="hidden rounded-2xl border border-border/80 bg-background/70 px-4 py-3 text-right sm:block">
                  <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    Total
                  </div>
                  <div className="mt-1 text-2xl font-semibold text-[#1d221d]">
                    {projectsQuery.data.length}
                  </div>
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {projectsQuery.data.map((p, index) => (
                  <Card
                    key={p.project_uuid}
                    className="overflow-hidden rounded-[1.5rem] border-border/80 bg-[#fcfaf5] shadow-none transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-md"
                  >
                    <Link to={`/projects/${p.project_uuid}`} className="block p-5">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                            Project {index + 1}
                          </div>
                          <div className="mt-2 text-lg font-semibold text-[#1d221d]">
                            {p.name}
                          </div>
                        </div>
                        <div className="rounded-full bg-[#efe6d2] px-3 py-1 text-[11px] font-medium text-primary">
                          Open
                        </div>
                      </div>
                      <div className="mt-8 text-xs text-muted-foreground">
                        {p.project_uuid}
                      </div>
                    </Link>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {projectsQuery.isLoading && (
            <p className="text-sm text-muted-foreground">Loading projects…</p>
          )}
          {projectsQuery.isError && (
            <p className="text-sm text-destructive">
              {projectsQuery.error instanceof ApiError
                ? projectsQuery.error.detail
                : "Failed to load projects"}
            </p>
          )}
        </div>

        <div className="space-y-4">
          <Card className="rounded-[1.75rem] border-border/80 bg-[#163927] text-white shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-white">
                <Sparkles className="h-4 w-4 text-[#c8a867]" />
                Focus
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-white/78">
              <p>Use the dashboard for new projects and the workspace for OCR, translation review, and exports.</p>
              <p>The redesign keeps the advanced controls, but shifts them into calmer secondary panels.</p>
            </CardContent>
          </Card>

          <Card className="rounded-[1.75rem] border-border/80 bg-card/95 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-[#1d221d]">Quick actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button
                variant="outline"
                className="w-full justify-start rounded-xl"
                onClick={() => {
                  setCreateError(null);
                  setCreateOpen(true);
                }}
              >
                <FolderPlus className="h-4 w-4" />
                Create a project
              </Button>
              <Button asChild variant="outline" className="w-full justify-start rounded-xl">
                <Link to="/diagnostics">Open diagnostics</Link>
              </Button>
              <Button asChild variant="outline" className="w-full justify-start rounded-xl">
                <Link to="/directories">Open directories</Link>
              </Button>
              <Button asChild variant="outline" className="w-full justify-start rounded-xl">
                <Link to="/trash">Open trash</Link>
              </Button>
              {account?.is_admin && (
                <Button asChild variant="ghost" className="w-full justify-start rounded-xl">
                  <Link to="/admin">Open admin panel</Link>
                </Button>
              )}
            </CardContent>
          </Card>
        </div>
      </section>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="rounded-[1.75rem] border-border/80 bg-[#fbf7f0]">
          <DialogHeader>
            <DialogTitle>Create a new project</DialogTitle>
            <DialogDescription>
              Start one project per book. You can upload the source file as soon as the project is created.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="project-name">Project name</Label>
              <Input
                id="project-name"
                placeholder="e.g. Sahih al-Bukhari, Volume 1"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="rounded-xl border-border/80 bg-white"
              />
            </div>
            {createError && <p className="text-sm text-destructive">{createError}</p>}
            <div className="flex justify-end gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => setCreateOpen(false)}
                className="rounded-xl"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending || name.trim().length === 0}
                className="rounded-xl"
              >
                {createMutation.isPending ? "Creating…" : "Create project"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
