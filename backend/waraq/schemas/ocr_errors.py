"""T-4.1.3 + T-4.3.1 — `ocr_error_instance` schema.

Each row records one detected OCR failure (F-01..F-09) attached to a Page,
optionally narrowed by a Block. `state` cycles `offen → aufgeloest`.

Severity is **not** stored on the row. Per Sprint 1 §2 / R-S1-04, the
severity for each F-XX is read from a configurable mapping at aggregation
time (see `waraq.ocr.review.SeverityWeights`). Storing severity on the row
would calcify the mapping and convert post-Gold-Corpus calibration into a
data migration.

The row is **page-rooted**: page_uuid is NOT NULL; block_uuid is nullable
(populated when the failure can be narrowed beyond the page). No `satz_uuid`
column — that's intentional. The OCR pipeline operates on Pages; segments
emerge from a successful pass. Tying error rows to satz_uuid would require
backfilling on every re-segmentation. The Abkürzung 2 schema-level guard
also stays satisfied (segments + revisions only).
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from waraq.db.base import Base, TimestampMixin


class OcrErrorInstance(Base, TimestampMixin):
    __tablename__ = "ocr_error_instances"

    ocr_error_instance_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True
    )
    page_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pages.page_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    block_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("blocks.block_uuid", ondelete="RESTRICT"),
        nullable=True,
    )
    # F-XX wire form ("F-01" .. "F-09"). The CHECK constraint lives in the
    # migration; we keep the column type as plain VARCHAR for fast indexing
    # and to avoid binding the column to a hard-coded enum.
    error_code: Mapped[str] = mapped_column(String(8), nullable=False)
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="offen", index=True
    )
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
