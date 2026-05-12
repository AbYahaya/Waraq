"""Phase 4 sub-batch B' — replace shamela_sections btree skeleton index
with a `pg_trgm` GIN index.

Revision ID: 0025
Revises: 0024
Create Date: 2026-05-10

The Phase 2E ingest of real OpenITI texts (Bukhari first) hit:

    index row size 3728 exceeds btree version 4 maximum 2704 for index
    "ix_shamela_section_skeleton"

Postgres's own hint: "Values larger than 1/3 of a buffer page cannot
be indexed. Consider a function index of an MD5 hash of the value, or
use full text indexing."

The skeleton is matched via `LIKE '%skeleton%'` (substring) per
`waraq.shamela.lookup.find_by_skeleton`. Btree on a long-string
column is useless for that query pattern AND fails on long values.
The right tool is `pg_trgm`'s GIN trigram index — built for
substring matching at scale.

Steps:
  1. Drop the existing btree `ix_shamela_section_skeleton`.
  2. Create the `pg_trgm` extension if missing (idempotent).
  3. Create a GIN index on `text_skeleton` using `gin_trgm_ops`.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_shamela_section_skeleton")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX ix_shamela_section_skeleton_trgm "
        "ON shamela_sections USING gin (text_skeleton gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_shamela_section_skeleton_trgm")
    op.execute("CREATE INDEX ix_shamela_section_skeleton ON shamela_sections (text_skeleton)")
    # Note: pg_trgm extension is left installed — it's a deployment-shared
    # resource and removing it could break other indexes added later.
