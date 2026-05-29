"""Project-level style profile helpers.

The active style profile is stored as the latest project-scoped
DecisionEvent with `decision_source=style_management`. This keeps style
changes auditable without adding a mutable table.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.decisions import create_decision_event
from waraq.schemas import DecisionEvent
from waraq.schemas.enums import DecisionSource, ScopeType

DEFAULT_STYLE_PROFILE: dict[str, Any] = {
    "translation_font_family": "Iowan Old Style",
    "translation_font_size_px": 17,
    "translation_line_height": 1.95,
    "translation_paragraph_spacing_px": 20,
    "heading_font_size_px": 25,
    "heading_line_height": 1.35,
    "heading_paragraph_spacing_px": 24,
    "quote_font_size_px": 16,
    "quote_line_height": 1.85,
    "quote_paragraph_spacing_px": 18,
    "footnote_font_size_px": 14,
    "footnote_line_height": 1.65,
    "footnote_paragraph_spacing_px": 10,
    "protected_font_size_px": 16,
    "protected_line_height": 1.9,
    "protected_paragraph_spacing_px": 16,
    "arabic_font_family": "Noto Naskh Arabic",
    "arabic_font_size_px": 22,
    "arabic_line_height": 2.35,
    "page_max_width_rem": 54,
    "docx_translation_font_family": "Times New Roman",
    "docx_translation_font_size_pt": 11,
    "docx_arabic_font_family": "Noto Naskh Arabic",
    "docx_arabic_font_size_pt": 14,
    "docx_line_spacing": 1.25,
    "docx_paragraph_spacing_pt": 6,
    "docx_heading_font_size_pt": 16,
    "docx_quote_font_size_pt": 10,
    "docx_footnote_font_size_pt": 9,
    "docx_protected_font_size_pt": 11,
    "docx_header_font_size_pt": 9,
    "translation_style_templates": {
        "body_de": {
            "display_label": "Body",
            "font_family": "Calibri",
            "font_size_px": 17,
            "line_height": 1.65,
            "paragraph_spacing_px": 8,
            "docx_font_size_pt": 11,
            "alignment": "left",
            "first_line_indent_px": 19,
            "left_indent_px": 0,
            "border_left": False,
            "italic": False,
            "bold": False,
        },
        "body_de_no_indent": {
            "display_label": "Body, no indent",
            "font_family": "Calibri",
            "font_size_px": 17,
            "line_height": 1.65,
            "paragraph_spacing_px": 8,
            "docx_font_size_pt": 11,
            "alignment": "left",
            "first_line_indent_px": 0,
            "left_indent_px": 0,
            "border_left": False,
            "italic": False,
            "bold": False,
        },
        "heading_1": {
            "display_label": "Heading 1",
            "font_family": "Calibri",
            "font_size_px": 24,
            "line_height": 1.25,
            "paragraph_spacing_px": 16,
            "docx_font_size_pt": 16,
            "alignment": "left",
            "first_line_indent_px": 0,
            "left_indent_px": 0,
            "border_left": False,
            "italic": False,
            "bold": True,
        },
        "heading_2": {
            "display_label": "Heading 2",
            "font_family": "Calibri",
            "font_size_px": 21,
            "line_height": 1.25,
            "paragraph_spacing_px": 12,
            "docx_font_size_pt": 14,
            "alignment": "left",
            "first_line_indent_px": 0,
            "left_indent_px": 0,
            "border_left": False,
            "italic": False,
            "bold": True,
        },
        "heading_3": {
            "display_label": "Heading 3",
            "font_family": "Calibri",
            "font_size_px": 18,
            "line_height": 1.25,
            "paragraph_spacing_px": 10,
            "docx_font_size_pt": 12,
            "alignment": "left",
            "first_line_indent_px": 0,
            "left_indent_px": 0,
            "border_left": False,
            "italic": False,
            "bold": True,
        },
        "heading_4": {
            "display_label": "Heading 4",
            "font_family": "Calibri",
            "font_size_px": 17,
            "line_height": 1.25,
            "paragraph_spacing_px": 8,
            "docx_font_size_pt": 12,
            "alignment": "left",
            "first_line_indent_px": 0,
            "left_indent_px": 0,
            "border_left": False,
            "italic": False,
            "bold": True,
        },
        "heading_5": {
            "display_label": "Heading 5",
            "font_family": "Calibri",
            "font_size_px": 16,
            "line_height": 1.25,
            "paragraph_spacing_px": 8,
            "docx_font_size_pt": 11,
            "alignment": "left",
            "first_line_indent_px": 0,
            "left_indent_px": 0,
            "border_left": False,
            "italic": False,
            "bold": True,
        },
        "heading_6": {
            "display_label": "Heading 6",
            "font_family": "Calibri",
            "font_size_px": 16,
            "line_height": 1.25,
            "paragraph_spacing_px": 6,
            "docx_font_size_pt": 11,
            "alignment": "left",
            "first_line_indent_px": 0,
            "left_indent_px": 0,
            "border_left": False,
            "italic": False,
            "bold": True,
        },
        "quran_de": {
            "display_label": "Quran translation",
            "font_family": "Calibri",
            "font_size_px": 17,
            "line_height": 1.5,
            "paragraph_spacing_px": 12,
            "docx_font_size_pt": 11,
            "alignment": "left",
            "first_line_indent_px": 0,
            "left_indent_px": 23,
            "border_left": True,
            "italic": False,
            "bold": False,
        },
        "hadith_de": {
            "display_label": "Hadith translation",
            "font_family": "Calibri",
            "font_size_px": 17,
            "line_height": 1.5,
            "paragraph_spacing_px": 12,
            "docx_font_size_pt": 11,
            "alignment": "left",
            "first_line_indent_px": 0,
            "left_indent_px": 23,
            "border_left": True,
            "italic": False,
            "bold": False,
        },
        "quote_de": {
            "display_label": "Quote",
            "font_family": "Calibri",
            "font_size_px": 16,
            "line_height": 1.45,
            "paragraph_spacing_px": 12,
            "docx_font_size_pt": 10,
            "alignment": "left",
            "first_line_indent_px": 0,
            "left_indent_px": 23,
            "border_left": True,
            "italic": True,
            "bold": False,
        },
        "source_note": {
            "display_label": "Source note",
            "font_family": "Calibri",
            "font_size_px": 14,
            "line_height": 1.35,
            "paragraph_spacing_px": 10,
            "docx_font_size_pt": 9,
            "alignment": "left",
            "first_line_indent_px": 0,
            "left_indent_px": 23,
            "border_left": False,
            "italic": False,
            "bold": False,
        },
        "footnote_text": {
            "display_label": "Footnote",
            "font_family": "Calibri",
            "font_size_px": 14,
            "line_height": 1.25,
            "paragraph_spacing_px": 6,
            "docx_font_size_pt": 9,
            "alignment": "left",
            "first_line_indent_px": 0,
            "left_indent_px": 0,
            "border_left": False,
            "italic": False,
            "bold": False,
        },
    },
}


def normalize_style_profile(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Merge user overrides with safe defaults and clamp numeric values."""
    data = {**DEFAULT_STYLE_PROFILE, **(raw or {})}
    return {
        "translation_font_family": _string(
            data["translation_font_family"], 80, DEFAULT_STYLE_PROFILE["translation_font_family"]
        ),
        "translation_font_size_px": _clamp_int(data["translation_font_size_px"], 13, 26),
        "translation_line_height": _clamp_float(data["translation_line_height"], 1.25, 2.6),
        "translation_paragraph_spacing_px": _clamp_int(
            data["translation_paragraph_spacing_px"], 8, 40
        ),
        "heading_font_size_px": _clamp_int(data["heading_font_size_px"], 16, 38),
        "heading_line_height": _clamp_float(data["heading_line_height"], 1.0, 2.0),
        "heading_paragraph_spacing_px": _clamp_int(
            data["heading_paragraph_spacing_px"], 8, 52
        ),
        "quote_font_size_px": _clamp_int(data["quote_font_size_px"], 12, 24),
        "quote_line_height": _clamp_float(data["quote_line_height"], 1.2, 2.4),
        "quote_paragraph_spacing_px": _clamp_int(
            data["quote_paragraph_spacing_px"], 6, 36
        ),
        "footnote_font_size_px": _clamp_int(data["footnote_font_size_px"], 10, 20),
        "footnote_line_height": _clamp_float(data["footnote_line_height"], 1.1, 2.2),
        "footnote_paragraph_spacing_px": _clamp_int(
            data["footnote_paragraph_spacing_px"], 4, 28
        ),
        "protected_font_size_px": _clamp_int(data["protected_font_size_px"], 12, 24),
        "protected_line_height": _clamp_float(data["protected_line_height"], 1.2, 2.5),
        "protected_paragraph_spacing_px": _clamp_int(
            data["protected_paragraph_spacing_px"], 6, 36
        ),
        "arabic_font_family": _string(
            data["arabic_font_family"], 80, DEFAULT_STYLE_PROFILE["arabic_font_family"]
        ),
        "arabic_font_size_px": _clamp_int(data["arabic_font_size_px"], 16, 34),
        "arabic_line_height": _clamp_float(data["arabic_line_height"], 1.6, 3.0),
        "page_max_width_rem": _clamp_int(data["page_max_width_rem"], 38, 72),
        "docx_translation_font_family": _string(
            data["docx_translation_font_family"],
            80,
            DEFAULT_STYLE_PROFILE["docx_translation_font_family"],
        ),
        "docx_translation_font_size_pt": _clamp_int(
            data["docx_translation_font_size_pt"], 9, 16
        ),
        "docx_arabic_font_family": _string(
            data["docx_arabic_font_family"], 80, DEFAULT_STYLE_PROFILE["docx_arabic_font_family"]
        ),
        "docx_arabic_font_size_pt": _clamp_int(data["docx_arabic_font_size_pt"], 10, 22),
        "docx_line_spacing": _clamp_float(data["docx_line_spacing"], 1.0, 2.0),
        "docx_paragraph_spacing_pt": _clamp_int(data["docx_paragraph_spacing_pt"], 0, 18),
        "docx_heading_font_size_pt": _clamp_int(
            data["docx_heading_font_size_pt"], 11, 24
        ),
        "docx_quote_font_size_pt": _clamp_int(data["docx_quote_font_size_pt"], 8, 14),
        "docx_footnote_font_size_pt": _clamp_int(
            data["docx_footnote_font_size_pt"], 7, 12
        ),
        "docx_protected_font_size_pt": _clamp_int(
            data["docx_protected_font_size_pt"], 8, 14
        ),
        "docx_header_font_size_pt": _clamp_int(data["docx_header_font_size_pt"], 7, 14),
        "translation_style_templates": _normalize_translation_style_templates(
            data.get("translation_style_templates")
        ),
    }


def _normalize_translation_style_templates(raw: Any) -> dict[str, dict[str, Any]]:
    defaults = DEFAULT_STYLE_PROFILE["translation_style_templates"]
    source = raw if isinstance(raw, dict) else {}
    normalized: dict[str, dict[str, Any]] = {}
    for key, default_value in defaults.items():
        override = source.get(key)
        item = {**default_value, **(override if isinstance(override, dict) else {})}
        normalized[key] = {
            "display_label": _string(item.get("display_label"), 80, default_value["display_label"]),
            "font_family": _string(item.get("font_family"), 80, default_value["font_family"]),
            "font_size_px": _clamp_int(item.get("font_size_px"), 8, 48),
            "line_height": _clamp_float(item.get("line_height"), 1.0, 3.0),
            "paragraph_spacing_px": _clamp_int(item.get("paragraph_spacing_px"), 0, 72),
            "docx_font_size_pt": _clamp_int(item.get("docx_font_size_pt"), 6, 32),
            "alignment": _alignment(item.get("alignment"), default_value["alignment"]),
            "first_line_indent_px": _clamp_int(
                item.get("first_line_indent_px"), -80, 120
            ),
            "left_indent_px": _clamp_int(item.get("left_indent_px"), 0, 160),
            "border_left": bool(item.get("border_left")),
            "italic": bool(item.get("italic")),
            "bold": bool(item.get("bold")),
        }
    return normalized


def _alignment(value: Any, fallback: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in {"left", "center", "right", "justify"} else fallback


async def read_project_style_profile(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> dict[str, Any]:
    result = await session.execute(
        select(DecisionEvent)
        .where(DecisionEvent.scope_type == ScopeType.PROJECT.value)
        .where(DecisionEvent.scope_uuid == project_uuid)
        .where(DecisionEvent.decision_source == DecisionSource.STYLE_MANAGEMENT.value)
        .where(DecisionEvent.decision_type == "style_profile_update")
        .order_by(DecisionEvent.created_at.desc())
        .limit(1)
    )
    decision = result.scalar_one_or_none()
    if decision is None:
        return normalize_style_profile(None)
    content = decision.content or {}
    profile = content.get("profile") if isinstance(content, dict) else None
    return normalize_style_profile(profile if isinstance(profile, dict) else None)


async def write_project_style_profile(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    profile: dict[str, Any],
    actor_uuid: _uuid.UUID,
) -> dict[str, Any]:
    normalized = normalize_style_profile(profile)
    decision = await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        decision_type="style_profile_update",
        decision_source=DecisionSource.STYLE_MANAGEMENT,
        content={"profile": normalized},
        actor_uuid=actor_uuid,
    )
    return {
        **normalized,
        "decision_event_uuid": str(decision.decision_event_uuid),
        "updated_at": decision.created_at.isoformat() if decision.created_at else None,
    }


def _string(value: Any, max_len: int, fallback: Any) -> str:
    text = str(value or "").strip()
    return (text or str(fallback))[:max_len]


def _clamp_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = minimum
    return max(minimum, min(maximum, parsed))


def _clamp_float(value: Any, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = minimum
    return round(max(minimum, min(maximum, parsed)), 2)
