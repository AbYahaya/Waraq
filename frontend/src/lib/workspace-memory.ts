const LAST_WORKSPACE_URL_KEY = "waraq:last-workspace-url";

export function rememberWorkspaceUrl(url: string): void {
  if (!url.startsWith("/projects/")) return;
  window.localStorage.setItem(LAST_WORKSPACE_URL_KEY, url);
}

export function readLastWorkspaceUrl(): string | null {
  const url = window.localStorage.getItem(LAST_WORKSPACE_URL_KEY);
  return url && url.startsWith("/projects/") ? url : null;
}

export function clearLastWorkspaceUrl(projectUuid?: string): void {
  const current = readLastWorkspaceUrl();
  if (!projectUuid || current?.startsWith(`/projects/${projectUuid}`)) {
    window.localStorage.removeItem(LAST_WORKSPACE_URL_KEY);
  }
}
