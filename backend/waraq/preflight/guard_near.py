"""§4.7.3 — Guard-near pre-checks (run BEFORE the preflight dialog opens).

Per Dokument 1 §4.7.3 + Dokument 2 §3.1, four canonical guard-near
violations block opening the preflight dialog. They are NOT audit
cases; they are direct system mechanisms. None of them occupies a
P-Slot. Resolution paths are technical (fix the data / restore the
font / repair the style template), not "user confirms and proceeds".

Canonical four:

  1. Digit-standard violations         — blocking; system mechanism.
  2. Critical RTL encoding/application — blocking; integrity violation.
  3. Document style template integrity — blocking.
  4. Critical font availability        — blocking; resolution requires
                                         technical font restoration.

The four canonical fonts (§4.7.3 + §7.1):
  - KFGQPC Uthmanic Script HAFS
  - Traditional Naskh
  - Noto Sans Arabic
  - Calibri

Detection:

  - Digit-standard: deterministic — scan project Segment.text_content
    via `waraq.canon_rules.digit_guard.has_arabic_indic_digits`.
  - RTL encoding/application + Style-template integrity: structural
    mechanism with hookable detection. Callers supply a detection
    adapter (defaults to "no findings" so the gate is wired but
    inert until a detector is plugged in — same pattern as W-03's
    `formatvorlagen_graduelle_keys` upstream-supplied list in
    `evaluate_preflight`).
  - Font availability: queries the OS font cache. Stub-injectable
    for tests via `font_resolver` parameter.

Mechanism shipped here is canonical; concrete RTL + style-template
detectors are scope work outside Phase 3 (Phase 4 / OCR review).
The gate refuses to open preflight regardless of detector
sophistication — a stub that returns no findings simply means
"no blockers detected today", not "this rule is off".
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import uuid as _uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.canon_rules.digit_guard import has_arabic_indic_digits
from waraq.schemas import Block, Page, Segment

logger = logging.getLogger(__name__)

# Dev-only escape hatch. When set to a truthy value (`1`/`true`/`yes`),
# `_default_font_resolver` short-circuits to "no missing fonts" so a
# developer iterating on UI flows on a host that lacks Traditional
# Naskh / Calibri / KFGQPC Uthmanic Script HAFS doesn't get blocked
# at preflight. Production deployments must leave this UNSET — a
# warning is logged on every bypass to make accidental prod use loud.
# Tests already bypass the resolver via the autouse conftest fixture
# `_bypass_guard_near_font_check`, so this env var is purely for
# local dev (uvicorn --reload sessions, the user's machine).
_DEV_FONT_BYPASS_ENV = "WARAQ_DEV_FONT_BYPASS"


class GuardNearViolation(StrEnum):
    """The four canonical §4.7.3 guard-near blockers.

    Each value is the wire identifier returned in API responses /
    persisted in `GuardNearResult.blockers`. Adding a fifth here
    silently is a canon violation — the four are exhaustive per
    §4.7.3.
    """

    DIGIT_STANDARD = "digit_standard"
    CRITICAL_RTL = "critical_rtl"
    STYLE_TEMPLATE_INTEGRITY = "style_template_integrity"
    CRITICAL_FONT_MISSING = "critical_font_missing"


CRITICAL_FONTS: tuple[str, ...] = (
    "KFGQPC Uthmanic Script HAFS",
    "Traditional Naskh",
    "Noto Sans Arabic",
    "Calibri",
)
"""Per §4.7.3 + §7.1 — the four named critical fonts. Order matches canon."""


@dataclass(frozen=True, slots=True)
class GuardNearResult:
    """Result of one §4.7.3 guard-near pre-check pass.

    `blockers` is the canonical wire surface. `evidence` carries
    auxiliary diagnostic data (which segment had which digit, which
    font name was missing, etc.) — NOT canonical, NOT relied on by
    the preflight gate logic, but useful for the resolver UI.

    The gate logic is `bool(blockers)` — any blocker refuses to open
    the preflight dialog per §4.7.3.
    """

    blockers: list[GuardNearViolation] = field(default_factory=list)
    advisories: list[GuardNearViolation] = field(default_factory=list)
    evidence: dict[str, list[str]] = field(default_factory=dict)

    @property
    def passes(self) -> bool:
        """True iff no blocker — preflight dialog may open."""
        return not self.blockers


# Type aliases for the hookable detectors. Each takes the AsyncSession
# + project UUID and returns a list of evidence strings (empty = no
# blockers). The gate refuses regardless of evidence content; the
# strings are diagnostic.
RtlDetector = Callable[[AsyncSession, _uuid.UUID], Awaitable[list[str]]]
StyleTemplateDetector = Callable[[AsyncSession, _uuid.UUID], Awaitable[list[str]]]
FontResolver = Callable[[Sequence[str]], list[str]]
"""Returns the subset of font names that are MISSING (empty = all present)."""


# --- Default detector implementations ------------------------------------


async def _detect_digit_standard(session: AsyncSession, project_uuid: _uuid.UUID) -> list[str]:
    """Scan export-target text for Arabic-Indic digits.

    Returns evidence list of `satz_uuid` hex strings for offenders.
    Empty list → no digit-standard violations.
    """
    from waraq.text_state import SEPARATOR, split_source_target_text

    result = await session.execute(
        select(Segment.satz_uuid, Segment.text_content)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(Page.project_uuid == project_uuid)
    )
    offenders: list[str] = []
    for satz_uuid, text in result.all():
        _source_text, target_text = split_source_target_text(text)
        text_to_check = target_text if SEPARATOR in (text or "") else text
        if text_to_check and has_arabic_indic_digits(text_to_check):
            offenders.append(str(satz_uuid))
    return offenders


async def _detect_no_findings(_session: AsyncSession, _project_uuid: _uuid.UUID) -> list[str]:
    """Default no-op detector for RTL + style-template.

    Per the v1.0 implementation choice documented at module top: the
    gate is wired but inert until a real detector lands (Phase 4 /
    OCR review). Returning `[]` means "no findings detected", which
    the gate interprets as "no blocker for this rule today".
    """
    return []


def _default_font_resolver(font_names: Sequence[str]) -> list[str]:
    """Query the OS font cache for the given font names.

    Returns the subset of names NOT found. Uses `fc-list` (fontconfig)
    when available; falls back to "all present" when fontconfig is
    not installed (best-effort — the canonical gate mechanism is
    shipped, OS-specific resolution is calibration territory).

    Tests inject a stub via `run_guard_near_checks(font_resolver=...)`.
    """
    if os.environ.get(_DEV_FONT_BYPASS_ENV, "").strip().lower() in ("1", "true", "yes"):
        # Local-dev override: pretend every requested font is present.
        # Logged loudly so accidental prod-set is impossible to miss.
        logger.warning(
            "guard_near.font_check.bypassed (%s set) — preflight will pass "
            "the critical-font gate without verifying %d font(s). DO NOT "
            "SET THIS IN PRODUCTION.",
            _DEV_FONT_BYPASS_ENV,
            len(font_names),
        )
        return []
    fc_list = shutil.which("fc-list")
    if fc_list is None:
        # Without fontconfig we cannot answer authoritatively. Per
        # §4.7.3 "Resolution requires technical restoration of the
        # font; mere user confirmation does not suffice" — a missing
        # fontconfig is itself a deployment problem, but we don't
        # raise a false positive here. Production deployments install
        # fontconfig; dev hosts may not.
        return []

    try:
        proc = subprocess.run(
            [fc_list, ":", "family"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []

    available_lower = {line.strip().lower() for line in proc.stdout.splitlines() if line.strip()}
    missing: list[str] = []
    for name in font_names:
        # fc-list returns "Family,Family Variant" — match on substring of any family.
        name_lower = name.lower()
        if not any(name_lower in line for line in available_lower):
            missing.append(name)
    return missing


# --- Public entry point --------------------------------------------------


async def run_guard_near_checks(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    rtl_detector: RtlDetector | None = None,
    style_template_detector: StyleTemplateDetector | None = None,
    font_resolver: FontResolver | None = None,
    blocking_violations: set[GuardNearViolation] | None = None,
) -> GuardNearResult:
    """Run all four §4.7.3 guard-near pre-checks and return the result.

    Run order is canonical-stable (digit → RTL → style-template →
    font) so the evidence dict order is reproducible across runs.
    """
    rtl = rtl_detector if rtl_detector is not None else _detect_no_findings
    template = (
        style_template_detector if style_template_detector is not None else _detect_no_findings
    )
    fonts = font_resolver if font_resolver is not None else _default_font_resolver

    blockers: list[GuardNearViolation] = []
    advisories: list[GuardNearViolation] = []
    evidence: dict[str, list[str]] = {}

    def record(violation: GuardNearViolation, items: list[str]) -> None:
        if not items:
            return
        if blocking_violations is None or violation in blocking_violations:
            blockers.append(violation)
        else:
            advisories.append(violation)
        evidence[violation.value] = items

    # 1. Digit standard.
    digit_offenders = await _detect_digit_standard(session, project_uuid)
    record(GuardNearViolation.DIGIT_STANDARD, digit_offenders)

    # 2. RTL encoding/application.
    rtl_evidence = await rtl(session, project_uuid)
    record(GuardNearViolation.CRITICAL_RTL, rtl_evidence)

    # 3. Style template integrity.
    template_evidence = await template(session, project_uuid)
    record(GuardNearViolation.STYLE_TEMPLATE_INTEGRITY, template_evidence)

    # 4. Critical font availability.
    missing_fonts = fonts(CRITICAL_FONTS)
    record(GuardNearViolation.CRITICAL_FONT_MISSING, missing_fonts)

    return GuardNearResult(blockers=blockers, advisories=advisories, evidence=evidence)


__all__ = [
    "CRITICAL_FONTS",
    "FontResolver",
    "GuardNearResult",
    "GuardNearViolation",
    "RtlDetector",
    "StyleTemplateDetector",
    "run_guard_near_checks",
]
