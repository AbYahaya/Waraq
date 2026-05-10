"""Block active-uniqueness defence-in-depth.

Revision ID: 0023
Revises: 0022
Create Date: 2026-05-10

Closes the OCR auto-run duplicate-Block race condition diagnosed
2026-05-10:

  Two OCR runs on the same Page in separate transactions could each
  flush a new `main_text` Block before either committed (the second
  session can't see the first's uncommitted insert), producing two
  active Block rows for `(page_uuid, block_index=0)`.

The application-level fix (status gate + `SELECT FOR UPDATE` row lock
in `_ensure_block_and_segment`) closes the race in normal operation;
this migration adds the DB-level guarantee that even a regressed
service can't write the duplicate.

Partial UNIQUE index:
  - block_active_page_index_uq:    (page_uuid, block_index) WHERE active

The `WHERE active` predicate is essential: per H-5 inactivated rows
stay in the table forever, so a non-partial UNIQUE would forbid
inactivating a duplicate then re-creating a successor with the same
index — exactly the recovery path the application uses.

NOT applied to Segment: the §4.2.2 lineage flow (`record_split`,
`record_merge`) legitimately produces transient
`(block_uuid, satz_index)` collisions while a source is being
inactivated and daughters/target are being added at indexes that
overlap. The constraint would break those operations. Race-protection
on Segment is provided by the higher-level callers being
single-threaded user actions, not parallel automated pipelines.

Pre-index data cleanup: any existing active Block duplicate clusters
are collapsed by keeping the EARLIEST `created_at` row active and
inactivating the rest. This is the canonical "deactivate, never
delete" path (H-5). Segments under inactivated duplicate Blocks are
also inactivated so the active sub-graph stays consistent.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Inactivate active-duplicate Blocks. Keep the earliest by
    #    created_at per (page_uuid, block_index); inactivate the rest.
    op.execute(
        """
        WITH ranked AS (
            SELECT
                block_uuid,
                ROW_NUMBER() OVER (
                    PARTITION BY page_uuid, block_index
                    ORDER BY created_at ASC, block_uuid ASC
                ) AS rn
            FROM blocks
            WHERE active = TRUE
        )
        UPDATE blocks
        SET active = FALSE
        WHERE block_uuid IN (SELECT block_uuid FROM ranked WHERE rn > 1)
        """
    )

    # 2. Cascade: inactivate every Segment under a now-inactivated Block
    #    so the active set on the Block side and the active set on the
    #    Segment side stay consistent. A Segment hung on an inactive
    #    Block is unreachable through the normal `Block.active=true`
    #    join anyway.
    op.execute(
        """
        UPDATE segments
        SET active = FALSE
        WHERE block_uuid IN (SELECT block_uuid FROM blocks WHERE active = FALSE)
          AND active = TRUE
        """
    )

    # 3. Add the partial UNIQUE index on Block.
    op.execute(
        """
        CREATE UNIQUE INDEX block_active_page_index_uq
        ON blocks (page_uuid, block_index)
        WHERE active = TRUE
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS block_active_page_index_uq")
    # The data cleanup is intentionally NOT reversed — restoring
    # silently-duplicated rows would re-introduce the very state the
    # upgrade was written to escape.
