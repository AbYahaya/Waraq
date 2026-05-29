/**
 * DPI compare and OCR recovery view.
 *
 * The recovery path is deliberately non-destructive: retrying OCR creates
 * a candidate only. The existing page OCR is replaced only if the user
 * accepts the candidate through the manual segment edit endpoint.
 */

import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { api, apiPath } from "@/lib/api";
import { qk } from "@/lib/queries";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

const DEFAULT_REFERENCE_DPI = 120;
const DEFAULT_RETRY_DPI = 300;
const DPI_MIN = 50;
const DPI_MAX = 600;

interface CropBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface OcrRetryCandidate {
  candidate_uuid: string;
  page_uuid: string;
  segment_uuid: string | null;
  scope: "region" | "full_page";
  engine: "openai" | "gemini";
  dpi: number;
  crop: CropBox | null;
  text: string;
  text_chars: number;
  current_text: string | null;
  changed: boolean;
  warning: string | null;
}

export interface DpiCompareViewProps {
  pageUuid: string;
  projectUuid?: string;
  className?: string;
}

export function DpiCompareView({
  pageUuid,
  projectUuid,
  className,
}: DpiCompareViewProps): JSX.Element {
  const queryClient = useQueryClient();
  const [referenceDpi, setReferenceDpi] = useState(DEFAULT_REFERENCE_DPI);
  const [retryDpi, setRetryDpi] = useState(DEFAULT_RETRY_DPI);
  const [zoom, setZoom] = useState(100);
  const [engine, setEngine] = useState<"openai" | "gemini">("openai");
  const [selection, setSelection] = useState<CropBox | null>(null);
  const [candidate, setCandidate] = useState<OcrRetryCandidate | null>(null);
  const [candidateDraft, setCandidateDraft] = useState("");
  const [running, setRunning] = useState<"region" | "full_page" | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [acceptedMessage, setAcceptedMessage] = useState<string | null>(null);
  const hasUsableSelection =
    selection !== null && selection.width >= 0.002 && selection.height >= 0.002;

  useEffect(() => {
    setSelection(null);
    setCandidate(null);
    setCandidateDraft("");
    setError(null);
    setAcceptedMessage(null);
  }, [pageUuid]);

  const retry = async (scope: "region" | "full_page") => {
    setError(null);
    setAcceptedMessage(null);
    if (scope === "region" && !hasUsableSelection) {
      setError("Select a region on the right-hand image first.");
      return;
    }
    setRunning(scope);
    try {
      const resp = await api.post<OcrRetryCandidate>(
        `/pages/${pageUuid}/ocr-retry-candidate`,
        {
          dpi: retryDpi,
          scope,
          crop: scope === "region" ? selection : null,
          engine,
        },
      );
      setCandidate(resp);
      setCandidateDraft(resp.text);
    } catch (err) {
      setError(err instanceof Error ? err.message : "OCR retry failed.");
    } finally {
      setRunning(null);
    }
  };

  const acceptCandidate = async () => {
    if (candidate?.segment_uuid == null) {
      setError("No active OCR segment exists for this page yet.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.put(`/segments/${candidate.segment_uuid}/text`, {
        after_text: candidateDraft,
      });
      if (projectUuid !== undefined) {
        await api.post(
          `/projects/${projectUuid}/audit/segments/${candidate.segment_uuid}/ocr-attention-decision`,
          {
            action: "supersede",
            filter_matched: "ocr_retry",
            reason: "OCR retry candidate accepted.",
            details: {
              candidate_uuid: candidate.candidate_uuid,
              page_uuid: candidate.page_uuid,
              segment_uuid: candidate.segment_uuid,
              scope: candidate.scope,
              engine: candidate.engine,
              dpi: candidate.dpi,
              crop: candidate.crop,
              changed: candidate.changed,
              text_chars: candidate.text_chars,
            },
          },
        );
      }
      await queryClient.invalidateQueries({ queryKey: qk.pageSegments(pageUuid) });
      await queryClient.invalidateQueries({ queryKey: qk.page(pageUuid) });
      if (projectUuid !== undefined) {
        await queryClient.invalidateQueries({ queryKey: qk.projectPages(projectUuid) });
        await queryClient.invalidateQueries({ queryKey: ["audit"] });
        await queryClient.invalidateQueries({ queryKey: qk.pageDifficulty(pageUuid) });
        await queryClient.invalidateQueries({ queryKey: qk.projectDifficulty(projectUuid) });
        await queryClient.invalidateQueries({ queryKey: qk.guidedReviewQueue(projectUuid) });
      }
      setAcceptedMessage("Candidate accepted and saved as the current OCR text.");
      setCandidate(null);
      setCandidateDraft("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save OCR candidate.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={cn("flex h-full min-h-0 flex-col bg-background", className)}>
      <div className="border-b bg-muted/30 px-3 py-2">
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <DpiInput label="Reference DPI" value={referenceDpi} onChange={setReferenceDpi} />
          <DpiInput label="Retry DPI" value={retryDpi} onChange={setRetryDpi} />
          <label className="inline-flex items-center gap-1">
            <span className="text-muted-foreground">Zoom</span>
            <input
              type="number"
              min={60}
              max={240}
              value={zoom}
              onChange={(e) => {
                const n = Number.parseInt(e.target.value, 10);
                if (Number.isFinite(n)) setZoom(Math.max(60, Math.min(240, n)));
              }}
              className="w-16 rounded border bg-background px-1 py-0.5"
            />
            <span className="text-muted-foreground">%</span>
          </label>
          <label className="inline-flex items-center gap-1">
            <span className="text-muted-foreground">Engine</span>
            <select
              value={engine}
              onChange={(e) => setEngine(e.target.value as "openai" | "gemini")}
              className="rounded border bg-background px-2 py-1"
            >
              <option value="openai">OpenAI</option>
              <option value="gemini">Gemini</option>
            </select>
          </label>
          <span className="ml-auto text-muted-foreground">
            Drag on the right image to select a crop. Retry creates a candidate only.
          </span>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            onClick={() => void retry("region")}
            disabled={running !== null || !hasUsableSelection}
          >
            {running === "region" ? "Retrying region..." : "Retry selected region"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => void retry("full_page")}
            disabled={running !== null}
          >
            {running === "full_page" ? "Retrying full page..." : "Retry full page"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setSelection(null)}
            disabled={selection === null || running !== null}
          >
            Clear crop
          </Button>
          {hasUsableSelection ? (
            <span className="text-xs text-muted-foreground">
              Crop: {(selection.x * 100).toFixed(1)}%, {(selection.y * 100).toFixed(1)}%,{" "}
              {(selection.width * 100).toFixed(1)}% x {(selection.height * 100).toFixed(1)}%
            </span>
          ) : null}
        </div>
        {error !== null ? <p className="mt-2 text-xs text-destructive">{error}</p> : null}
        {acceptedMessage !== null ? (
          <p className="mt-2 text-xs text-emerald-700">{acceptedMessage}</p>
        ) : null}
      </div>

      <div className="grid flex-1 grid-cols-1 gap-1 overflow-hidden bg-muted/40 p-1 lg:grid-cols-2">
        <DpiImage pageUuid={pageUuid} dpi={referenceDpi} label={`Original reference · ${referenceDpi} DPI`} />
        <SelectableDpiImage
          pageUuid={pageUuid}
          dpi={retryDpi}
          zoom={zoom}
          selection={selection}
          onSelectionChange={setSelection}
          label={`OCR retry image · ${retryDpi} DPI`}
        />
      </div>

      {candidate !== null ? (
        <CandidateReview
          candidate={candidate}
          draft={candidateDraft}
          saving={saving}
          onDraftChange={setCandidateDraft}
          onAccept={() => void acceptCandidate()}
          onDiscard={() => {
            setCandidate(null);
            setCandidateDraft("");
          }}
        />
      ) : null}
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
        className="w-16 rounded border bg-background px-1 py-0.5"
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
  const { blobUrl, error } = useRenderedPage(pageUuid, dpi);

  return (
    <div className="flex min-h-0 flex-col border bg-card">
      <div className="border-b px-2 py-1 text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="flex min-h-0 flex-1 items-start justify-center overflow-auto">
        {error !== null ? (
          <p className="p-3 text-xs text-destructive">{error}</p>
        ) : blobUrl === null ? (
          <p className="p-3 text-xs text-muted-foreground">Rendering...</p>
        ) : (
          // eslint-disable-next-line jsx-a11y/img-redundant-alt
          <img src={blobUrl} alt={`Page rendered at ${dpi} DPI`} className="max-w-full" />
        )}
      </div>
    </div>
  );
}

interface SelectableDpiImageProps {
  pageUuid: string;
  dpi: number;
  zoom: number;
  selection: CropBox | null;
  onSelectionChange: (selection: CropBox | null) => void;
  label: string;
}

function SelectableDpiImage({
  pageUuid,
  dpi,
  zoom,
  selection,
  onSelectionChange,
  label,
}: SelectableDpiImageProps): JSX.Element {
  const { blobUrl, error } = useRenderedPage(pageUuid, dpi);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);

  useEffect(() => {
    setDragStart(null);
  }, [pageUuid, dpi]);

  const toPoint = (event: MouseEvent<HTMLImageElement>): { x: number; y: number } => {
    const rect = event.currentTarget.getBoundingClientRect();
    return {
      x: clamp01((event.clientX - rect.left) / rect.width),
      y: clamp01((event.clientY - rect.top) / rect.height),
    };
  };

  const updateSelection = (start: { x: number; y: number }, end: { x: number; y: number }) => {
    const x = Math.min(start.x, end.x);
    const y = Math.min(start.y, end.y);
    const width = Math.abs(end.x - start.x);
    const height = Math.abs(end.y - start.y);
    if (width < 0.002 || height < 0.002) return;
    onSelectionChange({ x, y, width, height });
  };

  return (
    <div className="flex min-h-0 flex-col border bg-card">
      <div className="border-b px-2 py-1 text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="flex min-h-0 flex-1 items-start justify-center overflow-auto">
        {error !== null ? (
          <p className="p-3 text-xs text-destructive">{error}</p>
        ) : blobUrl === null ? (
          <p className="p-3 text-xs text-muted-foreground">Rendering...</p>
        ) : (
          <div className="relative inline-block select-none" style={{ width: `${zoom}%` }}>
            {/* eslint-disable-next-line jsx-a11y/img-redundant-alt */}
            <img
              src={blobUrl}
              alt={`Selectable page rendered at ${dpi} DPI`}
              className="block w-full cursor-crosshair"
              draggable={false}
              onMouseDown={(event) => {
                const point = toPoint(event);
                setDragStart(point);
                onSelectionChange({ ...point, width: 0, height: 0 });
              }}
              onMouseMove={(event) => {
                if (dragStart === null) return;
                updateSelection(dragStart, toPoint(event));
              }}
              onMouseUp={(event) => {
                if (dragStart === null) return;
                updateSelection(dragStart, toPoint(event));
                setDragStart(null);
              }}
              onMouseLeave={(event) => {
                if (dragStart === null) return;
                updateSelection(dragStart, toPoint(event));
                setDragStart(null);
              }}
            />
            {selection !== null && selection.width > 0 && selection.height > 0 ? (
              <div
                className="pointer-events-none absolute border-2 border-emerald-500 bg-emerald-400/20 shadow-[0_0_0_9999px_rgba(15,23,42,0.22)]"
                style={{
                  left: `${selection.x * 100}%`,
                  top: `${selection.y * 100}%`,
                  width: `${selection.width * 100}%`,
                  height: `${selection.height * 100}%`,
                }}
              />
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}

function useRenderedPage(pageUuid: string, dpi: number): {
  blobUrl: string | null;
  error: string | null;
} {
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

  return { blobUrl, error };
}

interface CandidateReviewProps {
  candidate: OcrRetryCandidate;
  draft: string;
  saving: boolean;
  onDraftChange: (next: string) => void;
  onAccept: () => void;
  onDiscard: () => void;
}

function CandidateReview({
  candidate,
  draft,
  saving,
  onDraftChange,
  onAccept,
  onDiscard,
}: CandidateReviewProps): JSX.Element {
  const diffLines = useMemo(
    () => makeCandidateLineStates(candidate.current_text ?? "", draft),
    [candidate.current_text, draft],
  );

  return (
    <div className="max-h-[44%] overflow-auto border-t bg-card">
      <div className="flex flex-wrap items-center gap-2 border-b px-3 py-2">
        <div>
          <p className="text-sm font-semibold">OCR retry candidate</p>
          <p className="text-xs text-muted-foreground">
            {candidate.scope === "region" ? "Selected region" : "Full page"} · {candidate.engine} ·{" "}
            {candidate.dpi} DPI · {candidate.text_chars} characters
          </p>
        </div>
        <span
          className={cn(
            "rounded-full px-2 py-1 text-[10px] uppercase tracking-wide",
            candidate.changed
              ? "bg-amber-100 text-amber-900"
              : "bg-emerald-100 text-emerald-900",
          )}
        >
          {candidate.changed ? "Different from current OCR" : "Same as current OCR"}
        </span>
        <Button
          size="sm"
          className="ml-auto"
          onClick={onAccept}
          disabled={saving || candidate.segment_uuid === null}
        >
          {saving ? "Saving..." : "Accept candidate"}
        </Button>
        <Button size="sm" variant="outline" onClick={onDiscard} disabled={saving}>
          Discard
        </Button>
      </div>
      {candidate.warning !== null ? (
        <p className="border-b px-3 py-2 text-xs text-amber-800">{candidate.warning}</p>
      ) : null}
      <div className="grid gap-1 p-1 lg:grid-cols-3">
        <TextPanel label="Current OCR" text={candidate.current_text ?? "(No current OCR text)"} />
        <div className="flex min-h-[16rem] flex-col border bg-background">
          <div className="border-b px-2 py-1 text-[10px] uppercase tracking-wide text-muted-foreground">
            Candidate OCR (editable before accept)
          </div>
          <textarea
            dir="rtl"
            lang="ar"
            value={draft}
            onChange={(event) => onDraftChange(event.target.value)}
            className="min-h-[16rem] flex-1 resize-y whitespace-pre-wrap border-0 bg-background p-3 text-right font-arabic text-base leading-loose outline-none"
          />
        </div>
        <div className="flex min-h-[16rem] flex-col border bg-background">
          <div className="border-b px-2 py-1 text-[10px] uppercase tracking-wide text-muted-foreground">
            Candidate line differences
          </div>
          <div className="space-y-1 overflow-auto p-3 text-right font-arabic text-sm leading-loose" dir="rtl">
            {diffLines.length === 0 ? (
              <p className="text-xs text-muted-foreground" dir="ltr">
                No text to compare.
              </p>
            ) : (
              diffLines.map((line, index) => (
                <p
                  // eslint-disable-next-line react/no-array-index-key
                  key={`${line.state}-${index}`}
                  className={cn(
                    "whitespace-pre-wrap rounded px-2 py-1",
                    line.state === "new"
                      ? "bg-emerald-100 text-emerald-950"
                      : line.state === "changed"
                        ? "bg-amber-100 text-amber-950"
                        : "bg-muted/40 text-muted-foreground",
                  )}
                >
                  {line.text || " "}
                </p>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function TextPanel({ label, text }: { label: string; text: string }): JSX.Element {
  return (
    <div className="flex min-h-[16rem] flex-col border bg-background">
      <div className="border-b px-2 py-1 text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <pre
        dir="rtl"
        lang="ar"
        className="min-h-[16rem] flex-1 overflow-auto whitespace-pre-wrap p-3 text-right font-arabic text-base leading-loose"
      >
        {text}
      </pre>
    </div>
  );
}

function makeCandidateLineStates(
  currentText: string,
  candidateText: string,
): Array<{ text: string; state: "same" | "changed" | "new" }> {
  const currentLines = currentText.split(/\r?\n/);
  const candidateLines = candidateText.split(/\r?\n/);
  if (candidateLines.length === 1 && candidateLines[0] === "") return [];
  return candidateLines.map((line, index) => {
    if (currentLines[index] === line) return { text: line, state: "same" };
    if (currentLines.includes(line)) return { text: line, state: "changed" };
    return { text: line, state: "new" };
  });
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}
