# /docs/canon/ — Waraq Canonical Documents

This directory holds the frozen v1.0 specification canon for Waraq plus the lebende Master and the Arbeits-/Referenzdokument. The seven sprint plans v1.0 also live here, canonized 2026-05-01 per option (c).

This README is navigation only. For discipline rules — no coding without Coding-Freigabe, no silent re-baselining, no invented canon, etc. — see `/CLAUDE.md` at the project root.

---

## Directory structure

```
/docs/canon/
├── README.md                 ← this file
├── de/                       ← German originals; AUTHORITATIVE source-of-truth
└── en/                       ← English translations; agent-facing working copy
```

**Authority rule.** When German and English disagree on a substantive point, German is correct. The English directory exists for agent-facing fluency and accessibility, not for canon authority. Translation drift is a discipline failure — surface it, do not silently propagate.

**Asymmetry.** The two directories do not contain identical document sets. The German directory holds every canonical document. The English directory holds only documents that have been deliberately translated, plus the seven sprint plans (which exist as byte-identical English-content copies in both `en/Sprint-plan/` and `de/Sprint-plan/` — see §2.2 and §3). See §2 for the per-document split.

**Format within `de/`.** Each canonical document is held in two formats: the original `.docx` (Word) and a pandoc-converted `.md` (Markdown). The `.docx` is **source-of-truth**; the `.md` is a content-faithful conversion produced for agent readability and is regenerated whenever the `.docx` updates. Each `.md` carries a provenance header naming its `.docx` source and conversion date. Conversion preserves text, tables, identifier-like terms, Swiss German "ss", Arabic with RTL spans, §-references, and Word highlighting (as `<span class="mark">…</span>` where present in the source); it drops Word-specific visual styling. If `.md` and `.docx` disagree on substantive content, the `.docx` is correct — surface the drift and regenerate, do not silently propagate.

---

## 1. Status conventions

| Marker | Meaning |
|---|---|
| **eingefroren v1.0** | Frozen at version 1.0. Do not modify without an explicit Change-Request cycle. CR cycle: requirement → impact analysis → ALT→NEU diff → user approval → canon amendment. |
| **lebende Master** | Live, ongoing canonical updates. Currently only `Dokument 1`. Updates still require CR for substantive change; minor consolidation/clarification proceeds inline. |
| **Arbeits-/Referenzdokument** | Live working/reference doc. Currently only `Dokument 2`. Authoritative for process state (open/parked/decided lists), not for content canon. |
| **Arbeitsentwurf, kein Kanon** | Preserved working drafts. Currently only `Block 3`. Treat as preserved positions for later canonization, never as authoritative. |

When in doubt about a document's status, check its header. Every document carries its own status declaration.

---

## 2. Document inventory

### 2.1 Frozen v1.0 baselines (eingefroren)

| Document | German (de/) | English (en/) | Scope summary |
|---|---|---|---|
| Core Architecture Baseline | `core_architecture_baseline_v1_0.md` | — | Object model, identity types, H-1 through H-7 invariants, scope_type enum, F-01–F-09 fields, lineage logic |
| Implementation Translation Baseline | `implementation_translation_baseline_v1_0.md` | — | A-01–D-03 audit rule structure, K-01–K-07 consistency rules, gate semantics, preflight schichtenmodell |
| Engineering Execution Baseline | `engineering_execution_baseline_v1_0.md` | — | Definition of Done, execution disciplines, test family expectations |
| Delivery Backlog Baseline | `delivery_backlog_baseline_v1_0.md` | — | All 39 tickets T-1.1.1 through T-10.2.1, hard-gate list, falsche Abkürzungen, CR-3 stilfeature backlog layer |
| OCR-Export Endfassung v1.3 | `ocr_text_export_v1_3.md` | `ocr_text_export_v1_3.md` | OCR-export pipeline, OCR_EXPORT_EVENT semantics, Sprint-OCR plan |
| Dokument A v1.0 — Nutzerstil-Korpus | `dokument_a_v1_0_nutzerstil_korpus.md` | `dokument_a_v1_0_nutzerstil_korpus.md` | Bilingual AR/DE Stilfeature reference data |
| Dokument B v1.2 | `dokument_b_v1_2_erkenne_meinen_uebersetzungsstil.md` | `dokument_b_v1_2_erkenne_meinen_uebersetzungsstil.md` | "Erkenne meinen Übersetzungsstil" feature spec |
| Dokument C v1.1 — Integrationsnachricht | `dokument_c_v1_1_integrationsnachricht.md` | `dokument_c_v1_1_integrationsnachricht.md` | Stilfeature integration; deferral list (F1, F3, F4, F5) |
| Formatvorlagen-Baseline v1.1 | `formatvorlagen_baseline_v1_1.md` | `formatvorlagen_baseline_v1_1.md` | Layout, RTL handling, headings (with §7.2 Heading-4/5/6 Resthinweis), TOC, footnotes |
| Baseline Delivery Plan v1.0 | `baseline_delivery_plan_v1_0.md` | `baseline_delivery_plan_v1_0.md` | 7-sprint delivery roadmap at sprint-level abstraction |

### 2.2 Sprint plans v1.0 (eingefroren — see §3 for authorship note)

The seven sprint plans live in **both** `en/Sprint-plan/` and `de/Sprint-plan/` as byte-identical English-content copies. They were authored 2026-05-01 in English as canonical replacements for presumed-lost originals per option (c); no German translation exists. The German directory holds the duplicate intentionally for navigational symmetry, not as a translation. **For the sprint plans only, English is the authoring location** — if the two copies ever diverge, the English version is correct. This inverts the general Authority rule (which applies to every other document set) and applies *only* to the sprint plans.

| Sprint | File (present in both `de/Sprint-plan/` and `en/Sprint-plan/`) |
|---|---|
| Sprint 0 — Foundation | `sprint_0_foundation_delivery_plan_v1_0.md` |
| Sprint 1 — OCR Review + Lock + Glossary | `sprint_1_ocr_review_lock_glossary_delivery_plan_v1_0.md` |
| Sprint 2 — Release Gate + Translation Core | `sprint_2_release_gate_translation_core_delivery_plan_v1_0.md` |
| Sprint 3 — Audit + Rule-Binding Completion | `sprint_3_audit_rule_binding_completion_delivery_plan_v1_0.md` |
| Sprint 4 — Consistency + Preflight | `sprint_4_consistency_preflight_delivery_plan_v1_0.md` |
| Sprint 5 — Export Artifact + Provenance Handoff | `sprint_5_export_artifact_provenance_handoff_delivery_plan_v1_0.md` |
| Sprint 6 — Provenance Readout + History Endpoints | `sprint_6_provenance_readout_history_endpoints_delivery_plan_v1_0.md` |

### 2.3 Live working / reference / parked

| Document | Status | German (de/) | English (en/) |
|---|---|---|---|
| Dokument 1 | lebende Master | `dokument_1.md` | — |
| Dokument 2 | Arbeits-/Referenzdokument | `dokument_2.md` | — |
| Block 3 — Separate Volltext-Arbeitsstände | Arbeitsentwurf, kein Kanon | `block_3.md` | — |

The German-only set above (CAB, ITB, EEB, DBB, Dokument 1, Dokument 2, Block 3) is currently not translated. When precision matters or when the agent encounters technical terms it doesn't recognize, fall back to the German source. Future translation of any of these is fine but not blocking for current work.

---

## 3. Authorship of the sprint plans

The seven sprint plans were authored 2026-05-01 in this Claude session as canonical replacements per option (c) — the user's decision when the originally-frozen Sprint-0 through Sprint-6 plans v1.0 (referenced in `Dokument 2 §1` and `Baseline Delivery Plan §1`) were determined to be unrecoverable.

The plans are anchored to converging canonical sources: `Baseline Delivery Plan v1.0 §2` (sprint-level scope), `Delivery Backlog Baseline v1.0` ticket definitions, hard-gate list, and severity classification, plus structural guidance from `OCR-Export Endfassung v1.3 §5 Sprint Plan Sprint-OCR v1.3` (the only fully-written canonical sprint-document template). Each plan's header documents its specific anchor set.

**Implication for `Dokument 2 §1`.** Dokument 2 §1 lists "Sprint-0 bis Sprint-6 Pläne v1.0" among the eingefroren canonical documents. As of canonization, that entry refers to the 2026-05-01-authored replacements. A one-line amendment to Dokument 2 §1 should make this explicit so future readers see the reauthoring decision rather than treating the v1.0 plans as the unambiguous originals. Until that amendment lands, this README serves as the provenance record.

---

## 4. Where to look — common questions

| Question | First stop |
|---|---|
| Ticket scope, acceptance criteria, dependencies, risks | `delivery_backlog_baseline_v1_0.md` (DBB), indexed by ticket ID |
| Sprint-level scope, gates, mandatory tests, what's deliberately not in scope | The relevant `sprint_N_*.md` |
| H-1 through H-7 invariant detail | `core_architecture_baseline_v1_0.md` (CAB) §B |
| Audit rule A-XX/B-XX/C-XX/D-XX semantics | `implementation_translation_baseline_v1_0.md` (ITB) |
| Consistency rule K-XX semantics | ITB |
| Preflight gate P-XX/W-XX semantics, Konfigurations- vs Gate-Prüfungsschicht | ITB + `dokument_1.md` §4.7–§4.9 |
| `decision_source` enum (10 canonical values) | `dokument_1.md` §4.10 |
| `scope_type` enum + extension logic (segment/page/block/account/project) | CAB §B.1 + `dokument_2.md` §3.2 Eintrag 2D |
| Qurʾān-Stelle handling, kanonisch | `dokument_1.md` §4.15 |
| Qurʾān technical access spec | `block_3.md` Q4-1 to Q4-9 (working draft) |
| Hadith-Verifikationsstatus, Mehrquellen-Datenmodell, kanonisch | `dokument_1.md` §4.16 |
| Hadith technical access spec | `block_3.md` H5-1 to H5-12 (working draft) |
| Stilfeature canon | `dokument_1.md` §4.12–§4.14 + `dokument_b_v1_2_erkenne_meinen_uebersetzungsstil.md` |
| Stilfeature integration boundaries and deferrals | `dokument_c_v1_1_integrationsnachricht.md` |
| Format/layout, Word output, RTL | `formatvorlagen_baseline_v1_1.md` |
| Definition of Done | `engineering_execution_baseline_v1_0.md` (EEB) |
| OCR-Export specifics | `ocr_text_export_v1_3.md` |
| Currently open work, parked items, gebundene Resthinweise | `dokument_2.md` §3 (especially §3.2) |

---

## 5. Reading conventions used throughout the canon

- "§4.X" without document name = Dokument 1.
- "T-X.Y.Z" = ticket ID, defined in DBB.
- "H-1" through "H-7" (in architecture context) = core architecture invariants.
- "H-0" / "H-1" / "H-2" (in Hadith context) = Verifikationsklassen per `dokument_1.md` §4.16. Context disambiguates from architecture H-X.
- "P-XX" / "W-XX" = preflight gate slots.
- "K-01" through "K-07" = consistency rules.
- "A-01" through "D-03" = audit rules.
- "F-01" through "F-09" = OCR error classes.
- "N-1" through "N-10" = Hadith-Stellentypen per §4.16.
- "V-0/V-1/V-2" = Vokalisierungs-Eskalationsklassen per §4.16.
- "F1" through "F5" = Stilfeature backlog ticket families per CR-3, per DBB §7.

---

## 6. Cross-document references

When documents disagree, the precedence order is:

1. v1.0 baselines (CAB, ITB, EEB, DBB, OCR-Export v1.3, Formatvorlagen v1.1, Dokument A, B v1.2, C v1.1, Sprint plans v1.0, Baseline Delivery Plan v1.0) — on points where they specifically froze something.
2. Dokument 1 — on everything else.
3. Dokument 2 — for process state (open/parked/decided); not for content canon.
4. Block 3 — preserved working material; not authoritative.

If you can't tell whether a baseline "specifically froze" a point, surface the question to the user rather than guessing.

---

## 7. See also

- `/CLAUDE.md` (project root) — agent briefing with hard rules and discipline conventions.
- `dokument_2.md` §3 — current open-and-parked-items list, authoritative for process state.
- `dokument_2.md` §8 — Verifikationsblock, useful as a quick canonical-position check across major topics.

---

## 8. Maintenance

Update this README when canon shifts:

- New baseline frozen → add to §2.1.
- CR accepted that adds, removes, or renames a document → update §2.
- Working draft canonized → move from §2.3 to §2.1 or §2.2.
- Parked item resumed → update §2.3 status; surface in `dokument_2.md` §4.3 as well.
- Sprint plan reauthoring or amendment → update §3, **and** apply the change to both `en/Sprint-plan/<file>.md` and `de/Sprint-plan/<file>.md` to keep them byte-identical (per §2.2 mirror rule).
- Translation added (a German-only doc gets an English version) → update §2 entry's English column.
- `.docx` source updated in `de/` → regenerate the corresponding `de/*.md` via pandoc and refresh the provenance header (date, source filename). See "Format within `de/`" in the intro for the conversion contract.
- New canonical `.docx` added to `de/` → generate the matching `.md`, add the row to §2, regenerate provenance header.

Treat outdated README as a discipline failure parallel to outdated CLAUDE.md. Inventory drift in this file makes the canon set harder to navigate, which makes canon discipline harder to enforce.

— End of README.md —