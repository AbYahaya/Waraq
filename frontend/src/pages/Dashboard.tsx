import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api } from "@/lib/api";
import type { Project } from "@/lib/types";

export function DashboardPage(): JSX.Element {
  const qc = useQueryClient();
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
  });
  const [name, setName] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (name: string) => api.post<Project>("/projects", { name }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["projects"] });
      setName("");
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
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
        <p className="text-muted-foreground">One project per book.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Create a new project</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="flex gap-3 items-end">
            <div className="flex-1 space-y-2">
              <Label htmlFor="project-name">Name</Label>
              <Input
                id="project-name"
                placeholder="e.g. Sahih Bukhari Vol 1"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <Button type="submit" disabled={createMutation.isPending || name.trim().length === 0}>
              {createMutation.isPending ? "Creating…" : "Create"}
            </Button>
          </form>
          {createError && (
            <p className="text-sm text-destructive mt-2">{createError}</p>
          )}
        </CardContent>
      </Card>

      <section className="space-y-4">
        <h2 className="text-lg font-medium">Your projects</h2>
        {projectsQuery.isLoading && (
          <p className="text-sm text-muted-foreground">Loading…</p>
        )}
        {projectsQuery.isError && (
          <p className="text-sm text-destructive">
            {projectsQuery.error instanceof ApiError
              ? projectsQuery.error.detail
              : "Failed to load projects"}
          </p>
        )}
        {projectsQuery.data && projectsQuery.data.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No projects yet. Create your first one above.
          </p>
        )}
        {projectsQuery.data && projectsQuery.data.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {projectsQuery.data.map((p) => (
              <Card key={p.project_uuid} className="hover:bg-accent/30 transition-colors">
                <Link
                  to={`/projects/${p.project_uuid}`}
                  className="block p-5"
                >
                  <div className="font-medium">{p.name}</div>
                  <div className="text-xs text-muted-foreground mt-1 truncate">
                    {p.project_uuid}
                  </div>
                </Link>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
