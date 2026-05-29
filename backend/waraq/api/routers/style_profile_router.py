"""Project style-profile endpoints."""

from __future__ import annotations

import uuid as _uuid
import shutil
import subprocess
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from waraq.api._ownership import owned_project_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.preflight.guard_near import CRITICAL_FONTS
from waraq.style_profile import read_project_style_profile, write_project_style_profile

router = APIRouter(prefix="/projects/{project_uuid}/style-profile", tags=["style-profile"])


class StyleProfileResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    translation_font_family: str
    translation_font_size_px: int
    translation_line_height: float
    translation_paragraph_spacing_px: int
    heading_font_size_px: int
    heading_line_height: float
    heading_paragraph_spacing_px: int
    quote_font_size_px: int
    quote_line_height: float
    quote_paragraph_spacing_px: int
    footnote_font_size_px: int
    footnote_line_height: float
    footnote_paragraph_spacing_px: int
    protected_font_size_px: int
    protected_line_height: float
    protected_paragraph_spacing_px: int
    arabic_font_family: str
    arabic_font_size_px: int
    arabic_line_height: float
    page_max_width_rem: int
    docx_translation_font_family: str
    docx_translation_font_size_pt: int
    docx_arabic_font_family: str
    docx_arabic_font_size_pt: int
    docx_line_spacing: float
    docx_paragraph_spacing_pt: int
    docx_heading_font_size_pt: int
    docx_quote_font_size_pt: int
    docx_footnote_font_size_pt: int
    docx_protected_font_size_pt: int
    docx_header_font_size_pt: int
    decision_event_uuid: str | None = None
    updated_at: str | None = None


class StyleProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    translation_font_family: str | None = None
    translation_font_size_px: int | None = None
    translation_line_height: float | None = None
    translation_paragraph_spacing_px: int | None = None
    heading_font_size_px: int | None = None
    heading_line_height: float | None = None
    heading_paragraph_spacing_px: int | None = None
    quote_font_size_px: int | None = None
    quote_line_height: float | None = None
    quote_paragraph_spacing_px: int | None = None
    footnote_font_size_px: int | None = None
    footnote_line_height: float | None = None
    footnote_paragraph_spacing_px: int | None = None
    protected_font_size_px: int | None = None
    protected_line_height: float | None = None
    protected_paragraph_spacing_px: int | None = None
    arabic_font_family: str | None = None
    arabic_font_size_px: int | None = None
    arabic_line_height: float | None = None
    page_max_width_rem: int | None = None
    docx_translation_font_family: str | None = None
    docx_translation_font_size_pt: int | None = None
    docx_arabic_font_family: str | None = None
    docx_arabic_font_size_pt: int | None = None
    docx_line_spacing: float | None = None
    docx_paragraph_spacing_pt: int | None = None
    docx_heading_font_size_pt: int | None = None
    docx_quote_font_size_pt: int | None = None
    docx_footnote_font_size_pt: int | None = None
    docx_protected_font_size_pt: int | None = None
    docx_header_font_size_pt: int | None = None

    def as_patch(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class FontLibraryResponse(BaseModel):
    available_fonts: list[str]
    critical_fonts: list[str]
    missing_critical_fonts: list[str]


@router.get("", response_model=StyleProfileResponse)
async def get_style_profile(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> StyleProfileResponse:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    profile = await read_project_style_profile(session=session, project_uuid=project_uuid)
    return StyleProfileResponse.model_validate(profile)


@router.get("/fonts", response_model=FontLibraryResponse)
async def get_style_font_library(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> FontLibraryResponse:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    fonts = _available_font_families()
    fonts_lower = {font.lower() for font in fonts}
    missing = [
        font
        for font in CRITICAL_FONTS
        if not any(font.lower() in available for available in fonts_lower)
    ]
    return FontLibraryResponse(
        available_fonts=fonts,
        critical_fonts=list(CRITICAL_FONTS),
        missing_critical_fonts=missing,
    )


@router.put("", response_model=StyleProfileResponse)
async def update_style_profile(
    project_uuid: _uuid.UUID,
    req: StyleProfileUpdateRequest,
    session: DbSession,
    current: CurrentAccount,
) -> StyleProfileResponse:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    current_profile = await read_project_style_profile(session=session, project_uuid=project_uuid)
    next_profile = {**current_profile, **req.as_patch()}
    saved = await write_project_style_profile(
        session=session,
        project_uuid=project_uuid,
        profile=next_profile,
        actor_uuid=current.account_uuid,
    )
    return StyleProfileResponse.model_validate(saved)


def _available_font_families() -> list[str]:
    fc_list = shutil.which("fc-list")
    if fc_list is None:
        return []
    proc = subprocess.run(
        [fc_list, ":", "family"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    names: set[str] = set()
    for line in proc.stdout.splitlines():
        for family in line.split(","):
            cleaned = family.strip()
            if cleaned:
                names.add(cleaned)
    return sorted(names)
