"""§4.12.1 / §2.2 — Tier 1 glossary precedence enforcement (overlay).

> §2.2: "Glossary always takes precedence over learned style. No
>  single-instance override of a glossary entry in context is possible.
>  Anyone wishing to deviate must change or delete the entry."

> §4.12.1: "A style profile suggestion that conflicts with Tier 1 is
>  not executed. Silent override of a Tier 1 system rule by the style
>  feature is excluded."

> §4.6: "C-01: Terminology entry violated – Terminology registry or
>  Glossary (violation of G-2)" — Critical, blocking (P-03).

This module is the translation-time enforcer. It runs on every
translated chunk: for each glossary hit found in the source by
`ChunkContextResolver.resolve` (sub-batch B), it checks whether the
canonical `gloss` actually appears in the LLM output. If not, the
translation is taken as-is (no silent text rewrite — that would
violate the H-1/H-2 manual-write discipline) but a structured
violation record is attached to the TRANSLATION-PO payload.

The C-01 audit rule (`waraq/audit/rules.py::rule_c_01`) is currently
a marker-based stub; a follow-up will upgrade it to query the glossary
directly so the same detection runs at audit-job time. This module
gives immediate visibility at translation time without depending on a
separate audit run.

**No automatic text replacement.** Per H-1/H-2 plus §2.2's "No
single-instance override of a glossary entry in context is possible":
the canonical resolution path is for the user to change or accept,
not for the system to silently rewrite. Detection + persistence is
all this module does.

False-positive note: the substring matcher used here is case-folded
verbatim. German morphology means a glossary entry "Konsens" matches
"Konsens" / "konsensual" / "Konsenses" but NOT a synonym like
"Übereinstimmung". For v1.0 this is acceptable — any genuine
violation surfaces a real-user review. Stem-aware matching is a
Phase 4 follow-up.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, kw_only=True, slots=True)
class GlossaryViolation:
    """One detected glossary-precedence violation: the source contained
    a glossary surface form, but the translation didn't include the
    canonical gloss (or any case-insensitive substring match thereof)."""

    surface_form: str
    expected_gloss: str
    binding_level: str  # 'project' or 'account'
    concept_id: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "surface_form": self.surface_form,
            "expected_gloss": self.expected_gloss,
            "binding_level": self.binding_level,
            "concept_id": self.concept_id,
        }


def verify_glossary_precedence(
    *,
    brief: Any,
    output_text: str,
) -> list[GlossaryViolation]:
    """Check that every glossary hit in `brief` has its `gloss` present
    in `output_text`. Returns a list of detected violations (empty when
    glossary precedence is respected).

    Match heuristic: case-folded substring presence of the gloss in the
    output. Non-empty gloss only — empty/None glosses are skipped (no
    enforceable rendering). When `brief` is None or has no glossary
    hits, returns an empty list immediately.
    """
    if brief is None or not getattr(brief, "glossary_hits", None):
        return []
    if not output_text:
        # Empty output AND glossary hits in source → every hit is a
        # violation (translator produced nothing for terms that
        # canonically must appear).
        return [
            GlossaryViolation(
                surface_form=h.surface_form,
                expected_gloss=h.gloss,
                binding_level=h.binding_level,
                concept_id=str(h.concept_id),
            )
            for h in brief.glossary_hits
            if h.gloss
        ]

    output_cf = output_text.casefold()
    violations: list[GlossaryViolation] = []
    for hit in brief.glossary_hits:
        if not hit.gloss:
            continue
        if hit.gloss.casefold() in output_cf:
            continue
        violations.append(
            GlossaryViolation(
                surface_form=hit.surface_form,
                expected_gloss=hit.gloss,
                binding_level=hit.binding_level,
                concept_id=str(hit.concept_id),
            )
        )
    return violations


__all__ = [
    "GlossaryViolation",
    "verify_glossary_precedence",
]
