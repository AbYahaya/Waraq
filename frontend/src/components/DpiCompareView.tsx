/**
 * DPI compare and OCR recovery view.
 *
 * The recovery path is deliberately non-destructive: retrying OCR creates
 * a candidate only. The existing page OCR is replaced only if the user
 * accepts the candidate through the manual segment edit endpoint.
 */

import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

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
  issue_uuid: string | null;
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

function parseBoundedNumber(
  value: string | null,
  fallback: number,
  min: number,
  max: number,
): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(max, Math.max(min, Math.round(parsed)));
}

function parseOcrEngine(value: string | null): "openai" | "gemini" {
  return value === "gemini" ? "gemini" : "openai";
}

function setNumericSearchParam(
  params: URLSearchParams,
  key: string,
  value: number,
  fallback: number,
): void {
  if (value === fallback) {
    params.delete(key);
    return;
  }
  params.set(key, String(value));
}

export interface DpiCompareViewProps {
  pageUuid: string;
  projectUuid?: string;
  sourceIssueLabel?: string | null;
  sourceIssueRef?: string | null;
  sourceIssueUuid?: string | null;
  attentionReturnUrl?: string | null;
  className?: string;
}

export function DpiCompareView({
  pageUuid,
  projectUuid,
  sourceIssueLabel,
  sourceIssueRef,
  sourceIssueUuid,
  attentionReturnUrl,
  className,
}: DpiCompareViewProps): JSX.Element {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [referenceDpi, setReferenceDpi] = useState(() =>
    parseBoundedNumber(searchParams.get("ref_dpi"), DEFAULT_REFERENCE_DPI, DPI_MIN, DPI_MAX),
  );
  const [retryDpi, setRetryDpi] = useState(() =>
    parseBoundedNumber(searchParams.get("retry_dpi"), DEFAULT_RETRY_DPI, DPI_MIN, DPI_MAX),
  );
  const [zoom, setZoom] = useState(() =>
    parseBoundedNumber(searchParams.get("dpi_zoom"), 100, 50, 240),
  );
  const [engine, setEngine] = useState<"openai" | "gemini">(() =>
    parseOcrEngine(searchParams.get("dpi_engine")),
  );
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

  useEffect(() => {
    setReferenceDpi(parseBoundedNumber(searchParams.get("ref_dpi"), DEFAULT_REFERENCE_DPI, DPI_MIN, DPI_MAX));
    setRetryDpi(parseBoundedNumber(searchParams.get("retry_dpi"), DEFAULT_RETRY_DPI, DPI_MIN, DPI_MAX));
    setZoom(parseBoundedNumber(searchParams.get("dpi_zoom"), 100, 50, 240));
    setEngine(parseOcrEngine(searchParams.get("dpi_engine")));
  }, [searchParams]);

  useEffect(() => {
    const next = new URLSearchParams(searchParams);
    setNumericSearchParam(next, "ref_dpi", referenceDpi, DEFAULT_REFERENCE_DPI);
    setNumericSearchParam(next, "retry_dpi", retryDpi, DEFAULT_RETRY_DPI);
    setNumericSearchParam(next, "dpi_zoom", zoom, 100);
    if (engine === "openai") {
      next.delete("dpi_engine");
    } else {
      next.set("dpi_engine", engine);
    }
    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true });
    }
  }, [engine, referenceDpi, retryDpi, searchParams, setSearchParams, zoom]);

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
          issue_uuid: sourceIssueUuid ?? null,
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
              issue_uuid: candidate.issue_uuid,
              page_uuid: candidate.page_uuid,
              segment_uuid: candidate.segment_uuid,
              scope: candidate.scope,
              engine: candidate.engine,
              dpi: candidate.dpi,
              crop: candidate.crop,
              changed: candidate.changed,
              text_chars: candidate.text_chars,
            },
            issue_uuid: candidate.issue_uuid,
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
          sourceIssueLabel={sourceIssueLabel}
          sourceIssueRef={sourceIssueRef}
          sourceIssueUuid={sourceIssueUuid}
          attentionReturnUrl={attentionReturnUrl}
          onDraftChange={setCandidateDraft}
          onAccept={() => void acceptCandidate()}
          onKeepCurrent={() => {
            setAcceptedMessage("Current OCR kept. Retry candidate was not applied.");
            setCandidate(null);
            setCandidateDraft("");
          }}
          onDiscard={() => {
            setAcceptedMessage(null);
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
  sourceIssueLabel?: string | null;
  sourceIssueRef?: string | null;
  sourceIssueUuid?: string | null;
  attentionReturnUrl?: string | null;
  onDraftChange: (next: string) => void;
  onAccept: () => void;
  onKeepCurrent: () => void;
  onDiscard: () => void;
}

function CandidateReview({
  candidate,
  draft,
  saving,
  sourceIssueLabel,
  sourceIssueRef,
  sourceIssueUuid,
  attentionReturnUrl,
  onDraftChange,
  onAccept,
  onKeepCurrent,
  onDiscard,
}: CandidateReviewProps): JSX.Element {
  const [editing, setEditing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const diffLines = useMemo(
    () => makeCandidateLineStates(candidate.current_text ?? "", draft),
    [candidate.current_text, draft],
  );
  const acceptLabel =
    candidate.scope === "region" ? "Accept new region OCR" : "Accept new full-page OCR";
  const mappingTarget =
    candidate.segment_uuid !== null
      ? `Page ${shortUuid(candidate.page_uuid)} / segment ${shortUuid(candidate.segment_uuid)}`
      : `Page ${shortUuid(candidate.page_uuid)} / no active segment`;

  return (
    <div className="max-h-[58%] overflow-auto border-t bg-card">
      <div className="flex flex-wrap items-center gap-2 border-b px-3 py-2">
        <div>
          <p className="text-sm font-semibold">OCR retry result review</p>
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
        <span className="rounded-full bg-muted px-2 py-1 text-[10px] uppercase tracking-wide text-muted-foreground">
          {candidate.segment_uuid === null ? "No segment mapping" : "Mapped to segment"}
        </span>
        <Button
          size="sm"
          className="ml-auto"
          onClick={onAccept}
          disabled={saving || candidate.segment_uuid === null}
        >
          {saving ? "Saving..." : acceptLabel}
        </Button>
        <Button size="sm" variant="outline" onClick={onKeepCurrent} disabled={saving}>
          Keep current OCR
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            setEditing(true);
            window.setTimeout(() => textareaRef.current?.focus(), 0);
          }}
          disabled={saving}
        >
          Edit manually
        </Button>
        <Button size="sm" variant="outline" onClick={onDiscard} disabled={saving}>
          Discard
        </Button>
      </div>
      {candidate.warning !== null ? (
        <p className="border-b px-3 py-2 text-xs text-amber-800">{candidate.warning}</p>
      ) : null}
      <div className="grid gap-1 border-b p-1 lg:grid-cols-[minmax(14rem,0.8fr)_minmax(0,1.2fr)]">
        <RetryRegionPreview candidate={candidate} />
        <div className="grid gap-1 md:grid-cols-2">
          <ReviewFact label="Mapping target" value={mappingTarget} />
          <ReviewFact
            label="Linked issue"
            value={sourceIssueLabel ?? "OCR retry from workspace"}
            detail={sourceIssueUuid ?? sourceIssueRef ?? "No source OCR issue selected"}
          />
          <ReviewFact
            label="Acceptance effect"
            value={
              candidate.segment_uuid === null
                ? "Cannot apply until a segment exists"
                : "Updates mapped segment OCR and records a superseded retry decision"
            }
          />
          <ReviewFact
            label="Confidence / reason"
            value={candidate.changed ? "Candidate differs from current OCR" : "Candidate matches current OCR"}
            detail="Retry engines do not currently return calibrated confidence for this review panel."
          />
          {attentionReturnUrl ? (
            <a
              href={attentionReturnUrl}
              className="rounded border bg-background p-2 text-xs underline text-muted-foreground hover:text-foreground md:col-span-2"
            >
              Back to source attention item
            </a>
          ) : null}
        </div>
      </div>
      <div className="grid gap-1 p-1 lg:grid-cols-3">
        <TextPanel label="Current OCR" text={candidate.current_text ?? "(No current OCR text)"} />
        <div className="flex min-h-[16rem] flex-col border bg-background">
          <div className="border-b px-2 py-1 text-[10px] uppercase tracking-wide text-muted-foreground">
            Candidate OCR {editing ? "(editing)" : "(use Edit manually to change)"}
          </div>
          <textarea
            ref={textareaRef}
            dir="rtl"
            lang="ar"
            value={draft}
            onChange={(event) => onDraftChange(event.target.value)}
            readOnly={!editing}
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

function RetryRegionPreview({ candidate }: { candidate: OcrRetryCandidate }): JSX.Element {
  const { blobUrl, error } = useRenderedPage(candidate.page_uuid, candidate.dpi);
  return (
    <div className="flex min-h-[12rem] flex-col border bg-background">
      <div className="border-b px-2 py-1 text-[10px] uppercase tracking-wide text-muted-foreground">
        Original {candidate.scope === "region" ? "crop" : "page"} region
      </div>
      <div className="flex min-h-0 flex-1 items-start justify-center overflow-auto p-2">
        {error !== null ? (
          <p className="text-xs text-destructive">{error}</p>
        ) : blobUrl === null ? (
          <p className="text-xs text-muted-foreground">Rendering...</p>
        ) : (
          <div className="relative inline-block max-h-56">
            <img
              src={blobUrl}
              alt="OCR retry source region"
              className="max-h-56 max-w-full rounded border"
            />
            {candidate.crop !== null ? (
              <div
                className="pointer-events-none absolute border-2 border-emerald-500 bg-emerald-400/20 shadow-[0_0_0_9999px_rgba(15,23,42,0.18)]"
                style={{
                  left: `${candidate.crop.x * 100}%`,
                  top: `${candidate.crop.y * 100}%`,
                  width: `${candidate.crop.width * 100}%`,
                  height: `${candidate.crop.height * 100}%`,
                }}
              />
            ) : null}
          </div>
        )}
      </div>
      <div className="border-t px-2 py-1 text-[10px] text-muted-foreground">
        {candidate.crop ? formatCrop(candidate.crop) : "Full page retry"}
      </div>
    </div>
  );
}

function ReviewFact({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail?: string;
}): JSX.Element {
  return (
    <div className="rounded border bg-background p-2 text-xs">
      <div className="uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 font-medium">{value}</div>
      {detail ? <div className="mt-1 text-muted-foreground">{detail}</div> : null}
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

function formatCrop(crop: CropBox): string {
  return `Crop ${percent(crop.x)}, ${percent(crop.y)}, ${percent(crop.width)} x ${percent(crop.height)}`;
}

function percent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function shortUuid(value: string): string {
  return value.slice(0, 8);
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
