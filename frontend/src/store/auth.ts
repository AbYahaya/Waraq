/**
 * Auth store — token + current account, persisted to localStorage.
 *
 * Uses Zustand (chosen for M4 per the agreed stack). Persistence so a
 * page refresh doesn't bounce the user back to /login. The token is the
 * source of truth; if it expires (401 from any API call), `lib/api.ts`
 * calls `logout()` which clears state and the route guard handles the
 * redirect.
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

import type { Account } from "@/lib/types";

interface AuthState {
  token: string | null;
  account: Account | null;
  setSession: (token: string, account: Account) => void;
  setAccount: (account: Account) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      account: null,
      setSession: (token, account) => set({ token, account }),
      setAccount: (account) => set({ account }),
      logout: () => set({ token: null, account: null }),
    }),
    {
      name: "waraq-auth",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
