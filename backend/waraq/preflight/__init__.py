"""T-9.1.1 + T-9.1.2 — Preflight (Sprint 4 §2).

The PREFLIGHT module's public surface. Sprint 4 ships:

- Konfigurationsschicht: four Pflichtfragen requiring active confirmation.
- Gate-Prüfungsschicht: P-03 (kritisch), P-04 (Pflichthinweis), W-01
  (mittel-audit), W-02 (Konsistenz), W-03 (graduelle Formatvorlagen).
- Independent named group: Hadith-Verifikationsstatus (H-0/H-1/H-2),
  occupies neither a P- nor a W-Slot.
- State machine: nicht_gestartet → läuft → exportierbar |
  exportierbar_mit_warnungen | blockiert.
- Exportlauf-Ereignis (Log-Eintrag) on every preflight evaluation.

Slot discipline (HG-S4-3): the public evaluator enumerates exactly the
five belegt slots. P-01/P-02/P-05/P-06/W-04..W-08 are not codified.
"""

from waraq.preflight.enums import (
    BlockingReason,
    HadithKlasse,
    HadithStellenTyp,
    PreflightState,
    WarningSlot,
)
from waraq.preflight.exceptions import (
    GuardNearBlocked,
    PflichthinweisCannotBeWarning,
    PreflightError,
    SlotNotImplemented,
)
from waraq.preflight.guard_near import (
    CRITICAL_FONTS,
    GuardNearResult,
    GuardNearViolation,
    run_guard_near_checks,
)
from waraq.preflight.hadith import (
    HADITH_ACTION_TYPES,
    derive_hadith_klasse,
    go_with_warning_hadith,
    record_hadith_status,
    resolve_hadith_h2,
)
from waraq.preflight.konfiguration import (
    PFLICHTFRAGE_COUNT,
    confirm_pflichtfrage,
    save_export_profile_prefill,
)
from waraq.preflight.pdf_choice import (
    PdfFormatChoice,
    confirm_pdf_format_choice,
    read_pdf_format_choice,
)
from waraq.preflight.pflichtfragen import (
    PFLICHTFRAGEN,
    PflichtfrageDefinition,
    get_pflichtfrage_by_index,
    get_pflichtfrage_by_key,
    validate_pflichtfrage_answer,
)
from waraq.preflight.service import (
    PreflightEvaluation,
    accept_warning_gate,
    evaluate_guard_near,
    evaluate_preflight,
    start_preflight_run,
)

__all__ = [
    "CRITICAL_FONTS",
    "HADITH_ACTION_TYPES",
    "PFLICHTFRAGEN",
    "PFLICHTFRAGE_COUNT",
    "BlockingReason",
    "GuardNearBlocked",
    "GuardNearResult",
    "GuardNearViolation",
    "HadithKlasse",
    "HadithStellenTyp",
    "PdfFormatChoice",
    "PflichtfrageDefinition",
    "PflichthinweisCannotBeWarning",
    "PreflightError",
    "PreflightEvaluation",
    "PreflightState",
    "SlotNotImplemented",
    "WarningSlot",
    "accept_warning_gate",
    "confirm_pdf_format_choice",
    "confirm_pflichtfrage",
    "derive_hadith_klasse",
    "evaluate_guard_near",
    "evaluate_preflight",
    "get_pflichtfrage_by_index",
    "get_pflichtfrage_by_key",
    "go_with_warning_hadith",
    "read_pdf_format_choice",
    "record_hadith_status",
    "resolve_hadith_h2",
    "run_guard_near_checks",
    "save_export_profile_prefill",
    "start_preflight_run",
    "validate_pflichtfrage_answer",
]
