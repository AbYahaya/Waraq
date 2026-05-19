/**
 * Shared TypeScript types mirroring the backend Pydantic shapes in
 * `waraq/api/schemas.py`. Kept narrow — only what the UI consumes.
 */

export interface Account {
  account_uuid: string;
  email: string;
  display_name: string | null;
  active: boolean;
  // Phase 5 sub-batch M — admission gate.
  approval_status: "pending" | "approved" | "rejected";
  is_admin: boolean;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}

/**
 * Phase 5 sub-batch M — response shape of /auth/register.
 * Admins get a token immediately; non-admins land in `pending` with
 * no token until an admin approves them via /admin/admissions/*.
 */
export interface RegisterResponse {
  approval_status: "pending" | "approved" | "rejected";
  access_token: string | null;
  token_type: string;
}

export interface Project {
  project_uuid: string;
  account_uuid: string;
  name: string;
  active: boolean;
}

export interface ProjectTranslationAvailability {
  project_uuid: string;
  total_segments: number;
  translated_segments: number;
  fresh_translated_segments: number;
  stale_translated_segments: number;
  untranslated_segments: number;
  has_translation: boolean;
  has_full_translation: boolean;
  has_fresh_translation: boolean;
  has_full_fresh_translation: boolean;
}

export interface Page {
  page_uuid: string;
  project_uuid: string;
  page_index: number;
  ocr_status: "ausstehend" | "in_review" | "go" | "go_with_warning" | "no_go";
  active: boolean;
}

export interface Segment {
  satz_uuid: string;
  block_uuid: string;
  satz_index: number;
  lock_flag: "none" | "manual_local" | "manual_editorial";
  current_rev_uuid: string | null;
  text_content: string | null;
  active: boolean;
}

export interface Conflict {
  conflict_uuid: string;
  satz_uuid: string;
  rule_source: string;
  conflict_type: string;
  state: "offen" | "aufgeloest";
  resolution_type: string | null;
  decision_event_uuid: string | null;
  context: Record<string, unknown>;
}

export interface ReleaseGate {
  state:
    | "uebersetzungsreif"
    | "uebersetzbar_mit_warnung"
    | "blockiert"
    | "nicht_erreichbar"
    | "freigabeschranken_pruefung";
  blocking_reasons: string[];
  warnings: string[];
  requires_confirmation: boolean;
}

export interface Job {
  job_uuid: string;
  job_type: string;
  state: "pending" | "running" | "paused" | "completed" | "failed";
  project_uuid: string | null;
  payload: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  error: Record<string, unknown> | null;
}

export interface OcrPageStatus {
  page_uuid: string;
  ocr_status: Page["ocr_status"];
  error_codes_open: string[];
}

export interface LockResponse {
  satz_uuid: string;
  lock_flag: Segment["lock_flag"];
  decision_event_uuid: string;
}
