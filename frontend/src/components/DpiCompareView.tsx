/**
 * §2.1 Phase 3 — DPI comparison view (low DPI / high DPI side-by-side).
 *
 * Fetches the same page rendered at two DPIs from
 * `GET /pages/{u}/render-png?dpi=N` and renders them in two `<img>`
 * tags. v1.0 picks 100 DPI (low) vs 300 DPI (high) — sensible default
 * pair for spotting OCR-level fidelity differences without flooding
 * the network.
 *
 * The user can override either DPI via the small toolbar.
 */

import { useEffect, useState } from "react";

import { apiPath } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { cn } from "@/lib/utils";

const DEFAULT_LOW_DPI = 100;
const DEFAULT_HIGH_DPI = 300;
const DPI_MIN = 50;
const DPI_MAX = 600;

export interface DpiCompareViewProps {
  pageUuid: string;
  className?: string;
}

export function DpiCompareView({ pageUuid, className }: DpiCompareViewProps): JSX.Element {
  const [lowDpi, setLowDpi] = useState(DEFAULT_LOW_DPI);
  const [highDpi, setHighDpi] = useState(DEFAULT_HIGH_DPI);

  return (
    <div className={cn("flex flex-col h-full min-h-0", className)}>
      <div className="px-3 py-2 border-b flex flex-wrap items-center gap-3 bg-muted/30 text-xs">
        <DpiInput label="Low DPI" value={lowDpi} onChange={setLowDpi} />
        <DpiInput label="High DPI" value={highDpi} onChange={setHighDpi} />
        <span className="text-muted-foreground ml-auto">
          Higher DPI = larger file + slower render.
        </span>
      </div>
      <div className="flex-1 grid grid-cols-2 gap-1 p-1 min-h-0 overflow-auto bg-muted/40">
        <DpiImage pageUuid={pageUuid} dpi={lowDpi} label={`Low · ${lowDpi} DPI`} />
        <DpiImage pageUuid={pageUuid} dpi={highDpi} label={`High · ${highDpi} DPI`} />
      </div>
    </div>
  );
}

interface DpiInputProps {
  label: string;
  value: number;
  onChange: (next: number) => void;
}

function DpiInput({ label, value, onChange }: DpiInputProps): JSX.Element {
  return (
    <label className="inline-flex items-center gap-1">
      <span className="text-muted-foreground">{label}</span>
      <input
        type="number"
        min={DPI_MIN}
        max={DPI_MAX}
        value={value}
        onChange={(e) => {
          const n = Number.parseInt(e.target.value, 10);
          if (Number.isFinite(n)) {
            onChange(Math.max(DPI_MIN, Math.min(DPI_MAX, n)));
          }
        }}
        className="w-16 px-1 py-0.5 border rounded bg-background"
      />
    </label>
  );
}

interface DpiImageProps {
  pageUuid: string;
  dpi: number;
  label: string;
}

function DpiImage({ pageUuid, dpi, label }: DpiImageProps): JSX.Element {
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

    fetch(apiPath(`/pages/${pageUuid}/render-png?dpi=${dpi}`), { headers })
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
  }, [pageUuid, dpi, token]);

  return (
    <div className="bg-card flex flex-col min-h-0 border">
      <div className="px-2 py-1 text-[10px] uppercase tracking-wide text-muted-foreground border-b">
        {label}
      </div>
      <div className="flex-1 min-h-0 overflow-auto flex items-start justify-center">
        {error !== null ? (
          <p className="text-xs text-destructive p-3">{error}</p>
        ) : blobUrl === null ? (
          <p className="text-xs text-muted-foreground p-3">Rendering…</p>
        ) : (
          // eslint-disable-next-line jsx-a11y/img-redundant-alt
          <img src={blobUrl} alt={`Page rendered at ${dpi} DPI`} className="max-w-full" />
        )}
      </div>
    </div>
  );
}
