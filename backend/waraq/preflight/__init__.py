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
)
from waraq.preflight.exceptions import (
    PflichthinweisCannotBeWarning,
    PreflightError,
    SlotNotImplemented,
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
from waraq.preflight.service import (
    PreflightEvaluation,
    accept_warning_gate,
    evaluate_preflight,
    start_preflight_run,
)

__all__ = [
    "HADITH_ACTION_TYPES",
    "PFLICHTFRAGE_COUNT",
    "BlockingReason",
    "HadithKlasse",
    "HadithStellenTyp",
    "PflichthinweisCannotBeWarning",
    "PreflightError",
    "PreflightEvaluation",
    "PreflightState",
    "SlotNotImplemented",
    "accept_warning_gate",
    "confirm_pflichtfrage",
    "derive_hadith_klasse",
    "evaluate_preflight",
    "go_with_warning_hadith",
    "record_hadith_status",
    "resolve_hadith_h2",
    "save_export_profile_prefill",
    "start_preflight_run",
]
