/**
 * Sub-batch N (out-of-phase, 2026-05-12) — Project audit dashboard.
 *
 * Read-only aggregation view over OCR confidence / engine agreement /
 * cross-check situations / open audit findings / open conflicts.
 * Renders:
 *   1. Summary card (counts + distribution chips)
 *   2. Filter chips (low confidence / divergent OCR / substantive deviation /
 *      ambiguity / check failed / open finding / open conflict)
 *   3. Attention list (filtered, with per-row deep-link to the existing
 *      review surface for that segment)
 *
 * Per §2.6 "no new domain concepts": this surface NEVER writes — it
 * links to the canonical per-segment review pages for decisions.
 */
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, api, apiPath } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/auth";

interface OcrStatusDistribution {
  ausstehend: number;
  in_review: number;
  go: number;
  go_with_warning: number;
  no_go: number;
}

interface ConfidenceDistribution {
  accepted: number;
  deficient: number;
  critical: number;
  unknown_or_unscored: number;
  no_ocr: number;
}

interface EngineAgreementDistribution {
  exact_match: number;
  skeleton_equal: number;
  divergent: number;
  single_engine: number;
  engine_error: number;
  none_recorded: number;
}

interface CrossCheckDistribution {
  agreement: number;
  auto_correction: number;
  substantive_deviation: number;
  ambiguity: number;
  check_failed: number;
  not_translated: number;
}

interface BefundDistribution {
  kritisch: number;
  hoch: number;
  mittel: number;
}

interface ProjectAuditSummary {
  project_uuid: string;
  total_pages: number;
  total_segments: number;
  page_ocr_status: OcrStatusDistribution;
  ocr_confidence: ConfidenceDistribution;
  engine_agreement: EngineAgreementDistribution;
  cross_check: CrossCheckDistribution;
  open_befunde: BefundDistribution;
  open_konsistenz_befunde: number;
  open_conflicts: number;
}

interface AttentionItem {
  project_uuid: string;
  page_uuid: string;
  page_index: number;
  block_uuid: string;
  block_index: number;
  satz_uuid: string;
  satz_index: number;
  filter_matched: string;
  detail: Record<string, unknown>;
}

interface AttentionListResponse {
  items: AttentionItem[];
}

interface EngineReading {
  engine: string;
  text: string | null;
  text_chars: number;
  confidence: number | null;
  error_class: string | null;
  is_current: boolean;
}

interface BefundDetailResponse {
  befund_uuid: string;
  regelkennung: string;
  schweregrad: string;
  verstossklasse: string;
  detection_context: Record<string, unknown>;
}

interface SegmentAuditDetail {
  satz_uuid: string;
  page_index: number;
  block_index: number;
  satz_index: number;
  current_text: string | null;
  ocr_engine_agreement: string | null;
  ocr_confidence_score: number | null;
  ocr_confidence_class: string | null;
  ocr_engines: EngineReading[];
  ocr_engines_have_text: boolean;
  translation_situation: string | null;
  translation_target_text: string | null;
  translation_primary_engine: string | null;
  translation_check_engine: string | null;
  translation_primary_output: string | null;
  translation_check_output: string | null;
  translation_check_error: string | null;
  open_befunde: BefundDetailResponse[];
  open_conflicts_count: number;
}

const FILTER_OPTIONS: { value: string; label: string; tone: string }[] = [
  { value: "low_confidence", label: "Low OCR confidence", tone: "amber" },
  { value: "divergent_ocr", label: "Divergent engines", tone: "amber" },
  { value: "cross_check_substantive", label: "Substantive deviation", tone: "red" },
  { value: "cross_check_ambiguity", label: "Translation ambiguity", tone: "amber" },
  { value: "cross_check_failed", label: "Cross-check failed", tone: "red" },
  { value: "open_audit_finding", label: "Open audit finding", tone: "red" },
  { value: "open_conflict", label: "Open conflict", tone: "red" },
];

const FILTER_LABEL: Record<string, string> = Object.fromEntries(
  FILTER_OPTIONS.map((o) => [o.value, o.label]),
);

export function ProjectAuditPage(): JSX.Element {
  const { projectUuid } = useParams<{ projectUuid: string }>();
  const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set());

  const summary = useQuery<ProjectAuditSummary>({
    queryKey: ["audit", "summary", projectUuid],
    queryFn: () =>
      api.get<ProjectAuditSummary>(`/projects/${projectUuid}/audit/summary`),
    enabled: !!projectUuid,
  });

  const attentionUrl = useMemo(() => {
    const params = new URLSearchParams();
    for (const f of activeFilters) {
      params.append("filter", f);
    }
    const qs = params.toString();
    return `/projects/${projectUuid}/audit/attention${qs ? `?${qs}` : ""}`;
  }, [projectUuid, activeFilters]);

  const attention = useQuery<AttentionListResponse>({
    queryKey: ["audit", "attention", projectUuid, [...activeFilters].sort().join(",")],
    queryFn: () => api.get<AttentionListResponse>(attentionUrl),
    enabled: !!projectUuid,
  });

  const toggleFilter = (value: string): void => {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  };

  if (!projectUuid) {
    return (
      <div className="text-sm text-muted-foreground">
        Open a project to see its audit dashboard.
      </div>
    );
  }

  return (
    <div className="max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Project audit</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Read-only view over OCR confidence, engine consensus, translation
          cross-check, and open audit findings. Click a row to open the
          segment's review surface.
        </p>
      </div>

      {summary.isLoading && (
        <div className="text-sm text-muted-foreground">Loading summary…</div>
      )}
      {summary.error && (
        <ErrorBox error={summary.error} />
      )}
      {summary.data && <SummaryCard summary={summary.data} />}

      <FilterChips active={activeFilters} onToggle={toggleFilter} />

      {attention.isLoading && (
        <div className="text-sm text-muted-foreground">Loading attention list…</div>
      )}
      {attention.error && <ErrorBox error={attention.error} />}
      {attention.data && (
        <AttentionList
          items={attention.data.items}
          projectUuid={projectUuid}
          activeFilters={activeFilters}
        />
      )}
    </div>
  );
}

function ErrorBox({ error }: { error: unknown }): JSX.Element {
  return (
    <div className="rounded border border-red-200 bg-red-50 text-red-900 text-sm p-3">
      {error instanceof ApiError ? error.detail : String(error)}
    </div>
  );
}

function SummaryCard({ summary }: { summary: ProjectAuditSummary }): JSX.Element {
  return (
    <section className="border rounded-lg p-4 bg-card">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Pages" value={summary.total_pages} />
        <Stat label="Segments" value={summary.total_segments} />
        <Stat
          label="Open findings"
          value={
            summary.open_befunde.kritisch +
            summary.open_befunde.hoch +
            summary.open_befunde.mittel
          }
        />
        <Stat label="Open conflicts" value={summary.open_conflicts} />
      </div>

      <div className="mt-4 space-y-3 text-sm">
        <DistributionRow
          label="Page OCR status"
          buckets={[
            { label: "go", value: summary.page_ocr_status.go, tone: "green" },
            {
              label: "go w/ warning",
              value: summary.page_ocr_status.go_with_warning,
              tone: "amber",
            },
            {
              label: "in review",
              value: summary.page_ocr_status.in_review,
              tone: "amber",
            },
            { label: "no go", value: summary.page_ocr_status.no_go, tone: "red" },
            {
              label: "ausstehend",
              value: summary.page_ocr_status.ausstehend,
              tone: "neutral",
            },
          ]}
        />
        <DistributionRow
          label="OCR confidence"
          buckets={[
            {
              label: "accepted",
              value: summary.ocr_confidence.accepted,
              tone: "green",
            },
            {
              label: "deficient",
              value: summary.ocr_confidence.deficient,
              tone: "amber",
            },
            {
              label: "critical",
              value: summary.ocr_confidence.critical,
              tone: "red",
            },
            {
              label: "no signal",
              value: summary.ocr_confidence.unknown_or_unscored,
              tone: "neutral",
            },
            {
              label: "no OCR yet",
              value: summary.ocr_confidence.no_ocr,
              tone: "neutral",
            },
          ]}
        />
        <DistributionRow
          label="Engine agreement"
          buckets={[
            {
              label: "exact",
              value: summary.engine_agreement.exact_match,
              tone: "green",
            },
            {
              label: "skeleton",
              value: summary.engine_agreement.skeleton_equal,
              tone: "green",
            },
            {
              label: "single",
              value: summary.engine_agreement.single_engine,
              tone: "neutral",
            },
            {
              label: "divergent",
              value: summary.engine_agreement.divergent,
              tone: "amber",
            },
            {
              label: "engine error",
              value: summary.engine_agreement.engine_error,
              tone: "red",
            },
            {
              label: "none",
              value: summary.engine_agreement.none_recorded,
              tone: "neutral",
            },
          ]}
        />
        <DistributionRow
          label="Translation cross-check"
          buckets={[
            {
              label: "agreement",
              value: summary.cross_check.agreement,
              tone: "green",
            },
            {
              label: "auto-correction",
              value: summary.cross_check.auto_correction,
              tone: "green",
            },
            {
              label: "substantive",
              value: summary.cross_check.substantive_deviation,
              tone: "red",
            },
            {
              label: "ambiguity",
              value: summary.cross_check.ambiguity,
              tone: "amber",
            },
            {
              label: "failed",
              value: summary.cross_check.check_failed,
              tone: "red",
            },
            {
              label: "not translated",
              value: summary.cross_check.not_translated,
              tone: "neutral",
            },
          ]}
        />
        <DistributionRow
          label="Open audit findings"
          buckets={[
            {
              label: "kritisch",
              value: summary.open_befunde.kritisch,
              tone: "red",
            },
            { label: "hoch", value: summary.open_befunde.hoch, tone: "red" },
            { label: "mittel", value: summary.open_befunde.mittel, tone: "amber" },
            {
              label: "consistency",
              value: summary.open_konsistenz_befunde,
              tone: "amber",
            },
          ]}
        />
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: number }): JSX.Element {
  return (
    <div>
      <div className="text-2xl font-semibold">{value}</div>
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
    </div>
  );
}

function DistributionRow({
  label,
  buckets,
}: {
  label: string;
  buckets: { label: string; value: number; tone: string }[];
}): JSX.Element {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
        {label}
      </div>
      <div className="flex flex-wrap gap-1">
        {buckets.map((b) => (
          <span
            key={b.label}
            className={`inline-flex items-baseline gap-1 rounded px-2 py-0.5 text-xs ${toneClass(b.tone, b.value === 0)}`}
          >
            <span className="font-medium">{b.value}</span>
            <span>{b.label}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function toneClass(tone: string, isZero: boolean): string {
  if (isZero) return "bg-muted text-muted-foreground";
  switch (tone) {
    case "green":
      return "bg-emerald-100 text-emerald-900";
    case "amber":
      return "bg-amber-100 text-amber-900";
    case "red":
      return "bg-red-100 text-red-900";
    default:
      return "bg-muted text-foreground";
  }
}

function FilterChips({
  active,
  onToggle,
}: {
  active: Set<string>;
  onToggle: (value: string) => void;
}): JSX.Element {
  return (
    <section>
      <div className="text-xs uppercase tracking-wide text-muted-foreground mb-2">
        Filter attention list
      </div>
      <div className="flex flex-wrap gap-2">
        {FILTER_OPTIONS.map((opt) => {
          const isActive = active.has(opt.value);
          return (
            <Button
              key={opt.value}
              size="sm"
              variant={isActive ? "default" : "outline"}
              onClick={() => onToggle(opt.value)}
            >
              {opt.label}
            </Button>
          );
        })}
      </div>
    </section>
  );
}

function AttentionList({
  items,
  projectUuid,
  activeFilters,
}: {
  items: AttentionItem[];
  projectUuid: string;
  activeFilters: Set<string>;
}): JSX.Element {
  if (items.length === 0) {
    return (
      <section className="border rounded-lg p-4 bg-card text-sm text-muted-foreground italic">
        {activeFilters.size === 0
          ? "No segments are flagged across all attention categories."
          : "No segments match the selected filters."}
      </section>
    );
  }

  return (
    <section className="border rounded-lg bg-card divide-y">
      <div className="px-4 py-2 text-xs uppercase tracking-wide text-muted-foreground">
        Attention list ({items.length})
      </div>
      {items.map((it, idx) => (
        <AttentionRow
          key={`${it.satz_uuid}-${it.filter_matched}-${idx}`}
          item={it}
          projectUuid={projectUuid}
          activeFilterKey={[...activeFilters].sort().join(",")}
        />
      ))}
    </section>
  );
}

function AttentionRow({
  item,
  projectUuid,
  activeFilterKey,
}: {
  item: AttentionItem;
  projectUuid: string;
  activeFilterKey: string;
}): JSX.Element {
  const [expanded, setExpanded] = useState(false);
  const detailParts = describeDetail(item);
  const detail = useQuery<SegmentAuditDetail>({
    queryKey: ["audit", "segment-detail", projectUuid, item.satz_uuid],
    queryFn: () =>
      api.get<SegmentAuditDetail>(
        `/projects/${projectUuid}/audit/segments/${item.satz_uuid}/detail`,
      ),
    enabled: expanded,
  });
  return (
    <div>
      <div className="px-4 py-3 flex items-center gap-3 text-sm">
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="text-xs text-muted-foreground hover:text-foreground w-4 text-center"
          aria-label={expanded ? "Collapse" : "Expand"}
        >
          {expanded ? "▼" : "▶"}
        </button>
        <span
          className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${chipTone(item.filter_matched)}`}
        >
          {FILTER_LABEL[item.filter_matched] ?? item.filter_matched}
        </span>
        <span className="text-muted-foreground text-xs whitespace-nowrap">
          page #{item.page_index} · block #{item.block_index} · seg #{item.satz_index}
        </span>
        {detailParts && (
          <span className="text-xs text-muted-foreground truncate">
            {detailParts}
          </span>
        )}
        <span className="flex-1" />
        <Link
          to={`/projects/${projectUuid}/pages/${item.page_uuid}`}
          className="text-xs underline text-muted-foreground hover:text-foreground"
        >
          Open page
        </Link>
      </div>
      {expanded && (
        <div className="px-6 pb-4 -mt-1">
          {detail.isLoading && (
            <p className="text-xs text-muted-foreground italic">Loading detail…</p>
          )}
          {detail.error && <ErrorBox error={detail.error} />}
          {detail.data && (
            <SegmentDetailPanel
              detail={detail.data}
              item={item}
              projectUuid={projectUuid}
              activeFilterKey={activeFilterKey}
            />
          )}
        </div>
      )}
    </div>
  );
}

function SegmentDetailPanel({
  detail,
  item,
  projectUuid,
  activeFilterKey,
}: {
  detail: SegmentAuditDetail;
  item: AttentionItem;
  projectUuid: string;
  activeFilterKey: string;
}): JSX.Element {
  const qc = useQueryClient();
  const [actionError, setActionError] = useState<string | null>(null);
  const refreshAudit = async (): Promise<void> => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["audit", "attention", projectUuid, activeFilterKey] }),
      qc.invalidateQueries({ queryKey: ["audit", "summary", projectUuid] }),
      qc.invalidateQueries({ queryKey: ["audit", "segment-detail", projectUuid, item.satz_uuid] }),
    ]);
  };
  const enterReview = async (): Promise<void> => {
    await api.post(`/pages/${item.page_uuid}/ocr-review/enter`);
  };
  const acceptCurrent = useMutation({
    mutationFn: async () => {
      await enterReview();
      await api.post(`/pages/${item.page_uuid}/ocr-review/approve-go`, {
        note: "Accepted current OCR from Audit attention detail.",
      });
    },
    onSuccess: refreshAudit,
    onError: (err) => setActionError(err instanceof ApiError ? err.detail : String(err)),
  });
  const approveWarning = useMutation({
    mutationFn: async () => {
      await enterReview();
      await api.post(`/pages/${item.page_uuid}/ocr-review/approve-warning`, {
        note: "Approved OCR with warning from Audit attention detail.",
      });
    },
    onSuccess: refreshAudit,
    onError: (err) => setActionError(err instanceof ApiError ? err.detail : String(err)),
  });
  const markUnresolved = useMutation({
    mutationFn: enterReview,
    onSuccess: refreshAudit,
    onError: (err) => setActionError(err instanceof ApiError ? err.detail : String(err)),
  });
  const acceptAlternative = useMutation({
    mutationFn: async (text: string) => {
      await api.put(`/segments/${item.satz_uuid}/text`, { after_text: text });
      await enterReview();
      await api.post(`/pages/${item.page_uuid}/ocr-review/approve-go`, {
        note: "Accepted OCR engine alternative from Audit attention detail.",
      });
    },
    onSuccess: refreshAudit,
    onError: (err) => setActionError(err instanceof ApiError ? err.detail : String(err)),
  });
  const busy =
    acceptCurrent.isPending ||
    approveWarning.isPending ||
    markUnresolved.isPending ||
    acceptAlternative.isPending;
  const isOcrAttention = item.filter_matched === "low_confidence" || item.filter_matched === "divergent_ocr";
  const isTranslationAttention = item.filter_matched.startsWith("cross_check_");

  return (
    <div className="space-y-3 text-sm">
      {isOcrAttention && (
        <>
          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_18rem]">
            <div className="rounded-lg border bg-[#fffaf0] p-3">
              <div className="text-xs uppercase tracking-wide text-muted-foreground mb-2">
                OCR review actions
              </div>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" onClick={() => acceptCurrent.mutate()} disabled={busy}>
                  Accept current OCR
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => approveWarning.mutate()}
                  disabled={busy}
                >
                  Approve with warning
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => markUnresolved.mutate()}
                  disabled={busy}
                >
                  Mark unresolved
                </Button>
                <Button size="sm" variant="outline" asChild>
                  <Link to={`/projects/${projectUuid}/pages/${item.page_uuid}`}>Open page</Link>
                </Button>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                Critical OCR confidence still blocks approval. Use Open page to edit OCR directly
                or rerun OCR from the workspace.
              </p>
              {actionError && (
                <p className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-900">
                  {actionError}
                </p>
              )}
            </div>
            <PageScanReference pageUuid={item.page_uuid} pageIndex={item.page_index} />
          </div>

          {detail.current_text !== null && (
            <div>
              <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
                Current OCR text
              </div>
              <div
                dir="rtl"
                lang="ar"
                className="border rounded p-2 bg-muted/40 whitespace-pre-wrap leading-relaxed"
              >
                {detail.current_text}
              </div>
            </div>
          )}
        </>
      )}

      {isOcrAttention && detail.ocr_engines.length > 0 && (
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
            OCR engines ({detail.ocr_engine_agreement ?? "no agreement label"}
            {detail.ocr_confidence_score !== null
              ? ` · confidence ${detail.ocr_confidence_score.toFixed(3)}`
              : ""}
            {detail.ocr_confidence_class
              ? ` · ${detail.ocr_confidence_class}`
              : ""})
          </div>
          {!detail.ocr_engines_have_text && (
            <p className="text-xs italic text-amber-700 mb-1">
              Legacy OCR-PO: per-engine text not persisted. Re-run OCR on this
              segment to see side-by-side readings.
            </p>
          )}
          <div className="grid md:grid-cols-2 gap-2">
            {detail.ocr_engines.map((e, i) => (
              <EnginePanel
                key={`${e.engine}-${i}`}
                reading={e}
                currentText={detail.current_text}
                onAccept={
                  e.text
                    ? () => acceptAlternative.mutate(e.text ?? "")
                    : undefined
                }
                disabled={busy || !e.text || e.is_current}
              />
            ))}
          </div>
        </div>
      )}

      {isTranslationAttention && (
        <TranslationCrossCheckPanel detail={detail} item={item} projectUuid={projectUuid} />
      )}

      {detail.open_befunde.length > 0 && (
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
            Open audit findings ({detail.open_befunde.length})
          </div>
          <ul className="space-y-1">
            {detail.open_befunde.map((b) => (
              <li
                key={b.befund_uuid}
                className="border rounded p-2 bg-amber-50 text-xs"
              >
                <span className="font-medium">{b.regelkennung}</span>{" "}
                <span className="text-muted-foreground">
                  · {b.schweregrad} · {b.verstossklasse}
                </span>
                {Object.keys(b.detection_context).length > 0 && (
                  <pre className="mt-1 whitespace-pre-wrap break-words text-[10px] text-amber-900">
                    {JSON.stringify(b.detection_context, null, 2)}
                  </pre>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {detail.open_conflicts_count > 0 && (
        <div className="text-xs text-amber-700">
          {detail.open_conflicts_count} open conflict
          {detail.open_conflicts_count === 1 ? "" : "s"} on this segment.
        </div>
      )}

      {detail.ocr_engines.length === 0 &&
        !detail.translation_situation &&
        detail.open_befunde.length === 0 && (
          <p className="text-xs italic text-muted-foreground">
            No OCR-PO or TRANSLATION-PO recorded for this segment yet.
          </p>
        )}
    </div>
  );
}

function PageScanReference({
  pageUuid,
  pageIndex,
}: {
  pageUuid: string;
  pageIndex: number;
}): JSX.Element {
  const token = useAuthStore((s) => s.token);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let revoke: string | null = null;
    let cancelled = false;
    setBlobUrl(null);
    setError(null);
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    fetch(apiPath(`/pages/${pageUuid}/render-png?dpi=120`), { headers })
      .then(async (resp) => {
        if (!resp.ok) throw new Error(await resp.text());
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
      if (revoke) URL.revokeObjectURL(revoke);
    };
  }, [pageUuid, token]);

  return (
    <div className="rounded-lg border bg-card p-2">
      <div className="mb-2 flex items-center justify-between gap-2 text-xs">
        <span className="uppercase tracking-wide text-muted-foreground">
          Original page #{pageIndex}
        </span>
        <Link
          to={`/projects/${pageUuid}`}
          className="hidden text-muted-foreground underline"
        >
          open
        </Link>
      </div>
      {error && (
        <p className="text-xs text-amber-800">
          Original preview unavailable here. Open the page for the full scan.
        </p>
      )}
      {!error && !blobUrl && (
        <p className="text-xs text-muted-foreground">Loading page image…</p>
      )}
      {blobUrl && (
        <a href={blobUrl} target="_blank" rel="noreferrer" title="Open rendered page image">
          <img
            src={blobUrl}
            alt={`Original page ${pageIndex}`}
            className="max-h-64 w-full rounded border object-contain"
          />
        </a>
      )}
      <p className="mt-2 text-[11px] text-muted-foreground">
        Region crop/retry is handled in the DPI Compare recovery tool.
      </p>
    </div>
  );
}

function TranslationCrossCheckPanel({
  detail,
  item,
  projectUuid,
}: {
  detail: SegmentAuditDetail;
  item: AttentionItem;
  projectUuid: string;
}): JSX.Element {
  const primaryText = detail.translation_primary_output ?? detail.translation_target_text;
  const checkText = detail.translation_check_output;

  return (
    <div className="space-y-3">
      <div className="rounded-lg border bg-[#f8f4ea] p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-xs uppercase tracking-wide text-muted-foreground">
              Translation cross-check
            </div>
            <div className="mt-1 text-sm font-medium">
              {detail.translation_situation ?? item.filter_matched}
            </div>
          </div>
          <Button size="sm" variant="outline" asChild>
            <Link to={`/projects/${projectUuid}/pages/${item.page_uuid}`}>Open translation page</Link>
          </Button>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          This section shows translated text only. OCR evidence is shown only under OCR confidence
          and divergent-engine attention rows.
        </p>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <TranslationOutputPanel
          label="Primary translation"
          engine={detail.translation_primary_engine}
          text={primaryText}
          active
        />
        <TranslationOutputPanel
          label="Cross-check translation"
          engine={detail.translation_check_engine}
          text={checkText}
          error={detail.translation_check_error}
        />
      </div>

      {detail.translation_target_text && detail.translation_target_text !== primaryText && (
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
            Saved translated text
          </div>
          <div className="rounded border bg-muted/40 p-3 leading-relaxed whitespace-pre-wrap">
            {detail.translation_target_text}
          </div>
        </div>
      )}
    </div>
  );
}

function TranslationOutputPanel({
  label,
  engine,
  text,
  error,
  active = false,
}: {
  label: string;
  engine: string | null;
  text: string | null;
  error?: string | null;
  active?: boolean;
}): JSX.Element {
  return (
    <div className={active ? "rounded border border-emerald-300 bg-emerald-50/40" : "rounded border bg-card"}>
      <div className="flex items-center justify-between gap-2 border-b px-3 py-2 text-xs text-muted-foreground">
        <span className="font-medium">{label}</span>
        <span>{engine ?? "unknown engine"}</span>
      </div>
      {text ? (
        <div className="max-h-80 overflow-auto whitespace-pre-wrap p-3 leading-relaxed">
          {text}
        </div>
      ) : error ? (
        <div className="p-3 text-xs text-red-800">
          Cross-check failed: {error}
        </div>
      ) : (
        <div className="p-3 text-xs italic text-muted-foreground">
          No translated output recorded for this side.
        </div>
      )}
    </div>
  );
}

function EnginePanel({
  reading,
  currentText,
  onAccept,
  disabled,
}: {
  reading: EngineReading;
  currentText: string | null;
  onAccept?: () => void;
  disabled?: boolean;
}): JSX.Element {
  const titleParts: string[] = [reading.engine];
  if (reading.confidence !== null) {
    titleParts.push(`conf ${reading.confidence.toFixed(3)}`);
  }
  titleParts.push(`${reading.text_chars} chars`);
  return (
    <div className={reading.is_current ? "rounded border border-emerald-300 bg-emerald-50/40" : "border rounded bg-card"}>
      <div className="px-2 py-1 text-xs border-b text-muted-foreground flex justify-between">
        <span className="font-medium">{titleParts.join(" · ")}</span>
        <span className="flex items-center gap-2">
          {reading.is_current && (
            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-emerald-800">
              active
            </span>
          )}
          {reading.error_class && (
            <span className="text-red-700">{reading.error_class}</span>
          )}
        </span>
      </div>
      {reading.text ? (
        <>
          <HighlightedArabicText text={reading.text} currentText={currentText} />
          <div className="border-t px-2 py-2">
            <Button
              size="sm"
              variant="outline"
              onClick={onAccept}
              disabled={disabled}
            >
              {reading.is_current ? "Current OCR" : "Accept this reading"}
            </Button>
          </div>
        </>
      ) : (
        <div className="p-2 text-xs italic text-muted-foreground">
          (text not persisted; legacy OCR-PO)
        </div>
      )}
    </div>
  );
}

function HighlightedArabicText({
  text,
  currentText,
}: {
  text: string;
  currentText: string | null;
}): JSX.Element {
  const changed = Boolean(currentText && currentText.trim() !== text.trim());
  return (
    <div
      dir="rtl"
      lang="ar"
      className="max-h-48 overflow-auto whitespace-pre-wrap p-2 leading-relaxed"
    >
      {changed ? (
        <mark className="rounded bg-amber-100 px-1 text-inherit">{text}</mark>
      ) : (
        text
      )}
    </div>
  );
}

function describeDetail(item: AttentionItem): string | null {
  const d = item.detail;
  switch (item.filter_matched) {
    case "low_confidence":
      return `${String(d.confidence_class)} (${typeof d.confidence_score === "number" ? d.confidence_score.toFixed(3) : "?"})`;
    case "divergent_ocr":
      return "engines disagreed";
    case "cross_check_substantive":
    case "cross_check_ambiguity":
    case "cross_check_failed":
      return String(d.situation ?? "");
    case "open_audit_finding":
      return `${String(d.regelkennung)} · ${String(d.schweregrad)}`;
    case "open_conflict":
      return `${String(d.rule_source)} / ${String(d.conflict_type)}`;
    default:
      return null;
  }
}

function chipTone(filter: string): string {
  switch (filter) {
    case "low_confidence":
    case "divergent_ocr":
    case "cross_check_ambiguity":
      return "bg-amber-100 text-amber-900";
    case "cross_check_substantive":
    case "cross_check_failed":
    case "open_audit_finding":
    case "open_conflict":
      return "bg-red-100 text-red-900";
    default:
      return "bg-muted text-foreground";
  }
}
