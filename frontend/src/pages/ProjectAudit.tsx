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
import { Link, useParams, useSearchParams } from "react-router-dom";
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
  issue_uuid: string | null;
  issue_state: string | null;
  issue_group_key: string | null;
  detail: Record<string, unknown>;
}

interface AttentionListResponse {
  items: AttentionItem[];
}

interface OcrReviewDecisionItem {
  decision_event_uuid: string;
  page_uuid: string;
  page_index: number;
  satz_uuid: string | null;
  decision_type: string;
  content: Record<string, unknown>;
  created_at: string;
}

interface OcrReviewDecisionListResponse {
  items: OcrReviewDecisionItem[];
}

interface OcrDifferenceExplanation {
  provider: string;
  model: string;
  summary: string;
  recommended_reading: string;
  confidence: number;
  normalization_notes: string[];
  line_differences: {
    line_number: number;
    gemini_line: string;
    openai_line: string;
    differences: string[];
  }[];
  character_differences: {
    gemini: string;
    openai: string;
    explanation: string;
    severity: string;
  }[];
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

type AuditTab = "active" | "resolved";
type ResolvedDecisionFilter =
  | "all"
  | "accepted"
  | "warning"
  | "unresolved"
  | "superseded"
  | "historical"
  | "ignored_deleted";

const RESOLVED_DECISION_FILTERS: ResolvedDecisionFilter[] = [
  "all",
  "accepted",
  "warning",
  "unresolved",
  "superseded",
  "historical",
  "ignored_deleted",
];

const AUDIT_FILTER_VALUES = new Set(FILTER_OPTIONS.map((option) => option.value));

export function ProjectAuditPage(): JSX.Element {
  const { projectUuid } = useParams<{ projectUuid: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeFilters, setActiveFilters] = useState<Set<string>>(() =>
    parseAuditFilters(searchParams),
  );
  const [auditTab, setAuditTab] = useState<AuditTab>(
    searchParams.get("tab") === "resolved" ? "resolved" : "active",
  );
  const [resolvedFilter, setResolvedFilter] = useState<ResolvedDecisionFilter>(() =>
    parseResolvedDecisionFilter(searchParams.get("resolved")),
  );

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
    enabled: !!projectUuid && auditTab === "active",
  });

  const ocrReviewDecisions = useQuery<OcrReviewDecisionListResponse>({
    queryKey: ["audit", "ocr-review-decisions", projectUuid],
    queryFn: () =>
      api.get<OcrReviewDecisionListResponse>(
        `/projects/${projectUuid}/audit/ocr-review-decisions`,
      ),
    enabled: !!projectUuid && auditTab === "resolved",
  });

  const toggleFilter = (value: string): void => {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  };

  useEffect(() => {
    setActiveFilters(parseAuditFilters(searchParams));
    setAuditTab(searchParams.get("tab") === "resolved" ? "resolved" : "active");
    setResolvedFilter(parseResolvedDecisionFilter(searchParams.get("resolved")));
  }, [searchParams]);

  useEffect(() => {
    const next = new URLSearchParams(searchParams);
    setSearchParamOrDelete(next, "tab", auditTab === "resolved" ? "resolved" : null);
    next.delete("filter");
    for (const filter of [...activeFilters].sort()) {
      next.append("filter", filter);
    }
    setSearchParamOrDelete(
      next,
      "resolved",
      auditTab === "resolved" && resolvedFilter !== "all" ? resolvedFilter : null,
    );
    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true });
    }
  }, [activeFilters, auditTab, resolvedFilter, searchParams, setSearchParams]);

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

      <AuditTabs active={auditTab} onChange={setAuditTab} />

      {auditTab === "active" && (
        <>
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
              focusKey={searchParams.get("focus")}
            />
          )}
        </>
      )}

      {auditTab === "resolved" && (
        <>
          {ocrReviewDecisions.isLoading && (
            <div className="text-sm text-muted-foreground">Loading resolved OCR decisions…</div>
          )}
          {ocrReviewDecisions.error && <ErrorBox error={ocrReviewDecisions.error} />}
          {ocrReviewDecisions.data && (
            <ResolvedOcrDecisionList
              items={ocrReviewDecisions.data.items}
              projectUuid={projectUuid}
              filter={resolvedFilter}
              onFilterChange={setResolvedFilter}
            />
          )}
        </>
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

function parseAuditFilters(searchParams: URLSearchParams): Set<string> {
  return new Set(searchParams.getAll("filter").filter((value) => AUDIT_FILTER_VALUES.has(value)));
}

function parseResolvedDecisionFilter(value: string | null): ResolvedDecisionFilter {
  return RESOLVED_DECISION_FILTERS.includes(value as ResolvedDecisionFilter)
    ? (value as ResolvedDecisionFilter)
    : "all";
}

function setSearchParamOrDelete(
  params: URLSearchParams,
  key: string,
  value: string | null,
): void {
  if (value === null || value === "") {
    params.delete(key);
    return;
  }
  params.set(key, value);
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

function AuditTabs({
  active,
  onChange,
}: {
  active: AuditTab;
  onChange: (tab: AuditTab) => void;
}): JSX.Element {
  return (
    <section className="rounded-lg border bg-card p-2">
      <div className="grid grid-cols-2 gap-2">
        <Button
          type="button"
          variant={active === "active" ? "default" : "outline"}
          onClick={() => onChange("active")}
        >
          Active attention
        </Button>
        <Button
          type="button"
          variant={active === "resolved" ? "default" : "outline"}
          onClick={() => onChange("resolved")}
        >
          Resolved OCR decisions
        </Button>
      </div>
      <p className="mt-2 px-1 text-xs text-muted-foreground">
        Active attention shows unresolved work only. Resolved OCR decisions show where
        accepted OCR findings move after page approval or approval with warning.
      </p>
    </section>
  );
}

interface AttentionGroup {
  key: string;
  primary: AttentionItem;
  reasons: AttentionItem[];
}

function AttentionList({
  items,
  projectUuid,
  activeFilters,
  focusKey,
}: {
  items: AttentionItem[];
  projectUuid: string;
  activeFilters: Set<string>;
  focusKey: string | null;
}): JSX.Element {
  const groups = useMemo(() => groupAttentionItems(items), [items]);

  if (groups.length === 0) {
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
        Attention list ({groups.length}
        {groups.length === items.length ? "" : ` groups from ${items.length} signals`})
      </div>
      {groups.map((group) => (
        <AttentionRow
          key={group.key}
          group={group}
          projectUuid={projectUuid}
          activeFilterKey={[...activeFilters].sort().join(",")}
          autoExpand={focusKey === attentionFocusKey(group)}
        />
      ))}
    </section>
  );
}

function AttentionRow({
  group,
  projectUuid,
  activeFilterKey,
  autoExpand,
}: {
  group: AttentionGroup;
  projectUuid: string;
  activeFilterKey: string;
  autoExpand: boolean;
}): JSX.Element {
  const item = group.primary;
  const [expanded, setExpanded] = useState(autoExpand);
  const detailParts = group.reasons.map(describeDetail).filter(Boolean).join(" · ");
  const detail = useQuery<SegmentAuditDetail>({
    queryKey: ["audit", "segment-detail", projectUuid, item.satz_uuid],
    queryFn: () =>
      api.get<SegmentAuditDetail>(
        `/projects/${projectUuid}/audit/segments/${item.satz_uuid}/detail`,
      ),
    enabled: expanded,
  });
  useEffect(() => {
    if (autoExpand) setExpanded(true);
  }, [autoExpand]);
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
          {group.reasons.length > 1
            ? `${group.reasons.length} active signals`
            : FILTER_LABEL[item.filter_matched] ?? item.filter_matched}
        </span>
        <span className="flex flex-wrap gap-1">
          {group.reasons.map((reason) => (
            <span
              key={reason.filter_matched}
              className={`rounded px-1.5 py-0.5 text-[10px] ${chipTone(reason.filter_matched)}`}
              title={reasonDefinition(reason.filter_matched)}
            >
              {FILTER_LABEL[reason.filter_matched] ?? reason.filter_matched}
            </span>
          ))}
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
          to={`/projects/${projectUuid}/pages/${item.page_uuid}?from=attention&focus=${attentionFocusKey(group)}`}
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
              group={group}
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
  group,
  projectUuid,
  activeFilterKey,
}: {
  detail: SegmentAuditDetail;
  group: AttentionGroup;
  projectUuid: string;
  activeFilterKey: string;
}): JSX.Element {
  const item = group.primary;
  const qc = useQueryClient();
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<OcrDifferenceExplanation | null>(null);
  const [explanationError, setExplanationError] = useState<string | null>(null);
  const geminiReading = detail.ocr_engines.find((reading) => isGeminiEngine(reading.engine));
  const openaiReading = detail.ocr_engines.find((reading) => isOpenAiEngine(reading.engine));
  const refreshAudit = async (): Promise<void> => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["audit", "attention", projectUuid, activeFilterKey] }),
      qc.invalidateQueries({ queryKey: ["audit", "summary", projectUuid] }),
      qc.invalidateQueries({ queryKey: ["audit", "segment-detail", projectUuid, item.satz_uuid] }),
      qc.invalidateQueries({ queryKey: ["audit", "ocr-review-decisions", projectUuid] }),
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
    onSuccess: async () => {
      setActionError(null);
      setActionMessage("Finding accepted and moved out of Active attention.");
      await refreshAudit();
    },
    onError: (err) => {
      setActionMessage(null);
      setActionError(err instanceof ApiError ? err.detail : String(err));
    },
  });
  const approveWarning = useMutation({
    mutationFn: async () => {
      await enterReview();
      await api.post(`/pages/${item.page_uuid}/ocr-review/approve-warning`, {
        note: "Approved OCR with warning from Audit attention detail.",
      });
    },
    onSuccess: async () => {
      setActionError(null);
      setActionMessage("Finding accepted with warning and moved to OCR decision history.");
      await refreshAudit();
    },
    onError: (err) => {
      setActionMessage(null);
      setActionError(err instanceof ApiError ? err.detail : String(err));
    },
  });
  const markUnresolved = useMutation({
    mutationFn: async () => {
      await enterReview();
      await api.post(
        `/projects/${projectUuid}/audit/segments/${item.satz_uuid}/ocr-attention-decision`,
        {
          action: "mark_unresolved",
          filter_matched: group.reasons.map((reason) => reason.filter_matched).join(","),
          issue_uuid: group.primary.issue_uuid,
          reason: "Marked unresolved from Audit attention detail.",
        },
      );
    },
    onSuccess: async () => {
      setActionError(null);
      setActionMessage("Finding remains active and the page is back in OCR review.");
      await refreshAudit();
    },
    onError: (err) => {
      setActionMessage(null);
      setActionError(err instanceof ApiError ? err.detail : String(err));
    },
  });
  const acceptAlternative = useMutation({
    mutationFn: async (text: string) => {
      await api.put(`/segments/${item.satz_uuid}/text`, { after_text: text });
      await enterReview();
      await api.post(`/pages/${item.page_uuid}/ocr-review/approve-go`, {
        note: "Accepted OCR engine alternative from Audit attention detail.",
      });
    },
    onSuccess: async () => {
      setActionError(null);
      setActionMessage("Alternative OCR reading accepted and linked findings were resolved.");
      await refreshAudit();
    },
    onError: (err) => {
      setActionMessage(null);
      setActionError(err instanceof ApiError ? err.detail : String(err));
    },
  });
  const ignoreFinding = useMutation({
    mutationFn: async () => {
      await api.post(
        `/projects/${projectUuid}/audit/segments/${item.satz_uuid}/ocr-attention-decision`,
        {
          action: "ignore",
          filter_matched: group.reasons.map((reason) => reason.filter_matched).join(","),
          issue_uuid: group.primary.issue_uuid,
          reason: "Ignored from Audit attention detail.",
        },
      );
    },
    onSuccess: async () => {
      setActionError(null);
      setActionMessage("Finding ignored and moved to the Ignored / deleted filter.");
      await refreshAudit();
    },
    onError: (err) => {
      setActionMessage(null);
      setActionError(err instanceof ApiError ? err.detail : String(err));
    },
  });
  const deleteFinding = useMutation({
    mutationFn: async () => {
      await api.post(
        `/projects/${projectUuid}/audit/segments/${item.satz_uuid}/ocr-attention-decision`,
        {
          action: "delete",
          filter_matched: group.reasons.map((reason) => reason.filter_matched).join(","),
          issue_uuid: group.primary.issue_uuid,
          reason: "Deleted/hidden from Audit attention detail.",
        },
      );
    },
    onSuccess: async () => {
      setActionError(null);
      setActionMessage("Finding hidden and moved to the Ignored / deleted filter.");
      await refreshAudit();
    },
    onError: (err) => {
      setActionMessage(null);
      setActionError(err instanceof ApiError ? err.detail : String(err));
    },
  });
  const explainDifference = useMutation({
    mutationFn: async () => {
      if (!geminiReading?.text || !openaiReading?.text) {
        throw new Error("Both Gemini and OpenAI OCR readings must be available before differences can be explained.");
      }
      return api.post<OcrDifferenceExplanation>(
        `/projects/${projectUuid}/audit/segments/${item.satz_uuid}/ocr-difference-explanation`,
        {
          gemini_text: geminiReading.text,
          openai_text: openaiReading.text,
        },
      );
    },
    onSuccess: (resp) => {
      setExplanationError(null);
      setExplanation(resp);
    },
    onError: (err) => {
      setExplanation(null);
      setExplanationError(err instanceof ApiError ? err.detail : String(err));
    },
  });
  const busy =
    acceptCurrent.isPending ||
    approveWarning.isPending ||
    markUnresolved.isPending ||
    acceptAlternative.isPending ||
    ignoreFinding.isPending ||
    deleteFinding.isPending ||
    explainDifference.isPending;
  const isOcrAttention = group.reasons.some(
    (reason) =>
      reason.filter_matched === "low_confidence" ||
      reason.filter_matched === "divergent_ocr",
  );
  const isTranslationAttention = item.filter_matched.startsWith("cross_check_");

  return (
    <div className="space-y-3 text-sm">
      {isOcrAttention && (
        <>
          <div className="grid gap-3 xl:grid-cols-[minmax(0,0.95fr)_minmax(24rem,1.05fr)]">
            <div className="rounded-lg border bg-[#fffaf0] p-3">
              <div className="text-xs uppercase tracking-wide text-muted-foreground mb-2">
                OCR review actions · {group.reasons.length} active signal{group.reasons.length === 1 ? "" : "s"}
              </div>
              <ReasonSummary reasons={group.reasons} />
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
                  <Link to={`/projects/${projectUuid}/pages/${item.page_uuid}?from=attention&focus=${attentionFocusKey(group)}`}>Open page</Link>
                </Button>
                <Button size="sm" variant="outline" asChild>
                  <Link
                    to={`/projects/${projectUuid}/pages/${item.page_uuid}?panel=dpi&from=attention&focus=${attentionFocusKey(group)}&issue=${encodeURIComponent(group.reasons.map((reason) => reason.filter_matched).join(","))}${group.primary.issue_uuid ? `&issue_uuid=${group.primary.issue_uuid}` : ""}`}
                  >
                    Open DPI retry
                  </Link>
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => ignoreFinding.mutate()}
                  disabled={busy}
                  title="Hide this OCR attention item from the active list while keeping it in the explicit ignored/deleted history filter."
                >
                  Ignore finding
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => deleteFinding.mutate()}
                  disabled={busy}
                  title="Hide this OCR attention item as deleted/ignored history. No OCR text or evidence is physically deleted."
                >
                  Mark deleted
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
              {actionMessage && (
                <p className="mt-2 rounded border border-emerald-200 bg-emerald-50 p-2 text-xs text-emerald-900">
                  {actionMessage}
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
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <div className="text-xs uppercase tracking-wide text-muted-foreground">
              OCR engines ({detail.ocr_engine_agreement ?? "no agreement label"}
              {detail.ocr_confidence_score !== null
                ? ` · confidence ${detail.ocr_confidence_score.toFixed(3)}`
                : ""}
              {detail.ocr_confidence_class
                ? ` · ${detail.ocr_confidence_class}`
                : ""})
            </div>
            <Button
              size="sm"
              variant="outline"
              className="ml-auto"
              onClick={() => {
                if (explanation) {
                  setExplanation(null);
                  setExplanationError(null);
                } else if (!geminiReading?.text || !openaiReading?.text) {
                  const missing = [
                    !geminiReading?.text ? "Gemini" : null,
                    !openaiReading?.text ? "OpenAI" : null,
                  ].filter(Boolean);
                  setExplanationError(
                    `${missing.join(" and ")} OCR text is missing from this audit record. Re-run OCR with both engines to explain differences.`,
                  );
                } else {
                  explainDifference.mutate();
                }
              }}
              disabled={explainDifference.isPending}
              title={
                geminiReading?.text && openaiReading?.text
                  ? "Compare the displayed OpenAI OCR against the displayed Gemini OCR."
                  : "Click to see which OCR engine text is missing."
              }
            >
              {explanation ? "Hide differences" : "Explain differences"}
            </Button>
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
                currentText={geminiReading?.text ?? detail.current_text}
                onAccept={
                  !e.is_current && e.text
                    ? () => acceptAlternative.mutate(e.text ?? "")
                    : undefined
                }
                disabled={busy || !e.text || e.is_current}
              />
            ))}
          </div>
          {explanationError && (
            <p className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-900">
              {explanationError}
            </p>
          )}
          {explanation && <OcrDifferenceExplanationPanel explanation={explanation} />}
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
    <div className="rounded-lg border bg-card p-3">
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
            className="max-h-[42rem] min-h-[24rem] w-full rounded border bg-[#f8f4ea] object-contain"
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
  onExplain,
  explainLabel = "Explain differences",
  explainDisabled,
  disabled,
}: {
  reading: EngineReading;
  currentText: string | null;
  onAccept?: () => void;
  onExplain?: () => void;
  explainLabel?: string;
  explainDisabled?: boolean;
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
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={onAccept}
                disabled={disabled}
              >
                {reading.is_current ? "Current OCR" : "Accept this reading"}
              </Button>
              {onExplain && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={onExplain}
                  disabled={explainDisabled ?? disabled}
                >
                  {explainLabel}
                </Button>
              )}
            </div>
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

function OcrDifferenceExplanationPanel({
  explanation,
}: {
  explanation: OcrDifferenceExplanation;
}): JSX.Element {
  return (
    <div className="mt-2 rounded-lg border bg-[#f8fbf7] p-3 text-xs">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="font-medium text-foreground">OpenAI OCR comparison</span>
        <span className="text-muted-foreground">
          {explanation.model} · confidence {explanation.confidence.toFixed(2)}
        </span>
      </div>
      <p className="text-muted-foreground">{explanation.summary}</p>
      {explanation.line_differences.length > 0 && (
        <div className="mt-2">
          <div className="mb-1 font-medium">Line-by-line differences</div>
          <ul className="space-y-2">
            {explanation.line_differences.map((line) => (
              <li key={line.line_number} className="rounded border bg-background p-2">
                <div className="mb-1 font-medium">Line {line.line_number}</div>
                <div className="grid gap-2 md:grid-cols-2">
                  <div>
                    <div className="mb-1 text-muted-foreground">Gemini</div>
                    <div dir="rtl" lang="ar" className="rounded bg-muted/40 p-2 leading-relaxed">
                      {line.gemini_line || "(empty)"}
                    </div>
                  </div>
                  <div>
                    <div className="mb-1 text-muted-foreground">OpenAI</div>
                    <div dir="rtl" lang="ar" className="rounded bg-muted/40 p-2 leading-relaxed">
                      {line.openai_line || "(empty)"}
                    </div>
                  </div>
                </div>
                {line.differences.length > 0 && (
                  <ul className="mt-2 list-disc space-y-1 pl-4 text-muted-foreground">
                    {line.differences.map((diff, index) => (
                      <li key={`${line.line_number}-${index}`}>{diff}</li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      {explanation.recommended_reading.trim() && (
        <div className="mt-2">
          <div className="mb-1 font-medium">Recommended reading</div>
          <div dir="rtl" lang="ar" className="rounded border bg-background p-2 leading-relaxed">
            {explanation.recommended_reading}
          </div>
        </div>
      )}
      {explanation.character_differences.length > 0 && (
        <div className="mt-2">
          <div className="mb-1 font-medium">Character differences</div>
          <ul className="space-y-1">
            {explanation.character_differences.map((diff, index) => (
              <li key={`${diff.gemini}-${diff.openai}-${index}`} className="rounded border bg-background p-2">
                <span dir="rtl" lang="ar" className="font-medium">
                  {diff.gemini || "(none)"} -&gt; {diff.openai || "(none)"}
                </span>
                <span className="text-muted-foreground"> · {diff.severity}</span>
                <div className="mt-1 text-muted-foreground">{diff.explanation}</div>
              </li>
            ))}
          </ul>
        </div>
      )}
      {explanation.normalization_notes.length > 0 && (
        <p className="mt-2 text-muted-foreground">
          Notes: {explanation.normalization_notes.join("; ")}
        </p>
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
  const parts = diffInlineText(text, currentText);
  return (
    <div
      dir="rtl"
      lang="ar"
      className="max-h-48 overflow-auto whitespace-pre-wrap p-2 leading-relaxed"
    >
      {parts.map((part, index) =>
        part.changed ? (
          <mark key={index} className="rounded bg-amber-100 px-0.5 text-inherit">
            {part.text}
          </mark>
        ) : (
          <span key={index}>{part.text}</span>
        ),
      )}
    </div>
  );
}

function ReasonSummary({ reasons }: { reasons: AttentionItem[] }): JSX.Element {
  return (
    <ul className="mb-3 space-y-1 text-xs text-muted-foreground">
      {reasons.map((reason) => (
        <li key={reason.filter_matched}>
          <span className="font-medium text-foreground">
            {FILTER_LABEL[reason.filter_matched] ?? reason.filter_matched}:
          </span>{" "}
          {reasonDefinition(reason.filter_matched)}
          {describeDetail(reason) ? ` (${describeDetail(reason)})` : ""}
        </li>
      ))}
    </ul>
  );
}

function ResolvedOcrDecisionList({
  items,
  projectUuid,
  filter,
  onFilterChange,
}: {
  items: OcrReviewDecisionItem[];
  projectUuid: string;
  filter: ResolvedDecisionFilter;
  onFilterChange: (filter: ResolvedDecisionFilter) => void;
}): JSX.Element {
  const filteredItems = items.filter((item) => decisionMatchesFilter(item, filter));

  if (items.length === 0) {
    return (
      <section className="border rounded-lg p-4 bg-card text-sm text-muted-foreground italic">
        No OCR review decisions have been recorded yet.
      </section>
    );
  }

  return (
    <section className="border rounded-lg bg-card">
      <div className="border-b px-4 py-3">
        <div className="text-xs uppercase tracking-wide text-muted-foreground">
          Resolved OCR decisions ({filteredItems.length} of {items.length})
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          {[
            ["all", "All"],
            ["accepted", "Accepted / resolved"],
            ["warning", "Accepted with warning"],
            ["unresolved", "Unresolved"],
            ["superseded", "Superseded by retry"],
            ["historical", "Historical"],
            ["ignored_deleted", "Ignored / deleted"],
          ].map(([value, label]) => (
            <Button
              key={value}
              size="sm"
              variant={filter === value ? "default" : "outline"}
              onClick={() => onFilterChange(value as ResolvedDecisionFilter)}
            >
              {label}
            </Button>
          ))}
        </div>
      </div>
      {filteredItems.length === 0 && (
        <div className="p-4 text-sm italic text-muted-foreground">
          No OCR decisions match this filter.
        </div>
      )}
      {filteredItems.map((item) => {
        const acceptedCount = Number(item.content.accepted_nonblocking_error_count ?? 0);
        const codes = Array.isArray(item.content.accepted_nonblocking_error_codes)
          ? item.content.accepted_nonblocking_error_codes.map(String)
          : [];
        return (
          <div key={item.decision_event_uuid} className="px-4 py-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`rounded px-2 py-0.5 text-xs font-medium ${decisionTone(item.decision_type)}`}>
                {decisionLabel(item.decision_type)}
              </span>
              <span className="text-xs text-muted-foreground">
                page #{item.page_index}
                {item.satz_uuid ? " · segment-level" : " · page-level"} ·{" "}
                {new Date(item.created_at).toLocaleString()}
              </span>
              <span className="flex-1" />
              <Link
                to={`/projects/${projectUuid}/pages/${item.page_uuid}`}
                className="text-xs underline text-muted-foreground hover:text-foreground"
              >
                Open page
              </Link>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              {item.decision_type === "ocr_attention_superseded_by_rerun"
                ? "OCR retry acceptance superseded this active attention item."
                : acceptedCount > 0
                ? `${acceptedCount} non-blocking OCR finding${acceptedCount === 1 ? "" : "s"} accepted/resolved.`
                : "Page-level OCR review decision recorded."}
              {codes.length > 0 ? ` Codes: ${codes.join(", ")}.` : ""}
            </p>
            {item.decision_type === "ocr_attention_superseded_by_rerun" && (
              <RetryDecisionDetails content={item.content} />
            )}
            {typeof item.content.note === "string" && item.content.note.trim() && (
              <p className="mt-1 rounded bg-muted/50 px-2 py-1 text-xs">
                {item.content.note}
              </p>
            )}
          </div>
        );
      })}
    </section>
  );
}

function groupAttentionItems(items: AttentionItem[]): AttentionGroup[] {
  const groups = new Map<string, AttentionGroup>();
  for (const item of items) {
    const isOcr =
      item.filter_matched === "low_confidence" || item.filter_matched === "divergent_ocr";
    const key = isOcr
      ? `ocr:${item.page_uuid}:${item.block_uuid}:${item.satz_uuid}`
      : `${item.filter_matched}:${item.page_uuid}:${item.block_uuid}:${item.satz_uuid}`;
    const existing = groups.get(key);
    if (existing) {
      existing.reasons.push(item);
    } else {
      groups.set(key, { key, primary: item, reasons: [item] });
    }
  }
  return [...groups.values()];
}

function attentionFocusKey(group: AttentionGroup): string {
  const item = group.primary;
  return encodeURIComponent(`${item.page_uuid}:${item.block_uuid}:${item.satz_uuid}`);
}

function isGeminiEngine(engine: string): boolean {
  return engine.toLowerCase().includes("gemini");
}

function isOpenAiEngine(engine: string): boolean {
  return engine.toLowerCase().includes("openai") || engine.toLowerCase().includes("gpt");
}

function diffInlineText(
  text: string,
  currentText: string | null,
): { text: string; changed: boolean }[] {
  if (!currentText || currentText.trim() === text.trim()) {
    return [{ text, changed: false }];
  }

  const candidate = [...text];
  const current = [...currentText];
  let prefix = 0;
  while (
    prefix < candidate.length &&
    prefix < current.length &&
    candidate[prefix] === current[prefix]
  ) {
    prefix += 1;
  }

  let suffix = 0;
  while (
    suffix < candidate.length - prefix &&
    suffix < current.length - prefix &&
    candidate[candidate.length - 1 - suffix] === current[current.length - 1 - suffix]
  ) {
    suffix += 1;
  }

  const parts: { text: string; changed: boolean }[] = [];
  const before = candidate.slice(0, prefix).join("");
  const changed = candidate.slice(prefix, candidate.length - suffix).join("");
  const after = suffix > 0 ? candidate.slice(candidate.length - suffix).join("") : "";
  if (before) parts.push({ text: before, changed: false });
  if (changed) parts.push({ text: changed, changed: true });
  if (after) parts.push({ text: after, changed: false });
  return parts.length > 0 ? parts : [{ text, changed: true }];
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

function reasonDefinition(filter: string): string {
  switch (filter) {
    case "low_confidence":
      return "The OCR result was scored below the accepted confidence band.";
    case "divergent_ocr":
      return "OCR engines produced different readings for the same segment.";
    case "cross_check_substantive":
      return "The translation cross-check found a substantive mismatch.";
    case "cross_check_ambiguity":
      return "The translation cross-check found an ambiguity requiring review.";
    case "cross_check_failed":
      return "The translation cross-check could not complete successfully.";
    case "open_audit_finding":
      return "A translation audit rule still has an unresolved finding.";
    case "open_conflict":
      return "A rule or terminology conflict still needs a decision.";
    default:
      return "This item needs review before it can leave active attention.";
  }
}

function decisionLabel(decisionType: string): string {
  switch (decisionType) {
    case "ocr_review_approve_go":
      return "Accepted / resolved";
    case "ocr_review_approve_with_warning":
      return "Accepted with warning";
    case "ocr_review_no_go_to_go":
      return "No-go resolved";
    case "ocr_attention_ignored":
      return "Ignored";
    case "ocr_attention_deleted":
      return "Deleted / hidden";
    case "ocr_attention_mark_unresolved":
      return "Marked unresolved";
    case "ocr_attention_superseded_by_rerun":
      return "Superseded by OCR retry";
    case "ocr_attention_historical":
      return "Historical";
    default:
      return decisionType;
  }
}

function decisionTone(decisionType: string): string {
  if (decisionType === "ocr_review_approve_with_warning") {
    return "bg-amber-100 text-amber-900";
  }
  if (decisionType === "ocr_attention_superseded_by_rerun") {
    return "bg-blue-100 text-blue-900";
  }
  if (decisionType === "ocr_attention_mark_unresolved") {
    return "bg-amber-100 text-amber-900";
  }
  if (decisionType === "ocr_attention_historical") {
    return "bg-zinc-100 text-zinc-800";
  }
  if (decisionType === "ocr_attention_ignored" || decisionType === "ocr_attention_deleted") {
    return "bg-slate-100 text-slate-800";
  }
  return "bg-emerald-100 text-emerald-900";
}

function decisionMatchesFilter(
  item: OcrReviewDecisionItem,
  filter: ResolvedDecisionFilter,
): boolean {
  if (filter === "all") return true;
  if (filter === "accepted") {
    return item.decision_type === "ocr_review_approve_go" ||
      item.decision_type === "ocr_review_no_go_to_go";
  }
  if (filter === "warning") {
    return item.decision_type === "ocr_review_approve_with_warning";
  }
  if (filter === "unresolved") {
    return item.decision_type === "ocr_attention_mark_unresolved";
  }
  if (filter === "superseded") {
    return item.decision_type === "ocr_attention_superseded_by_rerun";
  }
  if (filter === "historical") {
    return item.decision_type === "ocr_attention_historical";
  }
  return item.decision_type === "ocr_attention_ignored" ||
    item.decision_type === "ocr_attention_deleted";
}

function RetryDecisionDetails({ content }: { content: Record<string, unknown> }): JSX.Element | null {
  const details = content.details;
  if (typeof details !== "object" || details === null || Array.isArray(details)) {
    return null;
  }
  const retry = details as Record<string, unknown>;
  const crop = retry.crop;
  const cropText =
    typeof crop === "object" && crop !== null && !Array.isArray(crop)
      ? Object.entries(crop as Record<string, unknown>)
          .map(([key, value]) =>
            typeof value === "number" ? `${key} ${(value * 100).toFixed(1)}%` : null,
          )
          .filter(Boolean)
          .join(", ")
      : null;
  return (
    <p className="mt-1 rounded bg-muted/50 px-2 py-1 text-xs text-muted-foreground">
      Retry: {String(retry.engine ?? "unknown engine")} at {String(retry.dpi ?? "?")} DPI
      {retry.scope ? ` · ${String(retry.scope)}` : ""}
      {cropText ? ` · crop ${cropText}` : ""}
      {retry.candidate_uuid ? ` · candidate ${String(retry.candidate_uuid)}` : ""}
    </p>
  );
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
