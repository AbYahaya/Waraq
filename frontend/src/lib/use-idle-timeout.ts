/**
 * §2.2 / §7.4 — Background-aware idle timeout (2 hours; suspended
 * while a background process is active).
 *
 * Per Dokument 1 §2.2 + §7.4 verbatim:
 *
 *   "No timeout during an active background process, otherwise 2 hours."
 *
 * The hook attaches activity listeners (mouse / keyboard / touch /
 * focus) that reset the idle clock. Every 60s it polls
 * `/me/active-background-jobs` — when the count is > 0 the timeout
 * is suspended (canon "no timeout during active background"). When
 * the clock crosses the 2-hour mark with no recorded activity AND
 * no active background jobs, the supplied `onIdleTimeout` callback
 * fires (typically: log out).
 */

import { useEffect, useRef } from "react";

import { api } from "@/lib/api";

const TWO_HOURS_MS = 2 * 60 * 60 * 1000;
const POLL_INTERVAL_MS = 60 * 1000;
const ACTIVITY_EVENTS = [
  "mousemove",
  "mousedown",
  "keydown",
  "touchstart",
  "scroll",
  "focus",
] as const;

interface ActiveJobsResponse {
  running_or_pending: number;
}

export interface UseIdleTimeoutOptions {
  /** Called when the user crosses the canonical 2-hour idle threshold
   * with no active background jobs. Typically a logout function. */
  onIdleTimeout: () => void;
  /** When false, the hook is inert (no listeners, no polling). Used
   * for the unauthenticated routes. */
  enabled: boolean;
  /** Override the canonical 2-hour threshold for testing. */
  idleThresholdMs?: number;
  /** Override the active-jobs poll interval for testing. */
  pollIntervalMs?: number;
}

export function useIdleTimeout({
  onIdleTimeout,
  enabled,
  idleThresholdMs = TWO_HOURS_MS,
  pollIntervalMs = POLL_INTERVAL_MS,
}: UseIdleTimeoutOptions): void {
  // Refs so the listeners + timer callbacks stay stable identity.
  const lastActivityRef = useRef<number>(Date.now());
  const activeJobsRef = useRef<number>(0);

  useEffect(() => {
    if (!enabled) return;

    const recordActivity = (): void => {
      lastActivityRef.current = Date.now();
    };
    for (const ev of ACTIVITY_EVENTS) {
      window.addEventListener(ev, recordActivity, { passive: true });
    }

    const checkAndPoll = async (): Promise<void> => {
      // Poll the canonical active-jobs endpoint.
      try {
        const resp = await api.get<ActiveJobsResponse>("/me/active-background-jobs");
        activeJobsRef.current = resp.running_or_pending;
      } catch {
        // Network error — treat as 0 (don't suppress timeout if we
        // can't tell). The user can still avoid logout by being active.
        activeJobsRef.current = 0;
      }
      const idleMs = Date.now() - lastActivityRef.current;
      if (idleMs >= idleThresholdMs && activeJobsRef.current === 0) {
        onIdleTimeout();
      }
    };

    // Initial poll then interval.
    void checkAndPoll();
    const intervalId = window.setInterval(() => {
      void checkAndPoll();
    }, pollIntervalMs);

    return () => {
      for (const ev of ACTIVITY_EVENTS) {
        window.removeEventListener(ev, recordActivity);
      }
      window.clearInterval(intervalId);
    };
  }, [enabled, onIdleTimeout, idleThresholdMs, pollIntervalMs]);
}
