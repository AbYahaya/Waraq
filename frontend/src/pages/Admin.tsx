/**
 * Admin panel — accounts list + projects list per account.
 *
 * Gated by `WARAQ_ADMIN_EMAILS` server-side. The link only renders in
 * the AppShell when the current account email is in the local config
 * (we don't ship the admin allowlist to clients; the server returns
 * 403 if a non-admin hits the page directly).
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface AdminAccount {
  account_uuid: string;
  email: string;
  display_name: string | null;
  active: boolean;
}

interface AdminProject {
  project_uuid: string;
  account_uuid: string;
  name: string;
  active: boolean;
}

export function AdminPage(): JSX.Element {
  const accountsQ = useQuery({
    queryKey: ["admin", "accounts"],
    queryFn: () => api.get<AdminAccount[]>("/admin/accounts"),
  });
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);

  const projectsQ = useQuery({
    queryKey: ["admin", "projects", selectedAccount],
    queryFn: () =>
      api.get<AdminProject[]>(
        selectedAccount
          ? `/admin/projects?account_uuid=${selectedAccount}`
          : "/admin/projects",
      ),
  });

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Admin panel</h1>
        <p className="text-muted-foreground">
          Accounts and projects across the deployment.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[20rem_1fr]">
        <Card className="lg:max-h-[36rem] overflow-y-auto">
          <CardHeader className="sticky top-0 bg-card border-b">
            <CardTitle className="text-base">Accounts</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {accountsQ.isLoading && (
              <p className="text-sm text-muted-foreground p-3">Loading…</p>
            )}
            {accountsQ.isError && (
              <p className="text-sm text-destructive p-3">
                {accountsQ.error instanceof ApiError
                  ? accountsQ.error.detail
                  : "Failed to load accounts"}
              </p>
            )}
            <ul className="divide-y">
              <li>
                <button
                  type="button"
                  onClick={() => setSelectedAccount(null)}
                  className={cn(
                    "w-full text-left px-3 py-2 text-sm hover:bg-accent",
                    selectedAccount === null && "bg-accent",
                  )}
                >
                  <span className="font-medium">All accounts</span>
                </button>
              </li>
              {(accountsQ.data ?? []).map((a) => (
                <li key={a.account_uuid}>
                  <button
                    type="button"
                    onClick={() => setSelectedAccount(a.account_uuid)}
                    className={cn(
                      "w-full text-left px-3 py-2 text-sm hover:bg-accent",
                      selectedAccount === a.account_uuid && "bg-accent",
                    )}
                  >
                    <div className="font-medium truncate">{a.email}</div>
                    <div className="text-xs text-muted-foreground truncate">
                      {a.display_name ?? "—"}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b">
            <CardTitle className="text-base">
              Projects {selectedAccount ? "(for selected account)" : "(all)"}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {projectsQ.isLoading && (
              <p className="text-sm text-muted-foreground p-3">Loading…</p>
            )}
            {projectsQ.isError && (
              <p className="text-sm text-destructive p-3">
                {projectsQ.error instanceof ApiError
                  ? projectsQ.error.detail
                  : "Failed to load projects"}
              </p>
            )}
            {projectsQ.data && projectsQ.data.length === 0 && (
              <p className="text-sm text-muted-foreground p-3">No projects.</p>
            )}
            {projectsQ.data && projectsQ.data.length > 0 && (
              <ul className="divide-y">
                {projectsQ.data.map((p) => (
                  <li key={p.project_uuid} className="px-3 py-2 text-sm">
                    <div className="font-medium">{p.name}</div>
                    <div className="text-xs text-muted-foreground truncate">
                      project {p.project_uuid} · account {p.account_uuid}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
