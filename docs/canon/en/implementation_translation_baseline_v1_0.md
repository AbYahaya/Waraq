<!-- Source: Google Drive doc 1Q6imQm03ylfmMzuJbB_LAh-aao7D5Eo3bLkyJJc2VqQ (Implementation Translation Baseline v1.0) -->
<!-- Note: this is the canonical source for §4.6 audit matrix A-01...D-03 and is required for B-11 (Audit + Consistency layer). The agent's Phase-1 list omitted it; bring it in alongside the other six. -->

# WARAQ IMPLEMENTATION TRANSLATION BASELINE v1.0

## 1. Purpose and standing of this baseline

The Implementation Translation Baseline v1.0 describes the technical realization of the translation and check paths within Waraq. It is one of the frozen baselines and is explicitly listed as such in Document 1 §3.2. It is in particular the authoritative source for the full category definitions and classification of the audit categories A-01 through D-03 per Document 1 §4.6.

The core function of this baseline is:

- the binding definition of audit rules A-01 through D-03 with class, severity, and consequence,
- the technical placement of the audit and rule engine as a multi-layer model,
- the binding list of locked actions at the backend level,
- the list of decision gates that must not continue without active user acknowledgment.

## 2. Export preflight (§3.7)

### 2.1 Preflight states

`nicht_gestartet → läuft → exportierbar | exportierbar_mit_warnungen | blockiert`

`exportierbar_mit_warnungen` may be reached only after active confirmation of open warnings by the user (`go_with_warning`, canonical in §4.9 E-1 with double warning).

### 2.2 Preflight layer model

**Layer 1 — Configuration obligations.** The four required questions form an independent configuration layer. They demand necessary export parameters and check no finding in the document. They occupy no P slot automatically. Four required questions: (1) heading level header, (2) heading level chapter break, (3) TOC position front/back, (4) display Arabic chapter headings in body yes/no. PDF additionally: digital (RGB) or print (PDF/X-1a, CMYK, 3 mm bleed).

**Layer 2 — Gate checks.** Blocking P gates and warning-based W gates check facts in the document or in the export state.

### 2.3 Guard-near blockings before preflight

Before the preflight dialog is opened, the following states are checked guard-near. If a violation is present, the preflight dialog does not open. None of these blockings occupies a P slot.

- Digit standard violations: blocking, direct system mechanism.
- Critical RTL encoding/application errors: blocking as integrity violation.
- Document-style integrity violations: blocking; resolution requires technical removal.
- Critical font availability: blocking; resolution requires technical restoration; mere user confirmation does not suffice.

### 2.4 Occupied gates in the gate-check layer

- **P-03** — Critical audit violations (C-01, D-03) resolved individually. Independent blocking gate, structurally peer to P-04.
- **P-04** — High audit violations decided individually and actively.
- **W-01** — Medium audit violations (A-02, A-03, B-03, B-04, D-01, D-02) as notices.
- **W-02** — K-01 through K-07 consistency warnings.
- **W-03** — Gradual document-style deviations.
- **Hadith verification status group** — own named group within the gate-check layer. H-2 blocking (resolution via the seven canonized action types per §4.16). H-1 warning-based (`go_with_warning`, `decision_source = preflight_confirmation`). H-0 generates no group entry.

### 2.5 Open gate slots

P-01, P-02, P-05, P-06: no clean candidates. Slots open.
W-04 through W-08: no clean candidates. Slots open, no directional binding.

### 2.6 Forbidden transitions

- Export without active confirmation of all four required questions is not permitted.
- Mandatory notices (High violations) must not pass through as a general warning. P-04 blocking, decided individually.
- Template value not pushed through without active confirmation by user rule.

## 3. Audit and rule engine as technical layer (§4)

### 3.1 Layer model

**Layer 1 — Invariant guard (INVARIANT module).** Checks H-1 through H-7 before every operation. Binary decision: permitted / blocked. Generates no findings, no UI messages. Cannot be deactivated or overridden by anything.

**Layer 2 — Findings engine (AUDIT module + CONSISTENCY module).** Checks audit rules A-01 through D-03 and consistency rules K-01 through K-07. Delivers findings: Segment-UUID, rule label, violation class, severity. Makes no decisions. Generates no Revisions and no Decision-Event UUIDs.

**Layer 3 — Decision-gate layer (PREFLIGHT module).** Aggregates findings from Layer 2. Classifies as blocking (Critical, mandatory notice) and non-blocking (warning). Provides resolution options. Generates Decision-Event-UUIDs after user decision via the REVISION module, per the `decision_source` enum (§4.10) and the query rule `active_decision_event_uuids[]` (§4.11). Carries the preflight layer model and the hadith verification status group.

**Layer 4 — UI reporting layer.** Pure display. No own logic.

### 3.2 Separation rule

No layer may take on the tasks of another.

## 4. Audit rules A-01 through D-03

### 4.1 Founding principle

No overall score. Per-segment check. Audit runs in parallel with translation output. Does not stop the translation flow. Ignoring is logged as `decision_event` with `decision_source = audit_resolution`, decision = ignored.

### 4.2 Registry types and binding levels

- Terminology registry and glossary → violation of G-2 → Critical.
- Religious formulas registry → violation of G-3 → Critical.

D-03 is thereby upgraded from High to Critical.

### 4.3 Category A — Particle fidelity

**A-01 — إِنَّ / أَنَّ not transferred.** إِنَّ as emphatic introduction, أَنَّ as `dass`-introduction. Severity: High — mandatory notice.

**A-02 — لَ (emphasis) not transferred as emphasis.** With "wahrlich" or "fürwahr". Severity: Medium — notice.

**A-03 — فَ not transferred context-sensitively.** Context-sensitively with "so", "dann", or a consecutive conjunction. Severity: Medium — notice.

**A-04 — أَمَّا...فَ construction not fully transferred.** As "Was … betrifft, so". Severity: High — mandatory notice.

### 4.4 Category B — Structural fidelity

**B-01 — Idāfa too freely resolved.** Word-faithful, not paraphrased. Severity: High — mandatory notice.

**B-02 — Dual not visible.** Arabic dual must be explicitly recognizable as dual. Severity: High — mandatory notice.

**B-03 — Gender difference not transferred.** When semantically relevant and transferable. Severity: Medium — notice.

**B-04 — Conditional clause not text-near.** Text-near and word-faithful. Severity: Medium — notice.

### 4.5 Category C — Terminology and citations

**C-01 — Terminology entry violated.** Term transferred exactly per entry. Severity: Critical. Location blocked. Resolution: correction per entry, local exception with reason, or confirmed rule adjustment.

**C-02 — Islamic technical term without first-occurrence handling.** First occurrence = German technical translation + Arabic original in parentheses + footnote. Severity: High — mandatory notice.

**C-03 — Translator addition not marked.** Footnote `[Ü.]`. Severity: High — mandatory notice.

### 4.6 Category D — Stylistics and rhetoric

**D-01 — Metaphor or idiom not literal with footnote.** Footnote `[Ü.]`. Severity: Medium — notice.

**D-02 — Sajʿ without note in footnote.** Footnote "Im arabischen Original als Sajʿ (Reimprosa) formuliert". Severity: Medium — notice.

**D-03 — Religious formula violates registry.** Severity: Critical (upgraded per §4.2). Resolution: correction per registry, local exception with reason, or adjustment of the registry entry.

### 4.6a Style-feature violations (CR-2)

Extension of the A-01–D-03 audit matrix by style-feature violations along the concepts canonized in Document 1 §4.12, §4.14, and §5.3. The violations are placed in the existing tripartite division of violation classes (§4.7) and carry the structurally analogous gate effect per Document 1 §4.7.

**Critical-class violations (style feature):**

- Precedence-logic violation: a style-rule application violates a system rule per Document 1 §4.12. Severity: Critical. Effect: blocking, P-03 structurally analogous.
- Application of a style rule with status `vom_nutzer_gesperrt` per Document 1 §4.14. Severity: Critical. Effect: blocking, P-03 structurally analogous.

**High-class violation (style feature):**

- Violation of a PF-12 negative-list rule per Document 1 §5.3. Severity: High — mandatory notice. Effect: P-04 structurally analogous. Decided actively per location before export.

**Medium-class violation (style feature):**

- Violation of an active style rule without precedence-logic relation and without PF-12 relation. Severity: Medium — notice. Effect: W-01 structurally analogous (`go_with_warning`).

### 4.7 Violation classes — full tripartite division

- **Critical** = registry violation; style-feature Critical violations (precedence-logic violation, application of a `vom_nutzer_gesperrt` style rule). Location blocked. P-03 / P-03 structurally analogous.
- **High — mandatory notice** = decided actively per location; style-feature High (PF-12). P-04 / P-04 structurally analogous.
- **Medium — notice** = export with warning possible; style-feature Medium. W-01 / W-01 structurally analogous.

## 5. Locked actions (§6.2)

The backend enforces these locks. UI check alone is not sufficient.

| Action | Locked when |
|---|---|
| Translation start | Release gate not on `übersetzungsreif` / `übersetzbar_mit_warnung` with confirmation |
| Export | Preflight not on `exportierbar` / `exportierbar_mit_warnungen` with confirmation |
| Export | Four required questions not actively answered |
| Automatic segment change | Segment has active lock flag |
| Automatic conflict resolution | Lock flag conflict detected |
| Promotion to style rule | Without three-stage pipeline and user confirmation |
| Lifting of Lock Level 2 | Without confirmation dialog with clear-text warning |

Additionally: export with open H-2 hadith locations blocked; export on guard-near violations — preflight dialog does not open at all.

## 6. Explicitly acknowledgment-required decision gates (§6.3)

- Release gate (OCR review → translation).
- Four required questions before export (configuration layer).
- Each Critical audit violation individually (C-01, D-03) — P-03.
- Each mandatory notice (High violation) individually — P-04.
- Lock flag conflict (H-6).
- F-06-QR block without resolution (§4.9 E-1).
- V-2 vocalization conflict per §4.16 (`decision_source = conflict_resolution`).
- Hadith location decision (hadith verification status group). H-2 blocking, H-1 warning-based.
- Promotion-pipeline Stage 3 (pattern candidate → style rule) per §5.6.
- Export with warnings (`go_with_warning`, double warning, W-01/W-02/W-03 + H-1).
- Qurʾān location handling per §4.15.
- Style profile decisions (`decision_source = style_management`).
- Glossary entries (`decision_source = glossary_management`).
- Consistency-group resolution (`decision_source = consistency_resolution`).

## 7. Linkage to the canonical decision_source enum

Ten non-overlapping values: `ocr_review`, `lock_management`, `conflict_resolution`, `glossary_management`, `export_confirmation`, `preflight_confirmation`, `translation_pipeline`, `audit_resolution`, `consistency_resolution`, `style_management`. Query rule `active_decision_event_uuids[]` deterministically defined in Document 1 §4.11.

## 8. Demarcation from other baselines

This baseline does not define: H-1…H-7, G-1…G-4, core objects/identities, protection model, revision model, promotion pipeline (→ CAB v1.0); P/W gate definitions and K-01…K-07 (→ EEB v1.0); OCR Text Export Final Version v1.3; Formatvorlagen Baseline v1.1; style-feature detail (Doc A v1.0, Doc B v1.2, Doc C v1.1).

## 9. Open points

1. Original sections §1, §2, §3.1–§3.6, §5, §6.1, §7 not substantively elaborated; only §3.7 / §4 / §6.2 / §6.3 present.
2. Detail rules of audit-module implementation outside the layer model.
3. Full conflict typology A–F (only F via §4.16 V-2 and B Case 4 via §4.16 hadith verification status are partially picked up).
4. Full P/W slot specification (see EEB §13).
5. Internal flow detail of REVISION/EVENTING.
6. Detail flows of the invariant guard.

— End of version —