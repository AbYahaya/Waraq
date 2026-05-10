/**
 * §2.1 / §2.2 — In-app notification panel + per-user toggle controls.
 *
 * Renders a bell-icon trigger that opens a dropdown listing the user's
 * notifications (newest first). Includes per-channel toggles (email
 * + in-app) so the user controls both channels per §2.2.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface NotificationDto {
  notification_uuid: string;
  kind: string;
  title: string;
  body: string;
  created_at: string;
  read_at: string | null;
  email_sent_at: string | null;
}

interface NotificationListResponse {
  items: NotificationDto[];
  unread_count: number;
}

interface PreferencesDto {
  email_notifications_enabled: boolean;
  in_app_notifications_enabled: boolean;
}

const QK = {
  list: () => ["me", "notifications"] as const,
  prefs: () => ["me", "notifications", "preferences"] as const,
};

export function NotificationPanel(): JSX.Element {
  const [open, setOpen] = useState(false);
  const qc = useQueryClient();
  const listQ = useQuery({
    queryKey: QK.list(),
    queryFn: () => api.get<NotificationListResponse>("/me/notifications"),
    refetchInterval: 60_000,
  });
  const prefsQ = useQuery({
    queryKey: QK.prefs(),
    queryFn: () => api.get<PreferencesDto>("/me/notifications/preferences"),
    enabled: open,
  });

  const markOneMut = useMutation({
    mutationFn: (uuid: string) =>
      api.post<void>(`/me/notifications/${uuid}/read`),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK.list() }),
  });
  const markAllMut = useMutation({
    mutationFn: () => api.post<{ marked: number }>("/me/notifications/read-all"),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK.list() }),
  });
  const updatePrefsMut = useMutation({
    mutationFn: (patch: Partial<PreferencesDto>) =>
      api.put<PreferencesDto>("/me/notifications/preferences", patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK.prefs() }),
  });

  const unread = listQ.data?.unread_count ?? 0;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "relative inline-flex items-center gap-1 px-2 py-1 rounded text-sm hover:bg-accent",
          open && "bg-accent",
        )}
        aria-label={`Notifications (${unread} unread)`}
      >
        <BellIcon />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 inline-flex items-center justify-center min-w-[16px] h-4 px-1 rounded-full bg-destructive text-destructive-foreground text-[10px] font-semibold">
            {unread}
          </span>
        )}
      </button>

      {open && (
        <div
          className="absolute right-0 mt-2 w-96 max-h-[70vh] overflow-auto bg-card border rounded shadow-lg z-50"
          role="dialog"
          aria-label="Notifications"
        >
          <div className="px-3 py-2 border-b flex items-center justify-between">
            <span className="text-sm font-medium">Notifications</span>
            <div className="flex items-center gap-2">
              {unread > 0 && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => markAllMut.mutate()}
                  disabled={markAllMut.isPending}
                >
                  Mark all read
                </Button>
              )}
            </div>
          </div>

          {prefsQ.data && (
            <div className="px-3 py-2 border-b text-xs space-y-1 bg-muted/30">
              <div className="flex items-center justify-between">
                <span>In-app notifications</span>
                <input
                  type="checkbox"
                  checked={prefsQ.data.in_app_notifications_enabled}
                  onChange={(e) =>
                    updatePrefsMut.mutate({
                      in_app_notifications_enabled: e.target.checked,
                    })
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <span>Email notifications</span>
                <input
                  type="checkbox"
                  checked={prefsQ.data.email_notifications_enabled}
                  onChange={(e) =>
                    updatePrefsMut.mutate({
                      email_notifications_enabled: e.target.checked,
                    })
                  }
                />
              </div>
            </div>
          )}

          <div className="divide-y">
            {listQ.data && listQ.data.items.length === 0 && (
              <p className="text-sm text-muted-foreground p-3">No notifications.</p>
            )}
            {listQ.data?.items.map((n) => (
              <div
                key={n.notification_uuid}
                className={cn(
                  "px-3 py-2 hover:bg-accent/40 cursor-pointer",
                  n.read_at === null && "bg-accent/20",
                )}
                onClick={() => {
                  if (n.read_at === null) markOneMut.mutate(n.notification_uuid);
                }}
              >
                <div className="text-xs text-muted-foreground flex items-center gap-2">
                  <span>{new Date(n.created_at).toLocaleString()}</span>
                  {n.email_sent_at && (
                    <span className="text-emerald-700" title="Email sent">
                      ✉
                    </span>
                  )}
                  {n.read_at === null && (
                    <span className="text-destructive font-medium">●</span>
                  )}
                </div>
                <div className="font-medium text-sm">{n.title}</div>
                <div className="text-xs text-muted-foreground whitespace-pre-line">
                  {n.body}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function BellIcon(): JSX.Element {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </svg>
  );
}
