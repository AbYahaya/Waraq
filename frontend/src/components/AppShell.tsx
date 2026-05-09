import { Link, Outlet, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/auth";

export function AppShell(): JSX.Element {
  const navigate = useNavigate();
  const account = useAuthStore((s) => s.account);
  const logout = useAuthStore((s) => s.logout);

  const onLogout = (): void => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b bg-card">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <Link to="/" className="font-semibold tracking-tight">
            Waraq
          </Link>
          <div className="flex items-center gap-4 text-sm">
            <Link
              to="/admin"
              className="text-muted-foreground hover:text-foreground"
            >
              Admin
            </Link>
            {account && (
              <span className="text-muted-foreground">
                {account.display_name ?? account.email}
              </span>
            )}
            <Button size="sm" variant="ghost" onClick={onLogout}>
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="flex-1">
        <div className="container mx-auto px-4 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
