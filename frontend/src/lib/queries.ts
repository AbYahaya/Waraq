/**
 * Shared TanStack Query keys and reusable query factories.
 *
 * Centralizing keys here keeps invalidation predictable: a mutation can
 * invalidate `qk.projectPages(uuid)` without re-stating the array shape.
 */

import { api } from "@/lib/api";
import type {
  Conflict,
  Page,
  Project,
  ProjectStyleProfile,
  ReleaseGate,
  Segment,
} from "@/lib/types";

export const qk = {
  projects: () => ["projects"] as const,
  project: (uuid: string) => ["projects", uuid] as const,
  projectPages: (uuid: string) => ["projects", uuid, "pages"] as const,
  projectStyleProfile: (uuid: string) => ["projects", uuid, "style-profile"] as const,
  page: (uuid: string) => ["pages", uuid] as const,
  pageSegments: (uuid: string) => ["pages", uuid, "segments"] as const,
  segment: (uuid: string) => ["segments", uuid] as const,
  segmentConflicts: (uuid: string) => ["segments", uuid, "conflicts"] as const,
  pageConflicts: (uuid: string) => ["pages", uuid, "conflicts"] as const,
  projectConflicts: (uuid: string) => ["projects", uuid, "conflicts"] as const,
  releaseGate: (uuid: string) => ["projects", uuid, "release-gate"] as const,
  pageDifficulty: (uuid: string) => ["pages", uuid, "difficulty"] as const,
  projectDifficulty: (uuid: string) => ["projects", uuid, "difficulty"] as const,
  guidedReviewQueue: (uuid: string) => ["projects", uuid, "guided-review", "queue"] as const,
  projectToc: (uuid: string) => ["projects", uuid, "toc"] as const,
};

export const queries = {
  projects: () => ({
    queryKey: qk.projects(),
    queryFn: () => api.get<Project[]>("/projects"),
  }),
  project: (uuid: string) => ({
    queryKey: qk.project(uuid),
    queryFn: () => api.get<Project>(`/projects/${uuid}`),
  }),
  projectPages: (uuid: string) => ({
    queryKey: qk.projectPages(uuid),
    queryFn: () => api.get<Page[]>(`/projects/${uuid}/pages`),
  }),
  projectStyleProfile: (uuid: string) => ({
    queryKey: qk.projectStyleProfile(uuid),
    queryFn: () => api.get<ProjectStyleProfile>(`/projects/${uuid}/style-profile`),
  }),
  page: (uuid: string) => ({
    queryKey: qk.page(uuid),
    queryFn: () => api.get<Page>(`/pages/${uuid}`),
  }),
  pageSegments: (uuid: string) => ({
    queryKey: qk.pageSegments(uuid),
    queryFn: () => api.get<Segment[]>(`/pages/${uuid}/segments`),
  }),
  segmentConflicts: (uuid: string) => ({
    queryKey: qk.segmentConflicts(uuid),
    queryFn: () => api.get<Conflict[]>(`/segments/${uuid}/conflicts`),
  }),
  segmentHistory: (uuid: string) => ({
    queryKey: ["segments", uuid, "history"] as const,
    queryFn: () => api.get<SegmentHistoryDto>(`/segments/${uuid}/history`),
  }),
  releaseGate: (uuid: string) => ({
    queryKey: qk.releaseGate(uuid),
    queryFn: () => api.get<ReleaseGate>(`/projects/${uuid}/release-gate`),
  }),
  pageDifficulty: (uuid: string) => ({
    queryKey: qk.pageDifficulty(uuid),
    queryFn: () => api.get<DifficultyReportDto>(`/pages/${uuid}/difficulty`),
  }),
  projectDifficulty: (uuid: string) => ({
    queryKey: qk.projectDifficulty(uuid),
    queryFn: () => api.get<DifficultyReportDto>(`/projects/${uuid}/difficulty`),
  }),
  guidedReviewQueue: (uuid: string) => ({
    queryKey: qk.guidedReviewQueue(uuid),
    queryFn: () => api.get<GuidedReviewQueueDto>(`/projects/${uuid}/guided-review/queue`),
  }),
  projectToc: (uuid: string) => ({
    queryKey: qk.projectToc(uuid),
    queryFn: () => api.get<TocResponseDto>(`/projects/${uuid}/toc`),
  }),
};

export interface DifficultyBreakdownDto {
  audit_kritisch: number;
  audit_hoch: number;
  audit_mittel: number;
  konsistenz_kritisch: number;
  konsistenz_other: number;
  hadith_h_2: number;
  hadith_h_1: number;
  ocr_error_kritisch: number;
  ocr_error_hoch: number;
  ocr_error_mittel: number;
  locked_segment_manual_local: number;
  locked_segment_manual_editorial: number;
}

export interface DifficultyReportDto {
  scope: "page" | "project";
  scope_uuid: string;
  score: number;
  segment_count: number;
  breakdown: DifficultyBreakdownDto;
}

export interface GuidedReviewItemDto {
  kind: "audit_befund" | "konsistenz_befund" | "ocr_error" | "hadith";
  finding_uuid: string;
  tier: "p_03_blocking" | "p_04_blocking" | "warning";
  severity: string;
  detected_at: string;
  satz_uuid: string | null;
  page_uuid: string | null;
}

export interface GuidedReviewQueueDto {
  items: GuidedReviewItemDto[];
  total: number;
  by_tier: Record<string, number>;
}

export interface TocEntryDto {
  page_index: number;
  page_uuid: string;
  level: number;
  ar_text: string;
  de_text: string;
  satz_uuid: string | null;
  block_uuid: string | null;
}

export interface TocResponseDto {
  entries: TocEntryDto[];
  fallback_kind: "none" | "page_by_page";
  detected_heading_count: number;
  page_count: number;
  workflow_state:
    | "no_pages"
    | "no_toc_detected"
    | "toc_detected"
    | "toc_requires_attention"
    | "final_review_confirmed";
  requires_attention: boolean;
  attention_reasons: string[];
  confirmation_state: "confirmed" | "unconfirmed";
  confirmed_at: string | null;
  confirmed_by_decision_event_uuid: string | null;
  export_settings_summary: Record<string, string | number | boolean>;
}

/**
 * Loose-typed segment history shape matching the backend's
 * `_segment_history_to_dict` output. Only the fields the UI consumes
 * are typed; the rest stays as string-keyed records to avoid coupling
 * the UI to the full ORM column set.
 */
export interface SegmentHistoryDto {
  satz_uuid: string;
  revisions: Array<{
    rev_uuid: string;
    satz_uuid: string;
    before_text: string | null;
    after_text: string;
    change_source: string;
    created_at: string;
    [key: string]: unknown;
  }>;
  decision_events: Array<Record<string, unknown>>;
  provenance_objects: Array<Record<string, unknown>>;
  log_entries: Array<Record<string, unknown>>;
  conflict_instances: Array<Record<string, unknown>>;
  quran_passage?: Record<string, unknown> | null;
}
