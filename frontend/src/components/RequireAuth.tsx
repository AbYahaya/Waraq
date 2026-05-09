import { Navigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";

import { useAuthStore } from "@/store/auth";

export function RequireAuth({ children }: { children: ReactNode }): JSX.Element {
  const token = useAuthStore((s) => s.token);
  const location = useLocation();
  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}
