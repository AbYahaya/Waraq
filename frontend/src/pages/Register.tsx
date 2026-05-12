import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api } from "@/lib/api";
import type { Account, RegisterResponse } from "@/lib/types";
import { useAuthStore } from "@/store/auth";

export function RegisterPage(): JSX.Element {
  const navigate = useNavigate();
  const setSession = useAuthStore((s) => s.setSession);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [pendingAccount, setPendingAccount] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError(null);
    setPendingAccount(null);
    setSubmitting(true);
    try {
      const resp = await api.post<RegisterResponse>(
        "/auth/register",
        {
          email,
          password,
          display_name: displayName || null,
        },
        { auth: false },
      );
      if (resp.approval_status === "approved" && resp.access_token) {
        // Admin email auto-approved → log in immediately.
        const account = await api.get<Account>("/auth/me", {
          headers: { Authorization: `Bearer ${resp.access_token}` },
          auth: false,
        });
        setSession(resp.access_token, account);
        navigate("/", { replace: true });
      } else {
        // Non-admin: account is pending; admin must approve before login.
        setPendingAccount(email);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30 p-6">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Create your Waraq account</CardTitle>
          <CardDescription>Sign up to start a translation project.</CardDescription>
        </CardHeader>
        <CardContent>
          {pendingAccount ? (
            <div className="space-y-4">
              <div className="rounded border border-amber-200 bg-amber-50 p-4">
                <p className="font-medium text-amber-900">
                  Application received
                </p>
                <p className="text-sm text-amber-800 mt-2">
                  Your account <span className="font-mono">{pendingAccount}</span>{" "}
                  is awaiting administrator approval. You will be able to log in
                  once an admin approves your application.
                </p>
              </div>
              <Link to="/login" className="block text-center text-sm underline">
                Back to sign in
              </Link>
            </div>
          ) : (
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="display_name">Display name (optional)</Label>
              <Input
                id="display_name"
                type="text"
                autoComplete="name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Creating account…" : "Create account"}
            </Button>
            <p className="text-sm text-muted-foreground text-center">
              Have an account?{" "}
              <Link to="/login" className="underline">
                Sign in
              </Link>
            </p>
          </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
