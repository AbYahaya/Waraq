# CR Paket 7 — Schluss-Audit (Closing Audit)

**Status:** **RESOLVED — all three items decided 2026-05-08.**

- Item 1 → closed (already consistent on inspection).
- Item 2 → **(a)** approved. TOC raised to `\o "1-6"` in Formatvorlagen-Baseline v1.1 §7.2 (DE + EN); `_add_toc` implementation updated.
- Item 3 → **(β)** approved. Formal canonization deferred. Empirical mapping (12 cells) preserved below as informational; deferred to post-v1.0 stilfeature follow-on (CR-3, F1/F3/F4/F5).

ALT→NEU diffs applied; Dokument 2 §2D updated with both resolution notes. This file is preserved as the historical record of the decision process.

**Anchored to:** Sprint 6 §7 ("What remains canonically open after Sprint 6"),
Dokument 2 §2D ("Bound residual notices"), and the explicit references in
both to "anchored cleanly in the closing audit (Package 7) as ALT→NEU block".

**Scope:** Three deferred canon items per Sprint 6 §7. Items resolved
in earlier rounds (or shown to be already consistent on inspection)
are noted with their current state; items still requiring user
direction are flagged with options.

---

## Item 1 — `scope_type` enum extension (CAB §B.1, Dokument 1 §4.11)

**Status on inspection: already consistent. No ALT→NEU required.**

Dokument 2 §2D records: "*Decided: The enum value space is extended to
`segment | page | block | account | project`. ... anchored cleanly in
the closing audit (Package 7) as ALT→NEU block in CAB §B.1 and
Document 1 §4.11.*"

On inspection of the v1.0 baselines today:

- **CAB §B.1 (DE original, line 119)** already lists the full 5-value
  enum: `segment, page, block, account, project`. The marked
  paragraph reflects the decided extension.
- **CAB §B.1 (EN translation, line 110)** matches.
- **Dokument 1 §4.11 (DE original, line 634)** already states:
  > "Der allgemeine scope_type-Enum umfasst gemäss Core Architecture
  > Baseline §B.1: segment, page, block, account, project."
- **Dokument 1 §4.11 (EN translation, line 521)** matches.

The §4.11 OCR-export query rule itself uses only `segment` and `page`
in its WHERE clause — that is **deliberately snapshot-specific** per
the explicit footnote ("does not restrict the general scope_type
enum") and is correct as-is.

**Implementation alignment (no canon change):**
- `waraq.schemas.enums.ScopeType` enumerates all 5 values.
- `ScopeType` CHECK constraint on `decision_events` enforces the 5-value set.
- 23 schema regression tests cover the round-trip across all 5 values × all 10 `decision_source` values (`tests/schemas/test_events.py`).

**Action requested**: confirm "Item 1: closed — already consistent",
or flag any specific section you believe still needs an ALT→NEU diff.

---

## Item 2 — Heading-4/5/6 coverage (Formatvorlagen v1.1 §7.2, Dokument 1 §7.1, EEB v1.0 §3.4)

**Status: a real gap, but smaller than Sprint 6 §7's framing suggests.
User direction needed on the resolution.**

Sprint 6 §7 phrased this as a gap "zwischen Formatvorlagen-Baseline
v1.1 §7.2 (Heading 1–3 explizit), Dokument 1 §7.1 (Heading 1–6 für
Calibri), EEB v1.0 §3.4 und der IVZ-Konfiguration `\o "1-4"`".

On inspection:

- **Formatvorlagen-Baseline v1.1 §7.2** (DE lines 59–64) actually
  defines all 6 levels explicitly with full formatting properties
  (font, size, line-spacing, before/after, indent). The "Heading 1–3
  explizit" framing in Sprint 6 §7 is outdated — Heading 4, 5, and 6
  are present.
- **Dokument 1 §7.1** mentions Heading 1–6 for Calibri.
- **EEB §3.4** mentions Heading 1–6 for Calibri.
- **TOC configuration in Formatvorlagen-Baseline v1.1 §7.2** is
  `\o "1-4"` — meaning the table-of-contents includes Heading 1
  through 4 only.

**The actual gap:** Heading 5 and Heading 6 are **defined as styles**
but **not included in the auto-generated TOC**. This is a real
inconsistency to resolve. It can mean:

(a) **TOC should be `\o "1-6"`** — all defined heading levels are
    navigable. Cleanest if Heading 5/6 are intended for use.

(b) **TOC stays `\o "1-4"` deliberately** — Heading 5 and 6 are
    explicitly **not** navigable in TOC. Then a sentence to that
    effect should be added to §7.2 to remove the apparent
    inconsistency.

(c) **Reduce defined heading styles to 1–4** — drop Heading 5 and 6
    entirely from §7.2, matching the TOC depth. Cleaner if Heading
    5/6 are vestigial.

**My read of Dokument 1 §7.1 + EEB §3.4** ("Calibri … Heading 1–6"):
the canon expects 1–6 to be available styles. So **(c)** would
remove canonically-listed coverage. Between **(a)** and **(b)**, the
question is whether Heading 5/6 are deep-document landmarks the user
wants in the TOC or local-only structural markers.

**Recommendation: (a) `\o "1-6"`** — matches Calibri Heading 1–6
mention in Dokument 1 §7.1 + EEB §3.4 and the explicit definitions
in Formatvorlagen §7.2. The cost is a possibly-deeper TOC; user can
always limit per-export via a Pflichtfrage if a 4-level TOC is
preferred for a specific document.

**ALT (Formatvorlagen v1.1 §7.2 line 42)**:
> *TOC \o "1-4" \u. Tab-Stop 325,5 pt rechts, Punkte als Führungszeichen. Einzüge: toc1 = 0 pt, toc2 = 11 pt, toc3 = 22 pt, toc4 = 33 pt. Abstand nach allen IVZ-Ebenen: 5 pt.*

**NEU (recommendation a)**:
> *TOC \o "1-6" \u. Tab-Stop 325,5 pt rechts, Punkte als Führungszeichen. Einzüge: toc1 = 0 pt, toc2 = 11 pt, toc3 = 22 pt, toc4 = 33 pt, toc5 = 44 pt, toc6 = 55 pt. Abstand nach allen IVZ-Ebenen: 5 pt.*

**Implementation alignment**: `waraq/export/docx_builder.py::_add_toc`
currently writes `TOC \o "1-4"` per the ALT. Implementation will
follow whichever option you pick.

**Action requested**: pick (a) / (b) / (c).

---

## Item 3 — `decision_source × scope_type` mapping table (Dokument 2 §2D)

**Status: real gap — no canonical mapping table exists.**

Dokument 2 §2D (line 261) explicitly:
> "*The mapping between decision_source and permissible scope_type is
> not centrally defined in the current canon but distributed across
> multiple documents (CAB §B–§C, Document 1 §4.x, DBB T-x.x.x, OCR
> Export v1.3). A complete and consistent mapping table is currently
> not present. This gap is held as bound residual notice and requires
> systematic, source-supported consolidation before possible
> canonization. No implicit condensation or pre-emption.*"

**The implementation has, in the course of M2-M5, established a
working mapping** by writing Decision Events for every event class.
That working mapping is captured below from a sweep of `tests/`,
`waraq/decisions/`, `waraq/preflight/`, `waraq/audit/`, `waraq/consistency/`,
`waraq/conflicts/`, `waraq/lock/`, `waraq/glossary/`, `waraq/promotion/`,
and `waraq/export/`.

### Empirical mapping (from implementation; **not** yet canon)

| `decision_source` | Used at `scope_type` | Producing service / DE type |
|---|---|---|
| `ocr_review` | `page` | `waraq.ocr.review` — OCR-Status-Beschluss |
| `lock_management` | `segment` | `waraq.lock.service` — `lock_set` / `lock_release` |
| `conflict_resolution` | `segment` | `waraq.conflicts.service` — `local_exception` / `glossary_overrides` / `keep_locked` (the 3 H-6 paths) |
| `translation_pipeline` | `project` | `waraq.release_gate.service::start_translation` — `uebersetzungsstart` |
| `audit_resolution` | `segment` | `waraq.audit.service` — `audit_befund_aufgeloest` / `audit_befund_quittiert` |
| `consistency_resolution` | `project` | `waraq.consistency.resolution` — `konsistenzgruppe_verbindlich` / `konsistenzbefund_quittiert` |
| `glossary_management` | `project`, `account` | `waraq.glossary.service` (project-bound + account-bound entries); `waraq.entities.service` (subsystem='entity') |
| `preflight_confirmation` | `project` | `waraq.preflight.konfiguration::confirm_pflichtfrage`, `waraq.preflight.service::accept_warning_gate`, `waraq.preflight.hadith::go_with_warning_hadith`, `waraq.export.service::export_starten` |
| `export_confirmation` | `project` | OCR-export only (`waraq.ocr_export.gate` Pflichtfragen-Bestätigung) |
| `style_management` | `project`, `account` | `waraq.promotion.stilregel::bestaetige_stilregel` (project), `verwerfe_musterkandidat` (project); future F1/F3/F4/F5 work will add account-scope |

### Notes

- **`scope_type=block` is canonically permitted but currently unused** in any service. If/when block-level decisions become load-bearing, this row gets filled in. Keeping the column open is correct.
- **`style_management × account`** is the gebundener Resthinweis from
  Dokument 2 §2D about the account-scoped Decision-Event-Lesepfad —
  deferred per CR-3 follow-on. The mapping cell is **decided** (it WILL
  be `account` for project-cross-cutting Stilprofil-Decisions per Dokument 1
  §5.2) but the read path is held.
- **`scope_type=segment` × `translation_pipeline`** is reserved per
  Dokument 1 §4.16.5 (Hadith action types) but currently routed at
  `scope_type=project` via `waraq.preflight.hadith::resolve_hadith_h2`.
  Per §4.16.6 Level 4 the Hadith result-object's user-decision overlay
  is per-passage (which corresponds to segment scope), but v1.0 routes
  via project scope as a simplification. This is consistent with the
  v1.0 minimal Hadith model decision (WORKLOG 2026-05-07).

### Proposed canonization

Two options:

(α) **Full canonization**: insert this table verbatim as a new
    sub-section "§B.2 — `decision_source × scope_type` mapping" in
    CAB. Adds normative weight to the implementation's choices.

(β) **Decline canonization for v1.0**: keep the table as informational
    documentation in Dokument 2 §3.X "Working state — implementation
    mapping". Defer formal canonization until F1/F3/F4/F5 stilfeature
    follow-on completes (when account-scope rows fill in).

Recommendation: **(β)**. The mapping is real but two cells (style_management
× account, possibly translation_pipeline × segment for §4.16.5)
require post-v1.0 work to lock down. Premature canonization of the
empirical state would make those future cells harder to amend.

**Action requested**: pick (α) / (β).

---

## Summary

| Item | Decision (2026-05-08) | Result |
|---|---|---|
| 1. `scope_type` enum extension | closed — already consistent | no canon change |
| 2. Heading-4/5/6 / TOC depth | **(a)** TOC `\o "1-6"` | Formatvorlagen v1.1 §7.2 (DE+EN) updated; `_add_toc` updated; test assertion updated |
| 3. `decision_source × scope_type` mapping | **(β)** defer canonization | mapping table preserved here as informational; Dokument 2 §2D notes status |

All approved ALT→NEU edits applied. Implementation alignment for Item 2
landed in `waraq/export/docx_builder.py::_add_toc` and the matching
assertion in `tests/export/test_export_gate_mode_and_format.py`.
