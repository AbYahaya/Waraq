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
  ReleaseGate,
  Segment,
} from "@/lib/types";

export const qk = {
  projects: () => ["projects"] as const,
  project: (uuid: string) => ["projects", uuid] as const,
  projectPages: (uuid: string) => ["projects", uuid, "pages"] as const,
  page: (uuid: string) => ["pages", uuid] as const,
  pageSegments: (uuid: string) => ["pages", uuid, "segments"] as const,
  segment: (uuid: string) => ["segments", uuid] as const,
  segmentConflicts: (uuid: string) => ["segments", uuid, "conflicts"] as const,
  pageConflicts: (uuid: string) => ["pages", uuid, "conflicts"] as const,
  projectConflicts: (uuid: string) => ["projects", uuid, "conflicts"] as const,
  releaseGate: (uuid: string) => ["projects", uuid, "release-gate"] as const,
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
};

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
}
