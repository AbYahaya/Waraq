"""T-7.1.2 — TRANSLATION-PO + revision-UUID-on-change persistence hook.

This module supplies the `on_segment_translated` hook for T-7.1.1's
`run_translation_job`. With the hook installed, every translated Segment
gets:

1. A new **Revision** via T-1.4.1 `create_revision` — but **only when
   the translator output differs** from the Segment's current
   `text_content`. Identical output produces no Revision (Sprint 2 §2 /
   TRANSLATION-PO-Identische-Ausgabe-Keine-Revision-Test). H-4 by
   construction: a check pass that emits no translation never reaches
   this hook, so no Revision-UUID is issued for check operations
   (Sprint 2 §2 / TRANSLATION-PO-Pruefung-Keine-Revision-Test — the
   "no hook installed" form is the dry-run mode).

2. A **TRANSLATION-PO** via PROVENANCE-Kern `create_po` (Abkürzung 7
   protected: PROVENANCE-Kern is the sole writer). The PO is written on
   every translated Segment regardless of text-change — the PO records
   that translation happened; the Revision records the text change (and
   only when there was one). PO payload carries engine identifier,
   input text, output text, the terminology bindings consumed, the
   style anchors consumed, and `rev_uuid` (or null when text was
   identical).

R-S2-05 protection: revision-UUID is gated on actual text change, NOT on
"any translation pass produces a revision". R-S2-06 protection: the PO
goes through `create_po` exclusively — no direct DB insert.

The factory function returns a `SegmentTranslatedHook` (the type alias
defined in `translation.service`). Callers who want pure dry-run translation
(no provenance, no Revision) simply omit `on_segment_translated` from the
job invocation.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.invariant.enums import OperationMode
from waraq.provenance import create_po
from waraq.revision import create_revision
from waraq.schemas import Segment
from waraq.schemas.enums import ChangeSource, POType, ScopeType
from waraq.translation.service import SegmentTranslatedHook, TranslationContext


def make_translation_persistence_hook(
    *,
    engine_identifier: str,
) -> SegmentTranslatedHook:
    """Build a `SegmentTranslatedHook` that writes the canonical
    Revision (when text changes) + TRANSLATION-PO pair.

    Args:
        engine_identifier: Free-text label for the translation engine
            (e.g., "openai/gpt-4o-2024-11-20", "stub-deterministic-v1").
            Recorded on every TRANSLATION-PO payload so downstream
            provenance readout knows which engine produced which output.
    """

    async def _hook(
        session: AsyncSession,
        segment: Segment,
        output_text: str,
        context: TranslationContext,
    ) -> None:
        # Capture input BEFORE create_revision mutates segment.text_content.
        before_text = segment.text_content
        text_changed = output_text != before_text

        rev_uuid_str: str | None = None
        if text_changed:
            # T-1.4.1 H-1/H-2 Guard runs inside create_revision. Translation
            # pipeline never reaches here for locked segments — the live
            # lock-flag check in T-7.1.1's loop skips them. So this Guard
            # is belt-and-braces only.
            revision = await create_revision(
                session=session,
                segment=segment,
                after_text=output_text,
                change_source=ChangeSource.RE_TRANSLATE,
                operation_mode=OperationMode.AUTOMATIC,
            )
            rev_uuid_str = str(revision.rev_uuid)

        po_payload: dict[str, Any] = {
            "engine": engine_identifier,
            "input": before_text,
            "output": output_text,
            "text_changed": text_changed,
            "rev_uuid": rev_uuid_str,
            "terminology_bindings": dict(context.terminology_bindings),
            "style_anchors": list(context.style_anchors),
        }
        await create_po(
            session=session,
            po_type=POType.TRANSLATION,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=segment.satz_uuid,
            payload=po_payload,
        )

    return _hook
