/**
 * Admin panel — accounts list + projects list per account.
 *
 * Gated by `WARAQ_ADMIN_EMAILS` server-side. The link only renders in
 * the AppShell when the current account email is in the local config
 * (we don't ship the admin allowlist to clients; the server returns
 * 403 if a non-admin hits the page directly).
 */

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface AdminAccount {
  account_uuid: string;
  email: string;
  display_name: string | null;
  active: boolean;
  approval_status: "pending" | "approved" | "rejected";
  is_admin: boolean;
}

interface AdminProject {
  project_uuid: string;
  account_uuid: string;
  name: string;
  active: boolean;
}

export function AdminPage(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const accountsQ = useQuery({
    queryKey: ["admin", "accounts"],
    queryFn: () => api.get<AdminAccount[]>("/admin/accounts"),
  });
  const [selectedAccount, setSelectedAccount] = useState<string | null>(
    searchParams.get("account") || null,
  );

  const projectsQ = useQuery({
    queryKey: ["admin", "projects", selectedAccount],
    queryFn: () =>
      api.get<AdminProject[]>(
        selectedAccount
          ? `/admin/projects?account_uuid=${selectedAccount}`
          : "/admin/projects",
      ),
  });

  useEffect(() => {
    setSelectedAccount(searchParams.get("account") || null);
  }, [searchParams]);

  useEffect(() => {
    if (!accountsQ.data || selectedAccount === null) return;
    if (accountsQ.data.some((account) => account.account_uuid === selectedAccount)) return;
    setSelectedAccount(null);
  }, [accountsQ.data, selectedAccount]);

  useEffect(() => {
    const next = new URLSearchParams(searchParams);
    if (selectedAccount === null) {
      next.delete("account");
    } else {
      next.set("account", selectedAccount);
    }
    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, selectedAccount, setSearchParams]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Admin panel</h1>
        <p className="text-muted-foreground">
          Accounts, access states, account levels, and projects across the deployment.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <AdminMetric
          label="Accounts"
          value={accountsQ.data?.length ?? 0}
          helper="Visible active users"
        />
        <AdminMetric
          label="Pending"
          value={(accountsQ.data ?? []).filter((a) => a.approval_status === "pending").length}
          helper="Needs admission review"
        />
        <Card className="rounded-[1.5rem] border-border/80">
          <CardContent className="flex h-full flex-col justify-between gap-4 p-5">
            <div>
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                Admissions
              </div>
              <div className="mt-2 text-sm text-muted-foreground">
                Review applications and grant or reject access.
              </div>
            </div>
            <Button asChild variant="outline" className="w-fit rounded-xl">
              <Link to="/admin/admissions">Open admissions</Link>
            </Button>
          </CardContent>
        </Card>
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
                    <div className="mt-1 flex flex-wrap gap-1">
                      <span className={cn(
                        "rounded-full px-2 py-0.5 text-[10px] font-medium",
                        a.approval_status === "approved" && "bg-green-100 text-green-800",
                        a.approval_status === "pending" && "bg-amber-100 text-amber-800",
                        a.approval_status === "rejected" && "bg-red-100 text-red-800",
                      )}>
                        {a.approval_status}
                      </span>
                      <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                        {a.is_admin ? "administrator" : "publisher"}
                      </span>
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
                      project {p.project_uuid} · account {p.account_uuid} ·{" "}
                      {p.active ? "active" : "trashed"}
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

function AdminMetric({
  label,
  value,
  helper,
}: {
  label: string;
  value: number;
  helper: string;
}): JSX.Element {
  return (
    <Card className="rounded-[1.5rem] border-border/80">
      <CardContent className="p-5">
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
          {label}
        </div>
        <div className="mt-2 text-3xl font-semibold text-[#1d221d]">{value}</div>
        <div className="mt-1 text-sm text-muted-foreground">{helper}</div>
      </CardContent>
    </Card>
  );
}
