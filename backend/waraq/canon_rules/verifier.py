"""§2.2 — Pre-export canon-rule verifier (defense-in-depth).

Per Dokument 1 §2.2 the canonical rules are unconditional system
mechanisms ("Western digits everywhere", "Transliteration standard:
EI2 with Q and J", religious formulas as Unicode glyphs). Primary
enforcement is the `apply_all` auto-normalize:

  - Translation pipeline output (`gemini_translator.py` + OpenAI side).
  - Manual edits via the segment editor router (Phase 3 sub-batch B).

The §4.7.3 guard-near digit-standard pre-check (Phase 3 sub-batch A)
already blocks digit violations from opening preflight. This verifier
is the defense-in-depth twin for **all** §2.2 rules at the export-job
boundary: when any write path bypasses `apply_all` (a future tool, a
raw DB insert, a partial migration), this scan catches the leftover
violation before the export artefact ships.

Canonical placement (per CLAUDE.md §2.7 honest-status):

  - This is **NOT** a 5th §4.7.3 guard-near check (canon §4.7.3
    enumerates exactly 4 — extending that list silently would violate
    §2.6 / §2.7).
  - It is **NOT** a P-/W-Slot (those are belegt per §4.7.4 + §4.7.6).
  - It IS a defense-in-depth verifier hooked into the export-job
    preflight-recheck phase, structurally analogous to the existing
    `PreflightStateChanged` recheck (Sprint 5 §2 R-S5-04).

For §2.2 digit + EI2 violations specifically, the verifier returns a
list of `CanonRuleViolation` rows the caller (`run_export_job`)
translates into a `CanonRuleViolationsDetected` exception, fails the
Job, and writes an `export_failed` Log-Eintrag — same pattern as
`PreflightStateChanged`.
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.canon_rules.digit_guard import has_arabic_indic_digits
from waraq.canon_rules.religious_formulas import has_religious_formula_violations
from waraq.canon_rules.transliteration import has_ei2_violations
from waraq.schemas import Block, Page, Segment
from waraq.text_state import SEPARATOR, split_source_target_text


class CanonRuleViolationKind(StrEnum):
    """The §2.2 canonical-rule violation kinds the verifier scans for.

    All three canonical rules from §2.2 are scanned: Western digits,
    EI2 transliteration, and religious-formula glyphs. Each rule has
    an auto-normalize entry point in `apply_all`; the verifier is the
    defense-in-depth twin that catches any write path that bypassed
    auto-normalize (raw DB insert, partial migration, stale fixture).
    """

    ARABIC_INDIC_DIGITS = "arabic_indic_digits"
    EI2_TRANSLITERATION = "ei2_transliteration"
    RELIGIOUS_FORMULA_NOT_GLYPH = "religious_formula_not_glyph"


@dataclass(frozen=True, slots=True)
class CanonRuleViolation:
    """One leftover §2.2 violation detected on a project segment."""

    satz_uuid: _uuid.UUID
    kind: CanonRuleViolationKind


async def verify_canon_rules_for_export(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
) -> list[CanonRuleViolation]:
    """Scan all active project segments for residual §2.2 violations.

    Returns the full list (empty when the auto-normalize discipline has
    held). Run order is deterministic for stable test assertions:
    digit-standard checks first, then EI2 — but a single segment can
    contribute at most one row per kind.
    """
    result = await session.execute(
        select(Segment.satz_uuid, Segment.text_content)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(Segment.active.is_(True))
    )
    violations: list[CanonRuleViolation] = []
    for satz_uuid, text in result.all():
        if not text:
            continue
        _source_text, target_text = split_source_target_text(text)
        text_to_check = target_text if SEPARATOR in text else text
        if not text_to_check:
            continue
        if has_arabic_indic_digits(text_to_check):
            violations.append(
                CanonRuleViolation(
                    satz_uuid=satz_uuid,
                    kind=CanonRuleViolationKind.ARABIC_INDIC_DIGITS,
                )
            )
        if has_ei2_violations(text_to_check):
            violations.append(
                CanonRuleViolation(
                    satz_uuid=satz_uuid,
                    kind=CanonRuleViolationKind.EI2_TRANSLITERATION,
                )
            )
        # Religious-formula glyph canonicalization applies to spelled-out
        # honorifics wherever they appear in stored segment text. Check the
        # full payload to avoid missing source-side forms in "src---tgt" rows.
        if has_religious_formula_violations(text):
            violations.append(
                CanonRuleViolation(
                    satz_uuid=satz_uuid,
                    kind=CanonRuleViolationKind.RELIGIOUS_FORMULA_NOT_GLYPH,
                )
            )
    return violations


__all__ = [
    "CanonRuleViolation",
    "CanonRuleViolationKind",
    "verify_canon_rules_for_export",
]
