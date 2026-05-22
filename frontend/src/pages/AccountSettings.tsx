import { useEffect, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, KeyRound, UserRound, WalletCards } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api } from "@/lib/api";
import type { Account } from "@/lib/types";
import { useAuthStore } from "@/store/auth";

interface PreferencesDto {
  email_notifications_enabled: boolean;
  in_app_notifications_enabled: boolean;
}

interface AccountUsageResponse {
  general: {
    projects: number;
    active_projects: number;
    uploaded_books: number;
    pages: number;
    ocr_pages: number;
    translated_pages: number;
    segments: number;
    translated_segments: number;
    storage_bytes: number;
  };
  api: {
    provider_calls: Record<string, number>;
    jobs_by_type: Record<string, number>;
    jobs_by_state: Record<string, number>;
    ocr_provenance_objects: number;
    translation_provenance_objects: number;
    token_usage_available: boolean;
    total_input_tokens: number | null;
    total_output_tokens: number | null;
    estimated_cost_usd: number | null;
    note: string;
  };
}

const QK = {
  profile: () => ["me", "profile"] as const,
  prefs: () => ["me", "notifications", "preferences"] as const,
  usage: () => ["me", "usage"] as const,
};

export function AccountSettingsPage(): JSX.Element {
  const qc = useQueryClient();
  const account = useAuthStore((s) => s.account);
  const setAccount = useAuthStore((s) => s.setAccount);

  const profileQ = useQuery({
    queryKey: QK.profile(),
    queryFn: () => api.get<Account>("/me/profile"),
  });
  const prefsQ = useQuery({
    queryKey: QK.prefs(),
    queryFn: () => api.get<PreferencesDto>("/me/notifications/preferences"),
  });
  const usageQ = useQuery({
    queryKey: QK.usage(),
    queryFn: () => api.get<AccountUsageResponse>("/me/usage"),
  });

  const profile = profileQ.data ?? account;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <section className="rounded-[2rem] border border-border/80 bg-[#fbf7ef] p-6 shadow-sm sm:p-8">
        <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">
          Account
        </p>
        <h2 className="mt-3 text-4xl font-semibold text-[#1d221d]">Settings and usage</h2>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
          Manage your profile, notification preferences, password, and review how much
          work this account has processed.
        </p>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <div className="space-y-6">
          <ProfileCard
            profile={profile}
            onUpdated={(next) => {
              setAccount(next);
              void qc.invalidateQueries({ queryKey: QK.profile() });
            }}
          />
          <PasswordCard />
          <NotificationPrefsCard
            prefs={prefsQ.data}
            loading={prefsQ.isLoading}
            onSaved={() => void qc.invalidateQueries({ queryKey: QK.prefs() })}
          />
        </div>

        <UsagePanel usage={usageQ.data} loading={usageQ.isLoading} error={usageQ.error} />
      </div>
    </div>
  );
}

function ProfileCard({
  profile,
  onUpdated,
}: {
  profile: Account | null;
  onUpdated: (account: Account) => void;
}): JSX.Element {
  const [displayName, setDisplayName] = useState(profile?.display_name ?? "");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setDisplayName(profile?.display_name ?? "");
  }, [profile?.display_name]);

  const mutation = useMutation({
    mutationFn: () =>
      api.put<Account>("/me/profile", {
        display_name: displayName.trim() || null,
      }),
    onSuccess: (next) => {
      onUpdated(next);
      setMessage("Profile updated.");
    },
    onError: (err) =>
      setMessage(err instanceof ApiError ? err.detail : "Could not update profile."),
  });

  return (
    <Card className="rounded-[1.75rem] border-border/80 shadow-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserRound className="h-5 w-5 text-primary" />
          Profile
        </CardTitle>
        <CardDescription>Your account identity and display name.</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="grid gap-4 sm:grid-cols-2"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            setMessage(null);
            mutation.mutate();
          }}
        >
          <div className="space-y-2">
            <Label>Email</Label>
            <Input value={profile?.email ?? ""} disabled />
          </div>
          <div className="space-y-2">
            <Label>Display name</Label>
            <Input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
          </div>
          <div className="flex items-center gap-3 sm:col-span-2">
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving..." : "Save profile"}
            </Button>
            <span className="text-xs text-muted-foreground">
              {profile?.is_admin ? "Administrator" : "Publisher"} ·{" "}
              {profile?.approval_status ?? "approved"}
            </span>
          </div>
          {message !== null ? <p className="text-sm text-muted-foreground sm:col-span-2">{message}</p> : null}
        </form>
      </CardContent>
    </Card>
  );
}

function PasswordCard(): JSX.Element {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      api.put<void>("/me/password", {
        current_password: currentPassword,
        new_password: newPassword,
      }),
    onSuccess: () => {
      setCurrentPassword("");
      setNewPassword("");
      setMessage("Password updated.");
    },
    onError: (err) =>
      setMessage(err instanceof ApiError ? err.detail : "Could not update password."),
  });

  return (
    <Card className="rounded-[1.75rem] border-border/80 shadow-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <KeyRound className="h-5 w-5 text-primary" />
          Security
        </CardTitle>
        <CardDescription>Change your login password.</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="grid gap-4 sm:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault();
            setMessage(null);
            mutation.mutate();
          }}
        >
          <div className="space-y-2">
            <Label>Current password</Label>
            <Input
              type="password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              autoComplete="current-password"
            />
          </div>
          <div className="space-y-2">
            <Label>New password</Label>
            <Input
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              autoComplete="new-password"
            />
          </div>
          <div className="flex items-center gap-3 sm:col-span-2">
            <Button type="submit" disabled={mutation.isPending || newPassword.length < 8}>
              {mutation.isPending ? "Saving..." : "Change password"}
            </Button>
            <span className="text-xs text-muted-foreground">Minimum 8 characters.</span>
          </div>
          {message !== null ? <p className="text-sm text-muted-foreground sm:col-span-2">{message}</p> : null}
        </form>
      </CardContent>
    </Card>
  );
}

function NotificationPrefsCard({
  prefs,
  loading,
  onSaved,
}: {
  prefs: PreferencesDto | undefined;
  loading: boolean;
  onSaved: () => void;
}): JSX.Element {
  const mutation = useMutation({
    mutationFn: (patch: Partial<PreferencesDto>) =>
      api.put<PreferencesDto>("/me/notifications/preferences", patch),
    onSuccess: onSaved,
  });

  return (
    <Card className="rounded-[1.75rem] border-border/80 shadow-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bell className="h-5 w-5 text-primary" />
          Notifications
        </CardTitle>
        <CardDescription>Choose where workflow alerts should appear.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? <p className="text-sm text-muted-foreground">Loading preferences...</p> : null}
        {prefs !== undefined ? (
          <>
            <ToggleRow
              label="In-app notifications"
              description="Show workflow updates in the bell panel."
              checked={prefs.in_app_notifications_enabled}
              onChange={(checked) => mutation.mutate({ in_app_notifications_enabled: checked })}
            />
            <ToggleRow
              label="Email notifications"
              description="Send important workflow alerts by email when configured."
              checked={prefs.email_notifications_enabled}
              onChange={(checked) => mutation.mutate({ email_notifications_enabled: checked })}
            />
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}

function ToggleRow({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}): JSX.Element {
  return (
    <label className="flex items-center justify-between gap-4 rounded-2xl border bg-muted/20 px-4 py-3">
      <span>
        <span className="block text-sm font-medium">{label}</span>
        <span className="block text-xs text-muted-foreground">{description}</span>
      </span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
    </label>
  );
}

function UsagePanel({
  usage,
  loading,
  error,
}: {
  usage: AccountUsageResponse | undefined;
  loading: boolean;
  error: unknown;
}): JSX.Element {
  return (
    <div className="space-y-6">
      <Card className="rounded-[1.75rem] border-border/80 shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <WalletCards className="h-5 w-5 text-primary" />
            Usage
          </CardTitle>
          <CardDescription>Account-wide project and provider activity.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? <p className="text-sm text-muted-foreground">Loading usage...</p> : null}
          {error !== null ? (
            <p className="text-sm text-destructive">
              {error instanceof ApiError ? error.detail : "Could not load usage."}
            </p>
          ) : null}
          {usage !== undefined ? (
            <>
              <div className="grid grid-cols-2 gap-3">
                <Stat label="Projects" value={usage.general.projects} />
                <Stat label="Uploaded books" value={usage.general.uploaded_books} />
                <Stat label="Pages" value={usage.general.pages} />
                <Stat label="OCR pages" value={usage.general.ocr_pages} />
                <Stat label="Translated pages" value={usage.general.translated_pages} />
                <Stat label="Segments" value={usage.general.segments} />
              </div>
              <Stat label="Storage" value={formatBytes(usage.general.storage_bytes)} wide />
              <UsageMap title="Provider calls" values={usage.api.provider_calls} />
              <UsageMap title="Jobs by type" values={usage.api.jobs_by_type} />
              <UsageMap title="Jobs by state" values={usage.api.jobs_by_state} />
              <div className="rounded-2xl border bg-muted/20 px-4 py-3 text-xs text-muted-foreground">
                <p>{usage.api.note}</p>
                <p className="mt-2">
                  Tokens:{" "}
                  {usage.api.token_usage_available
                    ? `${usage.api.total_input_tokens ?? 0} input / ${
                        usage.api.total_output_tokens ?? 0
                      } output`
                    : "not tracked yet"}
                </p>
                <p>
                  Estimated cost:{" "}
                  {usage.api.estimated_cost_usd === null
                    ? "not tracked yet"
                    : `$${usage.api.estimated_cost_usd.toFixed(2)}`}
                </p>
              </div>
            </>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

function Stat({
  label,
  value,
  wide = false,
}: {
  label: string;
  value: number | string;
  wide?: boolean;
}): JSX.Element {
  return (
    <div className={wide ? "rounded-2xl border bg-[#fcfaf5] px-4 py-3" : "rounded-2xl border bg-[#fcfaf5] px-4 py-3"}>
      <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-[#1d221d]">{value}</p>
    </div>
  );
}

function UsageMap({ title, values }: { title: string; values: Record<string, number> }): JSX.Element {
  const entries = Object.entries(values);
  return (
    <div>
      <p className="mb-2 text-xs font-semibold text-[#1d221d]">{title}</p>
      {entries.length === 0 ? (
        <p className="rounded-2xl border bg-muted/20 px-4 py-3 text-xs text-muted-foreground">
          No activity recorded yet.
        </p>
      ) : (
        <div className="space-y-2">
          {entries.map(([key, value]) => (
            <div key={key} className="flex justify-between rounded-2xl border bg-muted/20 px-4 py-2 text-sm">
              <span className="capitalize text-muted-foreground">{key.replaceAll("_", " ")}</span>
              <span className="font-semibold">{value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(value >= 10 ? 1 : 2)} ${units[index]}`;
}
