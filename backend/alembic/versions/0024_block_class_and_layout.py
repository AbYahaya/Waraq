"""Phase 4 sub-batch B — block_type CHECK + Stage-1 layout columns.

Revision ID: 0024
Revises: 0023
Create Date: 2026-05-10

Per Dokument 1 §3.4 Stage-1 / Stage-2 block classification, plus the
schema-side comment on `Block.block_type` ("Intentionally an
unconstrained string here so that the constraint lands in the same
migration that introduces the classifier"). This migration is that
moment.

Three pieces:

  1. CHECK constraint on `blocks.block_type` allowing the canonical
     six `BlockClass` values plus the legacy `UE` / `HD` heading
     synonyms. UE / HD are pre-Phase-4 production data (TOC + DOCX
     export read them directly); a follow-up cleanup migrates them to
     `(heading, heading_level=1|2)`.

  2. New `reading_direction` column on `blocks` per the §3.4 Stage-1
     reading-direction map. Default 'rtl' (Arabic primary).

  3. New `text_density` (real) + `baseline_y` (integer) columns on
     `blocks` for the §3.4 Stage-1 text-density + baseline-detection
     signals. Both nullable; populated by real layout detectors when
     configured. v1.0 default detector leaves them NULL.

The Real LayoutParser / DocTR model invocation itself is a deployment
adapter (same pattern as Real-ESRGAN in sub-batch A) — this migration
ships the persistence shape; the implementation is pluggable.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Two parallel canonical taxonomies, both wire-stable:
#
#   Dokument 1 §3.4 — six full-name classes (the BlockClass enum):
#     main_text, footnote, heading, quran, hadith, marginalia
#
#   OCR-Export Endfassung v1.3 — six two-letter codes used by the
#   DOCX builder's style map and the `block_types_enabled` /
#   `block_types_present` artefact protocol:
#     MT (main_text), UE (heading 1), HD (heading 2), FN (footnote),
#     QR (quran), RN (marginalia/Randnote)
#
# Both sets are canonical and currently emitted by different code
# paths (page_runner writes "main_text"; OCR-export tests + docx
# builder emit the 2-letter codes). Allowing both preserves
# backward-compat without losing the §3.4 enum's invariant.
# A future cleanup can collapse the two surfaces; today the CHECK
# constraint defines the closed set.
_ALLOWED_BLOCK_TYPES: tuple[str, ...] = (
    # §3.4 canonical six.
    "main_text",
    "footnote",
    "heading",
    "quran",
    "hadith",
    "marginalia",
    # OCR-Export Endfassung v1.3 two-letter codes.
    "MT",
    "UE",
    "HD",
    "FN",
    "QR",
    "RN",
)


def upgrade() -> None:
    # 1. CHECK constraint on block_type. Existing rows are validated
    #    by the constraint creation; if any row holds a value outside
    #    the allowed set the migration fails fast (the deployer must
    #    reconcile before re-running).
    allowed_quoted = ", ".join(f"'{v}'" for v in _ALLOWED_BLOCK_TYPES)
    op.execute(
        f"ALTER TABLE blocks ADD CONSTRAINT ck_blocks_block_type "
        f"CHECK (block_type IN ({allowed_quoted}))"
    )

    # 2. reading_direction column. server_default 'rtl' so existing
    #    rows backfill cleanly; new rows default to RTL via the same
    #    server-default.
    op.add_column(
        "blocks",
        sa.Column(
            "reading_direction",
            sa.String(length=16),
            nullable=False,
            server_default="rtl",
        ),
    )
    op.execute(
        "ALTER TABLE blocks ADD CONSTRAINT ck_blocks_reading_direction "
        "CHECK (reading_direction IN ('rtl', 'ltr', 'unknown'))"
    )

    # 3. Stage-1 signals — both nullable.
    op.add_column("blocks", sa.Column("text_density", sa.Float(), nullable=True))
    op.add_column("blocks", sa.Column("baseline_y", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("blocks", "baseline_y")
    op.drop_column("blocks", "text_density")
    op.execute("ALTER TABLE blocks DROP CONSTRAINT IF EXISTS ck_blocks_reading_direction")
    op.drop_column("blocks", "reading_direction")
    op.execute("ALTER TABLE blocks DROP CONSTRAINT IF EXISTS ck_blocks_block_type")
