"""T-1.4.1 — `create_revision` service.

Append a Revision row and atomically update `segments.current_rev_uuid` and
`segments.text_content`. The service flushes; the caller controls the
transaction boundary.

Honors:
- H-1 / H-2 via INVARIANT-Guard: refuses automatic writes to segments with
  `lock_flag = manual_local | manual_editorial`.
- H-4 by construction: this service exists only for text-change operations;
  callers in check/audit code paths must not invoke it (and have their own
  H-4 Guard call to enforce that).
- H-5: we never delete or recycle UUIDs. The Revision is a new row; the
  Segment's UUID is unchanged; only `current_rev_uuid` and `text_content`
  move forward.

Atomicity expectation: the caller is in an active transaction. The Revision
insert and the two Segment updates land in the same transaction and either
all commit or all roll back.
"""

from __future__ import annotations

import uuid as _uuid

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity.service import new_uuid
from waraq.invariant.enums import OperationMode
from waraq.invariant.guard import assert_no_auto_write_to_locked_segment
from waraq.schemas.enums import ChangeSource
from waraq.schemas.events import Revision
from waraq.schemas.projects import Segment


async def create_revision(
    *,
    session: AsyncSession,
    segment: Segment,
    after_text: str,
    change_source: ChangeSource,
    operation_mode: OperationMode,
    author_uuid: _uuid.UUID | None = None,
) -> Revision:
    """Stage a Revision and bump the Segment's current_rev_uuid + text_content.

    Args:
        session: Active async session. Caller manages commit/rollback.
        segment: The Segment receiving the new text. Must already be persisted
            (have a satz_uuid) — this service does not create segments.
        after_text: The new text content. Required; revisions never write null
            after_text.
        change_source: Provenance of the change (manual / ocr / re_translate /
            style_profile). Recorded on the Revision row.
        operation_mode: AUTOMATIC for system-driven writes (OCR, translation,
            style_profile); MANUAL_WITH_CONFIRMATION for human-confirmed writes
            via the editor. The Guard refuses AUTOMATIC against locked Segments.
        author_uuid: Identity of the actor producing the change. None for
            system-authored revisions (e.g., automatic OCR).

    Returns:
        The Revision instance, with rev_uuid populated and `before_text` set
        to the segment's prior `text_content` (None for the first revision).
    """
    # H-1 / H-2 — refuse automatic write to locked segment.
    assert_no_auto_write_to_locked_segment(
        operation_mode=operation_mode,
        lock_flag=segment.lock_flag,
        segment_id=segment.satz_uuid,
    )

    revision = Revision(
        rev_uuid=new_uuid(),
        satz_uuid=segment.satz_uuid,
        before_text=segment.text_content,
        after_text=after_text,
        change_source=change_source,
        author_uuid=author_uuid,
    )
    session.add(revision)

    segment.current_rev_uuid = revision.rev_uuid
    segment.text_content = after_text

    await session.flush()
    return revision
