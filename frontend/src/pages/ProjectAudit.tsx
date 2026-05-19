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
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { ApiError, api } from "@/lib/api";
import { Button } from "@/components/ui/button";

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
        />
      ))}
    </section>
  );
}

function AttentionRow({
  item,
  projectUuid,
}: {
  item: AttentionItem;
  projectUuid: string;
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
          {detail.data && <SegmentDetailPanel detail={detail.data} />}
        </div>
      )}
    </div>
  );
}

function SegmentDetailPanel({
  detail,
}: {
  detail: SegmentAuditDetail;
}): JSX.Element {
  return (
    <div className="space-y-3 text-sm">
      {detail.current_text !== null && (
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
            Current segment text
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

      {detail.ocr_engines.length > 0 && (
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
              <EnginePanel key={`${e.engine}-${i}`} reading={e} />
            ))}
          </div>
        </div>
      )}

      {detail.translation_situation && (
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
            Translation — cross-check: {detail.translation_situation}
          </div>
          {(detail.translation_primary_engine || detail.translation_check_engine) && (
            <div className="mb-2 text-xs text-muted-foreground">
              Primary: {detail.translation_primary_engine ?? "unknown"} · Check:{" "}
              {detail.translation_check_engine ?? "unknown"}
            </div>
          )}
          {detail.translation_target_text && (
            <div className="border rounded p-2 bg-muted/40 whitespace-pre-wrap leading-relaxed">
              {detail.translation_target_text}
            </div>
          )}
        </div>
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

function EnginePanel({ reading }: { reading: EngineReading }): JSX.Element {
  const titleParts: string[] = [reading.engine];
  if (reading.confidence !== null) {
    titleParts.push(`conf ${reading.confidence.toFixed(3)}`);
  }
  titleParts.push(`${reading.text_chars} chars`);
  return (
    <div className="border rounded bg-card">
      <div className="px-2 py-1 text-xs border-b text-muted-foreground flex justify-between">
        <span className="font-medium">{titleParts.join(" · ")}</span>
        {reading.error_class && (
          <span className="text-red-700">{reading.error_class}</span>
        )}
      </div>
      {reading.text ? (
        <div
          dir="rtl"
          lang="ar"
          className="p-2 whitespace-pre-wrap leading-relaxed max-h-48 overflow-auto"
        >
          {reading.text}
        </div>
      ) : (
        <div className="p-2 text-xs italic text-muted-foreground">
          (text not persisted; legacy OCR-PO)
        </div>
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
