/**
 * Phase 5 sub-batch M — admin admissions dashboard.
 *
 * Admin-only page: shows accounts awaiting approval, with approve /
 * reject actions. Only reachable when `account.is_admin === true`
 * (env-driven `ADMIN_EMAILS` allowlist on the backend).
 *
 * The page calls three endpoints:
 *   GET  /admin/admissions/pending
 *   POST /admin/admissions/{uuid}/approve
 *   POST /admin/admissions/{uuid}/reject
 *
 * Per the user's 2026-05-12 scope decision, approval grants full
 * access — no tiers, no subscription. Tier 0/1/2 + subscription /
 * inactivity / guest / trash are canon-deferred to a later sub-batch.
 */
import { useCallback, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface AdmissionAccount {
  account_uuid: string;
  email: string;
  display_name: string | null;
  approval_status: "pending" | "approved" | "rejected";
  approved_at: string | null;
  approved_by_account_uuid: string | null;
  rejection_reason: string | null;
  created_at: string;
}

interface AdmissionListResponse {
  accounts: AdmissionAccount[];
}

const PENDING_QUERY_KEY = ["admin", "admissions", "pending"] as const;

export function AdmissionsPage(): JSX.Element {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery<AdmissionListResponse>({
    queryKey: PENDING_QUERY_KEY,
    queryFn: () => api.get<AdmissionListResponse>("/admin/admissions/pending"),
  });

  const approveMutation = useMutation({
    mutationFn: (account_uuid: string) =>
      api.post<AdmissionAccount>(
        `/admin/admissions/${account_uuid}/approve`,
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PENDING_QUERY_KEY });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (params: { account_uuid: string; reason: string | null }) =>
      api.post<AdmissionAccount>(
        `/admin/admissions/${params.account_uuid}/reject`,
        { reason: params.reason },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PENDING_QUERY_KEY });
    },
  });

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-semibold mb-2">Admission requests</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Pending account applications. Approve to grant full access; reject
        with an optional reason. Canon §2.3 row 8 (partial — tier system
        deferred).
      </p>
      {isLoading && (
        <p className="text-sm text-muted-foreground">Loading…</p>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 text-sm rounded p-3">
          {error instanceof ApiError ? error.detail : String(error)}
        </div>
      )}
      {data && data.accounts.length === 0 && (
        <div className="text-sm text-muted-foreground italic">
          No pending applications.
        </div>
      )}
      {data && data.accounts.length > 0 && (
        <div className="space-y-3">
          {data.accounts.map((a) => (
            <AdmissionRow
              key={a.account_uuid}
              account={a}
              onApprove={() => approveMutation.mutate(a.account_uuid)}
              onReject={(reason) =>
                rejectMutation.mutate({ account_uuid: a.account_uuid, reason })
              }
              busy={
                (approveMutation.isPending &&
                  approveMutation.variables === a.account_uuid) ||
                (rejectMutation.isPending &&
                  rejectMutation.variables?.account_uuid === a.account_uuid)
              }
            />
          ))}
        </div>
      )}
      {(approveMutation.error || rejectMutation.error) && (
        <div className="mt-4 bg-red-50 border border-red-200 text-red-800 text-sm rounded p-3">
          {approveMutation.error instanceof ApiError
            ? approveMutation.error.detail
            : rejectMutation.error instanceof ApiError
              ? rejectMutation.error.detail
              : "Action failed"}
        </div>
      )}
    </div>
  );
}

function AdmissionRow({
  account,
  onApprove,
  onReject,
  busy,
}: {
  account: AdmissionAccount;
  onApprove: () => void;
  onReject: (reason: string | null) => void;
  busy: boolean;
}): JSX.Element {
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");

  const confirmReject = useCallback(() => {
    onReject(reason.trim() || null);
    setRejecting(false);
    setReason("");
  }, [onReject, reason]);

  return (
    <div className="border rounded-lg p-4 bg-card">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="font-medium">{account.email}</div>
          {account.display_name && (
            <div className="text-sm text-muted-foreground">
              {account.display_name}
            </div>
          )}
          <div className="text-xs text-muted-foreground mt-1">
            Applied: {new Date(account.created_at).toLocaleString()}
          </div>
        </div>
        {!rejecting && (
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={onApprove}
              disabled={busy}
            >
              Approve
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setRejecting(true)}
              disabled={busy}
            >
              Reject
            </Button>
          </div>
        )}
      </div>
      {rejecting && (
        <div className="mt-3 space-y-2">
          <Label htmlFor={`reason-${account.account_uuid}`}>
            Rejection reason (optional, shown on next login attempt)
          </Label>
          <Input
            id={`reason-${account.account_uuid}`}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Application incomplete"
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="destructive"
              onClick={confirmReject}
              disabled={busy}
            >
              Confirm reject
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setRejecting(false);
                setReason("");
              }}
              disabled={busy}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
