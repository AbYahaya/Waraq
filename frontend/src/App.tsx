import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { AdminPage } from "@/pages/Admin";
import { AccountSettingsPage } from "@/pages/AccountSettings";
import { AdmissionsPage } from "@/pages/Admissions";
import { DashboardPage } from "@/pages/Dashboard";
import { DiagnosticsPage } from "@/pages/Diagnostics";
import { DirectoriesPage } from "@/pages/Directories";
import { LoginPage } from "@/pages/Login";
import { ProjectAuditPage } from "@/pages/ProjectAudit";
import { ProjectWorkspacePage } from "@/pages/ProjectWorkspace";
import { RegisterPage } from "@/pages/Register";
import { TrashPage } from "@/pages/Trash";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});

export function App(): JSX.Element {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            element={
              <RequireAuth>
                <AppShell />
              </RequireAuth>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="/projects/:projectUuid" element={<ProjectWorkspacePage />} />
            <Route
              path="/projects/:projectUuid/pages/:pageUuid"
              element={<ProjectWorkspacePage />}
            />
            <Route
              path="/projects/:projectUuid/audit"
              element={<ProjectAuditPage />}
            />
            <Route path="/admin" element={<AdminPage />} />
            <Route path="/admin/admissions" element={<AdmissionsPage />} />
            <Route path="/diagnostics" element={<DiagnosticsPage />} />
            <Route path="/directories" element={<DirectoriesPage />} />
            <Route path="/settings" element={<AccountSettingsPage />} />
            <Route path="/trash" element={<TrashPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
