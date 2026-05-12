"""Canonical enums used at the schema layer.

These are not Python-only conveniences — every value here is named in the canon
and changes must go through the CR cycle (CLAUDE.md §2.6). Column-level CHECK
constraints in migrations enforce the same value sets in Postgres.
"""

from __future__ import annotations

from enum import StrEnum


class ChangeSource(StrEnum):
    """Per CAB §5.2 — Revision.change_source canonical values."""

    MANUAL = "manual"
    OCR = "ocr"
    RE_TRANSLATE = "re_translate"
    STYLE_PROFILE = "style_profile"


class ApprovalStatus(StrEnum):
    """Phase 5 sub-batch M — Account.approval_status.

    Simplified admission gate (canon §2.3 row 8 partial — tier system
    + subscription deferred). State machine:
      pending  → approved | rejected     (by admin action)
      rejected → approved                (admin overturns rejection)
      approved → (terminal for v1.0; tier system will add transitions)

    New accounts default to `pending`. Accounts whose email is in
    `ADMIN_EMAILS` env are auto-approved at registration (bootstrap
    rule — there has to be at least one approver). Login refuses
    `pending` and `rejected` accounts with explicit error classes.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class DecisionSource(StrEnum):
    """Per Dokument 1 §4.10 / CLAUDE.md §5.9 — ten unveränderlich values.

    `export_confirmation` is OCR-export-specific. For translation EXPORT_EVENT
    the relevant decision-event sources are different (Sprint 5 T-9.2.1
    allowlist).
    """

    OCR_REVIEW = "ocr_review"
    LOCK_MANAGEMENT = "lock_management"
    CONFLICT_RESOLUTION = "conflict_resolution"
    TRANSLATION_PIPELINE = "translation_pipeline"
    AUDIT_RESOLUTION = "audit_resolution"
    CONSISTENCY_RESOLUTION = "consistency_resolution"
    GLOSSARY_MANAGEMENT = "glossary_management"
    PREFLIGHT_CONFIRMATION = "preflight_confirmation"
    EXPORT_CONFIRMATION = "export_confirmation"
    STYLE_MANAGEMENT = "style_management"


class POType(StrEnum):
    """Per CAB §5.3 / OCR Endfassung v1.3 §1.4 / CLAUDE.md §5.3.

    Eight canonical PO types after Sprint-OCR adds OCR_EXPORT_EVENT
    (CR-1.1).

    `MANUAL_` preserves the canonical trailing underscore from §2.4
    (`MANUAL_-PO`); do not silently drop it.

    Scope per type (informational; enforced by the service layer, not
    the schema):
    - SCAN              — page-scoped
    - OCR               — segment-scoped
    - MANUAL_           — segment-scoped
    - RULE_BINDING      — segment-scoped
    - TRANSLATION       — segment-scoped
    - LINEAGE_EVENT     — segment-scoped (system-authored)
    - EXPORT_EVENT      — artefact-scoped, work-wide. Canonically addressed
                          via `scope_type='project'` + `scope_uuid=project_uuid`,
                          with artefact identity (filename, format, sha256)
                          in `payload`. ScopeType is canonically fixed at five
                          values (§5.8); extending to add `artefact` would
                          be silent canon amendment.
    - OCR_EXPORT_EVENT  — analogue of EXPORT_EVENT for the OCR-source-text
                          export (Sprint-OCR §1.4). Must NEVER be silently
                          mixed or merged with EXPORT_EVENT — different
                          semantics. Also addressed via `scope_type='project'`
                          + project_uuid + payload (same convention as
                          EXPORT_EVENT for the v1.0 ScopeType taxonomy).
    """

    SCAN = "scan"
    OCR = "ocr"
    MANUAL_ = "manual_"
    RULE_BINDING = "rule_binding"
    TRANSLATION = "translation"
    LINEAGE_EVENT = "lineage_event"
    EXPORT_EVENT = "export_event"
    OCR_EXPORT_EVENT = "ocr_export_event"


class JobState(StrEnum):
    """Per T-2.1.1 — canonical Job state machine values.

    The transition graph (enforced by `waraq.jobs.service`):

        pending  → running, failed
        running  → paused, completed, failed
        paused   → running, failed
        completed → (terminal)
        failed   → (terminal)

    The DB CHECK constraint (added in migration 0004) enforces the value set;
    the service enforces the transition graph. New states or transitions
    require a CR.
    """

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class OcrStatus(StrEnum):
    """Per Sprint 1 §2 / T-4.3.1 — page-level OCR review status.

    State machine:
        ausstehend → in_review → go | go_with_warning | no_go
    Re-entry into in_review is permitted from any non-terminal state. The
    `no_go → go` transition is **not automatic** — it requires an explicit
    user-resolution Decision Event with `scope_type=page`.
    """

    AUSSTEHEND = "ausstehend"
    IN_REVIEW = "in_review"
    GO = "go"
    GO_WITH_WARNING = "go_with_warning"
    NO_GO = "no_go"


class OcrErrorState(StrEnum):
    """Per T-4.3.1 — `ocr_error_instance` lifecycle.

    `aufgeloest` is the canonical-ASCII transliteration of "aufgelöst" used as
    the wire/DB value. Display-side German renders the umlaut.
    """

    OFFEN = "offen"
    AUFGELOEST = "aufgeloest"


class OcrSeverity(StrEnum):
    """Per Sprint 1 §2 — severity classes used by status aggregation.

    The mapping from F-XX → severity is **configurable**, never hard-coded
    (R-S1-04). See `waraq.ocr.review.SeverityWeights`.
    """

    KRITISCH = "kritisch"
    HOCH = "hoch"
    MITTEL = "mittel"


class BlockClass(StrEnum):
    """Per Dokument 1 §3.4 — canonical OCR Stage-1 / Stage-2 block class.

    Six values. The Stage-1 layout detector classifies each detected
    block; Stage-2 OCR routes per class (different reading lines for
    main_text vs Qurʾān vs marginalia). Adding a seventh value here is a
    canon-amendment-shaped change.

    Legacy synonyms in pre-Phase-4 data: `UE` (Überschrift, Heading 1)
    and `HD` (Heading 2) — both historically modelled as `block_type`
    string values for the TOC + DOCX-export paths. Migration 0024
    extends the CHECK constraint to allow these legacy values alongside
    the canonical six until a follow-up cleanup migrates them to
    `(HEADING, heading_level=1|2)`. Both code paths read; new writes
    use the canonical values.
    """

    MAIN_TEXT = "main_text"
    FOOTNOTE = "footnote"
    HEADING = "heading"
    QURAN = "quran"
    HADITH = "hadith"
    MARGINALIA = "marginalia"


class ReadingDirection(StrEnum):
    """Per Dokument 1 §3.4 — text reading direction per Block.

    Arabic is RTL (default for this project's documents); LTR captures
    the rare interspersed Latin-script block. UNKNOWN is the harness
    fallback when a detector cannot decide — callers treat UNKNOWN like
    RTL for layout but log it so detector calibration can target it.
    """

    RTL = "rtl"
    LTR = "ltr"
    UNKNOWN = "unknown"


class ScopeType(StrEnum):
    """Per CAB §B.1 + Dokument 2 §3.2 Eintrag 2D extension.

    `account` and `project` are extensions over the original CAB enum; the
    extension is decided, ALT→NEU verankert in Schluss-Audit (Paket 7).
    Implementation supports all five from Sprint 0.
    """

    SEGMENT = "segment"
    PAGE = "page"
    BLOCK = "block"
    ACCOUNT = "account"
    PROJECT = "project"
