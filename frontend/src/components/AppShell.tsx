import { useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Link,
  NavLink,
  Outlet,
  useLocation,
  useNavigate,
} from "react-router-dom";
import {
  BookCopy,
  FolderOpen,
  LayoutDashboard,
  Library,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  ShieldCheck,
  Stethoscope,
  Trash2,
} from "lucide-react";

import { NotificationPanel } from "@/components/NotificationPanel";
import { ProjectWorkspaceSidebar } from "@/components/ProjectWorkspaceSidebar";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useIdleTimeout } from "@/lib/use-idle-timeout";
import { useAuthStore } from "@/store/auth";
import { readLastWorkspaceUrl } from "@/lib/workspace-memory";
import { queries } from "@/lib/queries";

export function AppShell(): JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const account = useAuthStore((s) => s.account);
  const logout = useAuthStore((s) => s.logout);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const onLogout = useCallback((): void => {
    logout();
    navigate("/login", { replace: true });
  }, [logout, navigate]);

  // §2.2 / §7.4 — 2-hour idle timeout, suspended while a background
  // job (translation / OCR) is running for this account.
  useIdleTimeout({
    enabled: account !== null,
    onIdleTimeout: onLogout,
  });

  const isWorkspaceRoute =
    location.pathname.startsWith("/projects/") ||
    location.pathname.startsWith("/diagnostics");

  const lastWorkspaceUrl = readLastWorkspaceUrl();
  const lastWorkspaceProject = getWorkspaceProject(lastWorkspaceUrl ?? "");
  const lastWorkspaceQ = useQuery({
    ...queries.project(lastWorkspaceProject?.projectUuid ?? ""),
    enabled: lastWorkspaceProject !== null,
    retry: false,
  });
  const workspaceDisabled =
    lastWorkspaceProject === null || lastWorkspaceQ.isLoading || lastWorkspaceQ.isError;
  const primaryNav = [
    {
      label: "Dashboard",
      to: "/",
      icon: LayoutDashboard,
      active: location.pathname === "/",
    },
    {
      label: "Workspace",
      to: lastWorkspaceUrl ?? "",
      icon: FolderOpen,
      active: location.pathname.startsWith("/projects/"),
      disabled: workspaceDisabled,
    },
    {
      label: "Diagnostics",
      to: "/diagnostics",
      icon: Stethoscope,
      active: location.pathname.startsWith("/diagnostics"),
    },
    {
      label: "Directories",
      to: "/directories",
      icon: Library,
      active: location.pathname.startsWith("/directories"),
    },
    {
      label: "Trash",
      to: "/trash",
      icon: Trash2,
      active: location.pathname.startsWith("/trash"),
    },
    {
      label: "Settings",
      to: "/settings",
      icon: Settings,
      active: location.pathname.startsWith("/settings"),
    },
  ];

  if (account?.is_admin) {
    primaryNav.push({
      label: "Admin",
      to: "/admin",
      icon: ShieldCheck,
      active:
        location.pathname.startsWith("/admin") &&
        !location.pathname.startsWith("/admin/admissions"),
    });
  }

  const secondaryNav = account?.is_admin
    ? [
        {
          label: "Admissions",
          to: "/admin/admissions",
          active: location.pathname.startsWith("/admin/admissions"),
        },
      ]
    : [];

  const pageMeta = getPageMeta(location.pathname);
  const workspaceProject = getWorkspaceProject(location.pathname);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex min-h-screen">
        <aside
          className={cn(
            "sticky top-0 hidden h-screen w-[280px] shrink-0 flex-col overflow-hidden bg-[#163927] text-white lg:flex",
            workspaceProject === null ? "px-5 py-6" : "px-4 py-5",
            !sidebarOpen && "lg:hidden",
          )}
        >
          {workspaceProject === null ? (
            <>
              <Link
                to="/"
                className="rounded-[1.75rem] border border-white/10 bg-white/5 px-5 py-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]"
              >
                <div className="flex items-center gap-3">
                  <BrandMark />
                  <div>
                    <div className="text-[2rem] font-semibold leading-none tracking-[0.08em]">
                      WARAQ
                    </div>
                    <p className="mt-2 max-w-[11rem] text-xs leading-5 text-white/70">
                      From Arabic scan to a print-ready book.
                    </p>
                  </div>
                </div>
              </Link>

              <nav className="mt-10 space-y-2">
                {primaryNav.map((item) => (
                  <NavItem
                    key={item.label}
                    to={item.to}
                    label={item.label}
                    icon={item.icon}
                    active={item.active}
                    disabled={item.disabled}
                  />
                ))}
              </nav>

              {secondaryNav.length > 0 && (
                <div className="mt-8">
                  <div className="px-3 text-[11px] uppercase tracking-[0.24em] text-white/45">
                    Review
                  </div>
                  <div className="mt-2 space-y-2">
                    {secondaryNav.map((item) => (
                      <NavLink
                        key={item.label}
                        to={item.to}
                        className={cn(
                          "block rounded-2xl px-4 py-3 text-sm text-white/74 transition hover:bg-white/10 hover:text-white",
                          item.active && "bg-white/12 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]",
                        )}
                      >
                        {item.label}
                      </NavLink>
                    ))}
                  </div>
                </div>
              )}

              <div className="mt-auto border-t border-white/10 pt-5">
                <div className="flex items-center gap-3 rounded-[1.5rem] bg-white/5 px-4 py-4">
                  <div className="flex h-11 w-11 items-center justify-center rounded-full bg-white/12 text-sm font-semibold">
                    {getInitials(account?.display_name ?? account?.email ?? "W")}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">
                      {account?.display_name ?? "Waraq User"}
                    </div>
                    <div className="truncate text-xs text-white/65">
                      {account?.is_admin ? "Administrator" : "Publisher"}
                    </div>
                  </div>
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={onLogout}
                    className="h-10 w-10 rounded-full text-white hover:bg-white/10 hover:text-white"
                    aria-label="Sign out"
                  >
                    <LogOut className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </>
          ) : (
            <ProjectWorkspaceSidebar
              projectUuid={workspaceProject.projectUuid}
              activePageUuid={workspaceProject.pageUuid}
              tone="dark"
            />
          )}
        </aside>

        <div className="flex min-h-screen min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-40 border-b border-border/80 bg-background/90 backdrop-blur supports-[backdrop-filter]:bg-background/75">
            <div className="flex h-20 items-center justify-between px-6 sm:px-8">
              <div className="min-w-0">
                <div className="flex items-start gap-3">
                  <Button
                    type="button"
                    size="icon"
                    variant="outline"
                    className="hidden h-10 w-10 rounded-xl lg:inline-flex"
                    onClick={() => setSidebarOpen((open) => !open)}
                    aria-label={sidebarOpen ? "Close menu" : "Open menu"}
                    title={sidebarOpen ? "Close menu" : "Open menu"}
                  >
                    {sidebarOpen ? (
                      <PanelLeftClose className="h-4 w-4" />
                    ) : (
                      <PanelLeftOpen className="h-4 w-4" />
                    )}
                  </Button>
                  <div className="min-w-0">
                    <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                      {pageMeta.eyebrow}
                    </p>
                    <div className="mt-1 flex items-center gap-3">
                      <h1 className="truncate text-2xl font-semibold text-[#1d221d]">
                        {pageMeta.title}
                      </h1>
                      <div className="hidden items-center gap-2 rounded-full border border-border/80 bg-card px-3 py-1 text-xs text-muted-foreground sm:flex">
                        <BookCopy className="h-3.5 w-3.5" />
                        {account?.display_name ?? account?.email ?? "Signed in"}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="hidden text-right md:block">
                  <div className="text-sm font-medium text-[#1d221d]">
                    {account?.display_name ?? "Waraq User"}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {account?.email}
                  </div>
                </div>
                {account && <NotificationPanel />}
              </div>
            </div>
          </header>

          <main
            className={cn(
              "min-h-0 flex-1",
              isWorkspaceRoute
                ? "overflow-y-auto p-4 sm:p-6"
                : "overflow-y-auto px-4 py-6 sm:px-8 sm:py-8",
            )}
          >
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}

interface NavItemProps {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
  active: boolean;
  disabled?: boolean;
}

function NavItem({ to, label, icon: Icon, active, disabled = false }: NavItemProps): JSX.Element {
  if (disabled) {
    return (
      <button
        type="button"
        disabled
        className="flex w-full cursor-not-allowed items-center gap-3 rounded-2xl px-4 py-3 text-sm text-white/35"
        title="Open a project workspace first."
      >
        <Icon className="h-4 w-4" />
        <span>{label}</span>
      </button>
    );
  }
  return (
    <NavLink
      to={to}
      className={cn(
        "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm text-white/74 transition hover:bg-white/10 hover:text-white",
        active && "bg-white/12 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]",
      )}
    >
      <Icon className="h-4 w-4" />
      <span>{label}</span>
    </NavLink>
  );
}

function BrandMark(): JSX.Element {
  return (
    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#c8a867] text-[#163927] shadow-sm">
      <BookCopy className="h-5 w-5" />
    </div>
  );
}

function getPageMeta(pathname: string): {
  eyebrow: string;
  title: string;
} {
  if (pathname === "/") {
    return { eyebrow: "Overview", title: "Dashboard" };
  }
  if (pathname.startsWith("/projects/")) {
    return { eyebrow: "Workspace", title: "Project Workspace" };
  }
  if (pathname.startsWith("/admin/admissions")) {
    return { eyebrow: "Review", title: "Admission Requests" };
  }
  if (pathname.startsWith("/settings")) {
    return { eyebrow: "Account", title: "Settings" };
  }
  if (pathname.startsWith("/directories")) {
    return { eyebrow: "Archives", title: "Directories" };
  }
  if (pathname.startsWith("/trash")) {
    return { eyebrow: "Recovery", title: "Trash" };
  }
  if (pathname.startsWith("/admin")) {
    return { eyebrow: "Operations", title: "Admin Panel" };
  }
  if (pathname.startsWith("/diagnostics")) {
    return { eyebrow: "Tools", title: "Diagnostics" };
  }
  return { eyebrow: "Waraq", title: "Workspace" };
}

function getWorkspaceProject(pathname: string): {
  projectUuid: string;
  pageUuid?: string;
} | null {
  const cleanPath = pathname.split(/[?#]/)[0] ?? pathname;
  const match = cleanPath.match(/^\/projects\/([^/]+)(?:\/pages\/([^/]+))?\/?$/);
  if (match === null) return null;
  return {
    projectUuid: decodeURIComponent(match[1] ?? ""),
    pageUuid: match[2] ? decodeURIComponent(match[2]) : undefined,
  };
}

function getInitials(value: string): string {
  return value
    .split(/[\s@._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}
