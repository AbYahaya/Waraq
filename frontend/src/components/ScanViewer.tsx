/**
 * Renders the source PDF for a Page using the browser's built-in viewer.
 *
 * The backend serves the underlying PDF (multiple physical pages) at
 * `/pages/{page_uuid}/source-pdf`; we append `#page=<page_index>` to
 * jump straight to the right page. A blob URL is used so the bearer
 * token can be attached to the request — `fetch` with `Authorization`
 * → `URL.createObjectURL`. The blob is revoked on unmount/page change.
 */

import { useEffect, useState } from "react";

import { useAuthStore } from "@/store/auth";

export interface ScanViewerProps {
  pageUuid: string;
  pageIndex: number;
}

export function ScanViewer({ pageUuid, pageIndex }: ScanViewerProps): JSX.Element {
  const token = useAuthStore((s) => s.token);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let revoke: string | null = null;
    let cancelled = false;
    setError(null);
    setBlobUrl(null);

    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    fetch(`/pages/${pageUuid}/source-pdf`, { headers })
      .then(async (resp) => {
        if (!resp.ok) {
          const text = await resp.text();
          throw new Error(`HTTP ${resp.status}: ${text}`);
        }
        return resp.blob();
      })
      .then((blob) => {
        if (cancelled) return;
        const url = URL.createObjectURL(blob);
        revoke = url;
        setBlobUrl(url);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });

    return () => {
      cancelled = true;
      if (revoke !== null) URL.revokeObjectURL(revoke);
    };
  }, [pageUuid, token]);

  if (error) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center">
        <div>
          <p className="text-destructive font-medium">Could not load scan</p>
          <p className="text-sm text-muted-foreground mt-2 break-all">{error}</p>
        </div>
      </div>
    );
  }
  if (!blobUrl) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        Loading scan…
      </div>
    );
  }

  return (
    <iframe
      title={`Scan page ${pageIndex}`}
      src={`${blobUrl}#page=${pageIndex}&view=FitH`}
      className="h-full w-full border-0"
    />
  );
}
