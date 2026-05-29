"""Pydantic request/response models for the HTTP layer.

Naming convention: `<Resource><Action>Request` for inputs, `<Resource>Response`
for outputs. UUIDs surface as strings on the wire (Pydantic handles the
conversion both ways).

These are NOT the SQLAlchemy schemas — they're the API contract. Keep them
narrow: only fields the client actually sends/receives.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# --- Auth ---------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    display_name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_uuid: _uuid.UUID
    email: str
    display_name: str | None
    active: bool
    # M admission gate — surfaced on /auth/me so the frontend can
    # render UI conditionally (admin vs. regular user, approval state).
    approval_status: str = "approved"  # legacy callers may not supply
    # True iff the account's email is in the `ADMIN_EMAILS` env (the
    # bootstrap admin allowlist). Used by the frontend to show the
    # admin admissions link. Server-computed; the response model has
    # a default so legacy callers stay shape-compatible.
    is_admin: bool = False


# --- Projects -----------------------------------------------------------


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_uuid: _uuid.UUID
    account_uuid: _uuid.UUID
    name: str
    active: bool


class TrashedProjectResponse(ProjectResponse):
    deleted_at: str | None
    restore_until: str | None
    days_remaining: int
    restorable: bool


class ProjectTranslationAvailabilityResponse(BaseModel):
    project_uuid: _uuid.UUID
    total_segments: int
    translated_segments: int
    fresh_translated_segments: int
    stale_translated_segments: int
    untranslated_segments: int
    has_translation: bool
    has_full_translation: bool
    has_fresh_translation: bool
    has_full_fresh_translation: bool


# --- Uploads ------------------------------------------------------------


class UploadStartRequest(BaseModel):
    project_uuid: _uuid.UUID
    original_filename: str = Field(min_length=1, max_length=512)
    total_chunks: int = Field(gt=0)
    total_size_bytes: int = Field(gt=0)


class UploadStartResponse(BaseModel):
    job_uuid: _uuid.UUID
    state: str
    expected_next_chunk: int


class UploadStatusResponse(BaseModel):
    job_uuid: _uuid.UUID
    state: str
    received_chunks: int
    total_chunks: int
    expected_next_chunk: int | None


class DuplicateMatchResponse(BaseModel):
    """One existing Page in this project that matches the upload on
    filename or content. Surfaced in pre-upload precheck (filename
    match) and post-finalize response (sha256 match). Both kinds are
    warnings — the user can confirm "upload anyway" via the frontend
    modal. Canon §2.1 / §2.2 row 6."""

    page_uuid: _uuid.UUID
    page_index: int
    upload_job_uuid: _uuid.UUID | None
    original_filename: str | None
    source_sha256: str | None
    match_kind: str  # "filename" | "sha256"


class UploadFinalizeResponse(BaseModel):
    job_uuid: _uuid.UUID
    state: str
    page_count: int
    page_uuids: list[_uuid.UUID]
    source_sha256: str
    # K-5 row 6 SHA-256 dedupe: any prior pages in this project whose
    # content matches the just-uploaded file. Empty list = unique
    # content. Frontend shows the post-upload duplicate modal when
    # non-empty.
    duplicate_sha256_matches: list[DuplicateMatchResponse] = []


class UploadPrecheckResponse(BaseModel):
    """K-5 rows 6+7. Frontend calls `GET /projects/{u}/upload-precheck`
    when the user picks a file (before any bytes upload). The response
    drives two modal warnings:
      - `filename_matches` non-empty → "filename already exists" modal
      - `project_has_existing_pages` True → "1-book-at-a-time" modal
    Both warnings, NOT hard blocks. SHA-256 match is reported
    post-upload via `UploadFinalizeResponse.duplicate_sha256_matches`."""

    filename_matches: list[DuplicateMatchResponse]
    project_has_existing_pages: bool


# --- OCR ----------------------------------------------------------------


class OcrStartResponse(BaseModel):
    job_uuid: _uuid.UUID
    state: str


class OcrRunResponse(BaseModel):
    job_uuid: _uuid.UUID
    state: str
    text: str
    text_chars: int
    text_changed: bool
    rev_uuid: _uuid.UUID | None


# --- Pages / Blocks / Segments (M4 surface) -----------------------------


class PageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page_uuid: _uuid.UUID
    project_uuid: _uuid.UUID
    page_index: int
    ocr_status: str
    active: bool


class BlockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    block_uuid: _uuid.UUID
    page_uuid: _uuid.UUID
    block_type: str
    block_index: int
    active: bool


class SegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    satz_uuid: _uuid.UUID
    block_uuid: _uuid.UUID
    block_type: str | None = None
    satz_index: int
    lock_flag: str
    current_rev_uuid: _uuid.UUID | None
    text_content: str | None
    translation_style_key: str | None = None
    active: bool


class SegmentEditRequest(BaseModel):
    """Manual edit of segment text. Writes a Revision via the canonical
    revision service (change_source='manual'). Refused on locked segments
    by the INVARIANT-Guard."""

    after_text: str = Field(min_length=0, max_length=8192)


class SegmentTranslationEditRequest(BaseModel):
    """Manual edit of a segment's translation text.

    Writes a Revision via the canonical revision service with
    `change_source='re_translate'`, preserving the source-side revision
    history while advancing the target-side text state.
    """

    after_text: str = Field(min_length=0, max_length=8192)


class SegmentTranslationStyleRequest(BaseModel):
    """Update a segment's canonical translation paragraph style."""

    internal_style_key: str = Field(min_length=1, max_length=64)


# --- Lock ---------------------------------------------------------------


class LockSetRequest(BaseModel):
    level: str = Field(pattern="^(manual_local|manual_editorial)$")
    note: str | None = Field(default=None, max_length=1024)


class LockReleaseRequest(BaseModel):
    note: str | None = Field(default=None, max_length=1024)


class LockResponse(BaseModel):
    satz_uuid: _uuid.UUID
    lock_flag: str
    decision_event_uuid: _uuid.UUID


# --- Glossary -----------------------------------------------------------


class GlossaryLookupRequest(BaseModel):
    surface_form: str = Field(min_length=1, max_length=255)
    project_uuid: _uuid.UUID | None = None
    account_uuid: _uuid.UUID | None = None


class GlossaryLookupResponse(BaseModel):
    found: bool
    concept_id: _uuid.UUID | None = None


class GlossaryEntryCreateRequest(BaseModel):
    canonical_label: str = Field(min_length=1, max_length=255)
    language: str = Field(min_length=2, max_length=8)
    binding_level: str = Field(pattern="^(project|account)$")
    project_uuid: _uuid.UUID | None = None
    account_uuid: _uuid.UUID | None = None
    gloss: str | None = Field(default=None, max_length=4096)


class GlossaryEntryUpdateRequest(BaseModel):
    canonical_label: str | None = Field(default=None, min_length=1, max_length=255)
    gloss: str | None = Field(default=None, max_length=4096)


class GlossaryEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    concept_id: _uuid.UUID
    canonical_label: str
    language: str
    gloss: str | None
    binding_level: str
    project_uuid: _uuid.UUID | None
    account_uuid: _uuid.UUID | None
    active: bool


# --- Entities -----------------------------------------------------------


class EntityCreateRequest(BaseModel):
    category: str = Field(
        pattern="^(scholar_or_person|historical_place|unit_of_measurement|"
        "arabic_book|dynasty_or_epoch)$"
    )
    canonical_label: str = Field(min_length=1, max_length=255)
    language: str = Field(min_length=2, max_length=8)
    binding_level: str = Field(pattern="^(project|account)$")
    project_uuid: _uuid.UUID | None = None
    account_uuid: _uuid.UUID | None = None
    short_bio: str | None = Field(default=None, max_length=4096)


class EntityUpdateRequest(BaseModel):
    canonical_label: str | None = Field(default=None, min_length=1, max_length=255)
    short_bio: str | None = Field(default=None, max_length=4096)


class EntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_id: _uuid.UUID
    category: str
    canonical_label: str
    language: str
    short_bio: str | None
    binding_level: str
    project_uuid: _uuid.UUID | None
    account_uuid: _uuid.UUID | None
    active: bool


# --- Conflicts ----------------------------------------------------------


class ConflictResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conflict_uuid: _uuid.UUID
    satz_uuid: _uuid.UUID
    rule_source: str
    conflict_type: str
    state: str
    resolution_type: str | None
    decision_event_uuid: _uuid.UUID | None
    context: dict[str, Any]


class ConflictResolveRequest(BaseModel):
    """Body for any of the three resolve_with_* paths.

    `note` lands in the Decision-Event content. `confirmation_note` is only
    consumed by the lock_release path.
    """

    note: str | None = Field(default=None, max_length=1024)
    confirmation_note: str | None = Field(default=None, max_length=1024)


# --- OCR Review ---------------------------------------------------------


class OcrFindingApply(BaseModel):
    error_code: str = Field(pattern="^F-(0[1-9]|06-QR)$")
    block_uuid: _uuid.UUID | None = None
    details: dict[str, Any] | None = None


class OcrApplyFindingsRequest(BaseModel):
    findings: list[OcrFindingApply]


class OcrApprovePageRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2048)


class OcrPageStatusResponse(BaseModel):
    page_uuid: _uuid.UUID
    ocr_status: str
    error_codes_open: list[str]


class OcrResolveNoGoRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2048)


# --- Release Gate -------------------------------------------------------


class ReleaseGateResponse(BaseModel):
    state: str
    blocking_reasons: list[str]
    warnings: list[str]
    requires_confirmation: bool


class ReleaseGateConfirmRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2048)


class TranslationStartRequest(BaseModel):
    segment_uuids: list[_uuid.UUID] = Field(min_length=1)


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_uuid: _uuid.UUID
    job_type: str
    state: str
    project_uuid: _uuid.UUID | None
    payload: dict[str, Any] | None
    result: dict[str, Any] | None
    error: dict[str, Any] | None


# --- Rule binding -------------------------------------------------------


class RuleBindingApplyRequest(BaseModel):
    """Caller supplies the surface forms to look up. The service resolves
    each via glossary.lookup, then writes a RULE_BINDING-PO or detects a
    conflict if the segment is locked."""

    candidate_surface_forms: list[str] = Field(min_length=1)
    application_context: dict[str, Any] | None = None


class RuleBindingResponse(BaseModel):
    outcome: str  # "applied" | "conflict_detected"
    matched_concept_ids: list[_uuid.UUID]
    conflict_uuid: _uuid.UUID | None = None
    rule_binding_po_uuid: _uuid.UUID | None = None


# --- Promotion (Stufen 1-2) --------------------------------------------


class PromotionObservationCreateRequest(BaseModel):
    revision_uuid: _uuid.UUID
    prior_translation: str = Field(max_length=8192)
    user_correction: str = Field(max_length=8192)
    source_text: str | None = Field(default=None, max_length=8192)
    source_class: str = Field(
        pattern="^(bestaetigte_referenzsaetze|manuelle_nutzerregeln|"
        "akzeptierte_ki_vorschlaege|korrigierte_ki_vorschlaege|"
        "ignorierte_ki_vorschlaege)$"
    )
    terminology_bindings: dict[str, str] | None = None


class PromotionAggregateRequest(BaseModel):
    threshold: int = Field(default=3, ge=1, le=1000)


class MusterkandidatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    musterkandidat_uuid: _uuid.UUID
    project_uuid: _uuid.UUID
    pattern_key: str
    observation_count: int
    sample_corrections: list[str]
    state: str


# --- OCR Export ---------------------------------------------------------


class OcrExportPflichtfragenInput(BaseModel):
    page_range: list[int] = Field(min_length=1)
    block_types_enabled: list[str] = Field(min_length=1)
    markings_enabled: bool
    mode: str = Field(pattern="^(arbeitsstand|endgueltig)$")


class OcrExportGateResponse(BaseModel):
    state: str
    blocking_reasons: list[str]
    warnings: list[str]


class OcrExportConfirmRequest(BaseModel):
    pflichtfragen: OcrExportPflichtfragenInput
    export_attempt_id: str = Field(min_length=1, max_length=64)


class OcrExportRunResponse(BaseModel):
    job_uuid: _uuid.UUID
    job_state: str
    artefact_uuid: _uuid.UUID
    sha256: str
    size_bytes: int
    ocr_export_event_po_uuid: _uuid.UUID
    n_segments_exported: int
    n_pages_exported: int


# --- History ------------------------------------------------------------


class HistoryResponse(BaseModel):
    """Full history payload — service returns dataclasses with several
    list[ORM] fields. We re-serialize via model_dump on the dict-of-lists
    the service provides; clients should not depend on shape stability of
    the embedded ORM rows beyond their PK + a few columns."""

    revisions: list[dict[str, Any]]
    decision_events: list[dict[str, Any]]
    log_entries: list[dict[str, Any]]
    provenance_objects: list[dict[str, Any]]
    conflict_instances: list[dict[str, Any]] = []
    ocr_error_instances: list[dict[str, Any]] = []
    konsistenz_befunde: list[dict[str, Any]] = []


# --- Errors -------------------------------------------------------------


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
    context: dict[str, Any] | None = None
