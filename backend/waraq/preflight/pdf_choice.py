"""§4.7.2 — PDF export format choice (Configuration Layer).

Per Dokument 1 §4.7.2:

  PDF export: Digital (RGB) or Print (PDF/X-1a, CMYK, 3 mm bleed).

This is a §4.7.2 Configuration Layer decision but **not** one of the
four canonical Pflichtfragen — the canon labels the four Pflichtfragen
explicitly (header heading-level / chapter-break heading-level / TOC
position / display-Arabic-headings). The PDF format choice is a
separate Configuration-Layer item, recorded when the user selects PDF
as the export format.

Two canonical values:

  - `digital_rgb`        — RGB output, no PDF/X-1a post-processing.
                           Suitable for screen reading, web distribution.
  - `print_pdf_x_1a`     — PDF/X-1a, CMYK, 3 mm bleed, prepress-grade.
                           Suitable for offset/digital print providers.

Persistence: each active selection writes a Decision Event with
`scope_type=project`, `decision_source=preflight_confirmation`
(§4.10), `decision_type="pdf_format_choice"`, tagged with
`related_export_attempt_id=<preflight_run_uuid>`. This mirrors the
Pflichtfrage-confirmation pattern: a saved-profile pre-fill never
replaces an active selection at export time.
"""

from __future__ import annotations

import uuid as _uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.decisions import create_decision_event
from waraq.schemas import DecisionEvent
from waraq.schemas.enums import DecisionSource, ScopeType


class PdfFormatChoice(StrEnum):
    """Per §4.7.2 — the two canonical PDF format choices."""

    DIGITAL_RGB = "digital_rgb"
    PRINT_PDF_X_1A = "print_pdf_x_1a"


_DECISION_TYPE = "pdf_format_choice"


async def confirm_pdf_format_choice(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    preflight_run_uuid: _uuid.UUID,
    choice: PdfFormatChoice,
    actor_uuid: _uuid.UUID | None = None,
) -> DecisionEvent:
    """Active confirmation of the PDF format choice for the current run.

    Writes a Decision Event with:
      - scope_type = project
      - decision_type = "pdf_format_choice"
      - decision_source = preflight_confirmation
      - related_export_attempt_id = str(preflight_run_uuid)
      - content = {"choice": "<digital_rgb|print_pdf_x_1a>"}

    A run may have multiple Decision Events for this type (the user
    can change their mind before export); the latest applies. The
    `read_pdf_format_choice` reader returns the most-recently created
    DE for the run.
    """
    de_content: dict[str, Any] = {
        "choice": choice.value,
        "preflight_run_uuid": str(preflight_run_uuid),
    }

    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        decision_type=_DECISION_TYPE,
        decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        actor_uuid=actor_uuid,
        content=de_content,
        related_export_attempt_id=str(preflight_run_uuid),
    )
    return de


async def read_pdf_format_choice(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    preflight_run_uuid: _uuid.UUID,
) -> PdfFormatChoice | None:
    """Read the latest active PDF format choice for the run.

    Returns None if the user hasn't confirmed a choice yet — callers
    interpret None as "no PDF export selected" (so a DOCX-only export
    is still valid; the choice only matters for PDF artefact paths).
    """
    result = await session.execute(
        select(DecisionEvent)
        .where(DecisionEvent.scope_type == ScopeType.PROJECT.value)
        .where(DecisionEvent.scope_uuid == project_uuid)
        .where(DecisionEvent.decision_source == DecisionSource.PREFLIGHT_CONFIRMATION.value)
        .where(DecisionEvent.decision_type == _DECISION_TYPE)
        .where(DecisionEvent.related_export_attempt_id == str(preflight_run_uuid))
        .order_by(DecisionEvent.created_at.desc())
    )
    latest = result.scalars().first()
    if latest is None:
        return None
    raw = (latest.content or {}).get("choice")
    if not isinstance(raw, str):
        return None
    try:
        return PdfFormatChoice(raw)
    except ValueError:
        return None


__all__ = [
    "PdfFormatChoice",
    "confirm_pdf_format_choice",
    "read_pdf_format_choice",
]
