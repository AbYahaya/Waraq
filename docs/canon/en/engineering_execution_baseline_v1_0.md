<!-- Source: Google Drive doc 1roVgbaMvW_8MKLx1W7F3Qgywwc36XlrRhNGuZ6kO5v4 (Engineering Execution Baseline v1.0) -->

# WARAQ ENGINEERING EXECUTION BASELINE v1.0

## 1. Purpose and scope

The Waraq Engineering Execution Baseline v1.0 describes, in Waraq, the technical realization of the export preflight logic, the gate checks, the work-wide consistency check, and the guard-near integrity safeguarding. It is listed in Document 1 §3.2 as a frozen baseline. Document 1 §4.7 and §4.8 explicitly refer to it as the authoritative source for the full definitions of the export preflight gates P-01 through P-06 / W-01 through W-08 and the work-wide consistency check K-01 through K-07.

This baseline covers:

- the preflight layer model,
- the guard-near prechecks before the preflight dialog,
- the occupancy of the P and W slots within the gate-check layer,
- the placement of the hadith verification status group,
- the structural placement of the consistency rules K-01 through K-07,
- the interplay with §4.6 (translation audit), §4.7 (export preflight), §4.8 (consistency check), and §4.16 (hadith handling),
- the link to the `decision_source` enum and the query rule `active_decision_event_uuids[]`.

Not part of this baseline and listed as open points in §13:

- the substantive single-rule definitions of K-01 through K-07,
- the substantive single definitions of P-01 through P-06 / W-01 through W-08 beyond the occupancies established here,
- the audit rules A-01 through D-03 (in the Implementation Translation Baseline),
- the hard invariants H-1 through H-7 and the Governable Rules G-1 through G-4 (in the Core Architecture Baseline).

## 2. Preflight layer model

The export preflight dialog contains two conceptually independent layers. This layer model is canonically confirmed in Document 1 §4.7.

### 2.1 Layer 1 — Configuration obligations

The four required questions form an independent configuration layer in the preflight dialog. They demand necessary export parameters and check no finding in the document. They occupy no P slot automatically.

The four required questions read:

1. Which heading level should be displayed in the header?
2. Which heading level marks chapter breaks?
3. Position of the table of contents (front / back)?
4. Display Arabic chapter headings in the body (yes / no)?

Additionally for PDF export: choice between digital (RGB) and print (PDF/X-1a, CMYK, 3 mm bleed).

Export must not continue without active confirmation of all four required questions. The confirmation formally occupies no P slot.

### 2.2 Layer 2 — Gate checks

Blocking P gates and warning-based W gates check facts in the document or in the export state against defined conditions. The concretely occupied gates are in §4.

### 2.3 Demarcation of the two layers

The configuration layer refers exclusively to parameters that the user sets before export. It does not replace a gate check and is not replaced by a gate check. The gate-check layer refers exclusively to findings in the document or to the export state itself.

## 3. Guard-near prechecks before the preflight dialog

Before the preflight dialog is opened, the system performs guard-near blockings. These are blocking and operate outside the preflight gate logic. None of these blockings occupies a P slot. Basis: Document 1 §4.7.

### 3.1 Digit standard

Western digits are to be used everywhere, never Arabic digits. Violations of the digit standard are handled guard-near and are blocking. No audit case, no user judgment — direct system mechanism. The check happens before the preflight dialog.

### 3.2 Critical RTL encoding / RTL application errors

Critical errors in RTL encoding or RTL application are handled guard-near as integrity violations and are blocking. The check happens before the preflight dialog.

### 3.3 Document-style integrity violations

Integrity violations of the document styles are handled guard-near and are blocking. The check happens immediately before opening the preflight dialog. If a violation is present, the preflight dialog does not open. Resolution requires technical removal of the violation. A mere user confirmation does not suffice.

### 3.4 Critical font availability

Critical are the four fonts named in the Formatvorlagen Baseline v1.1:

- KFGQPC Uthmanic Script HAFS (Quran_AR)
- Traditional Naskh (Hadith_AR, Zitat_AR, Titel_AR, Titel_AR_Untertitel)
- Noto Sans Arabic (UeberschriftAR_1–6, Begriff_AR, FussN_AR)
- Calibri (Body_DE, Titel_DE, Heading 1–6, FN_Uebersetzer, FN_Herausgeber, FN_Verlag)

If one of these four fonts is missing, the preflight dialog does not open. Resolution requires technical restoration of the font; mere user confirmation does not suffice. No silent fallback to a substitute font. No P slot occupied.

### 3.5 Not guard-near, but warning-based

Gradual document-style deviations are not guard-near, but warning-based. They reach the preflight dialog and occupy W-03 (see §4.5).

## 4. Occupied and open P/W slots

Basis: Document 1 §4.7.

### 4.1 P-03 — Critical audit violations

P-03 is an independent blocking gate in the gate-check layer, structurally peer to P-04. P-03 occupies the resolution of critical audit violations per §4.6:

- C-01 — Terminology entry violated (violation of G-2).
- D-03 — Religious formula violates registry (violation of G-3).

The location stays blocked until resolved. Ignoring is not possible.

### 4.2 P-04 — High audit findings

P-04 occupies the resolution of High audit violations (mandatory notices) per §4.6:

- A-01 — إِنَّ / أَنَّ not transferred.
- A-04 — أَمَّا...فَ construction not fully transferred.
- B-01 — Idāfa too freely resolved.
- B-02 — Dual not visible.
- C-02 — Islamic technical term without first-occurrence handling.
- C-03 — Translator addition not marked.

Each affected location must be decided actively before export. An ignore is logged as `decision_event` with `decision_source = audit_resolution`.

### 4.3 W-01 — Medium audit findings

W-01 occupies the Medium audit notices per §4.6:

- A-02 — لَ (emphasis) not transferred as emphasis.
- A-03 — فَ not transferred context-sensitively.
- B-03 — Gender difference not transferred.
- B-04 — Conditional clause not text-near.
- D-01 — Metaphor or idiom not literal with footnote.
- D-02 — Sajʿ without note in footnote.

Export with warning possible (`go_with_warning` analogous to §4.9 E-1, double warning). Logging takes place.

### 4.4 W-02 — Consistency warnings K-01 through K-07

W-02 occupies the work-wide consistency warnings K-01 through K-07 from §4.8. These are not export-blocking. They generate warnings. Export with warning possible.

Exception: if a K violation simultaneously violates a Critical class per §4.6, the audit gate (P-03) applies, not W-02.

The substantive single definitions of K-01 through K-07 are listed as an open point in §13.

### 4.5 W-03 — Gradual document-style deviations

W-03 occupies the gradual document-style deviations. Not to be confused with document-style integrity violations, which are guard-near and blocking (§3.3). Gradual deviations reach the preflight dialog and are warning-based.

### 4.6 Hadith verification status — own named group

The hadith verification status forms its own named group within the gate-check layer per §4.7 and §4.16. The group is not a new layer. It occupies neither of the open P or W slots. It carries two state classes:

- **H-2 blocking:** location not exportable as long as H-2 remains. Resolution exclusively via the seven canonized action types in §4.16.
- **H-1 warning-based:** location exportable with `go_with_warning` confirmation, consistent with §4.9 E-1. `decision_source = preflight_confirmation` per §4.10.

H-0 locations generate no group entry.

The gate effect of the group is led slot-independently. A later formal occupancy of open P/W slots remains possible without silently changing this canon.

The relation to §4.16 (location types N-1 through N-10, verification classes H-0 / H-1 / H-2, vocalization classes V-0 / V-1 / V-2) is deepened in §6.

### 4.7 Open P slots

P-01, P-02, P-05, P-06 are open. In the existing canon of the publication export, no clean candidates are currently identifiable. The slots remain open for now.

The occupancy logic: free P slots are occupied exclusively with blocking states already established in the existing canon. The hadith verification status does not occupy these slots, even though H-2 is blocking (see §4.6).

### 4.8 Open W slots

W-04 through W-08 are open. In the existing canon of the publication export, no further clean candidates are currently identifiable. No directional binding is anticipated. No new warning-based states are introduced.

## 5. Relation to §4.6, §4.7, §4.8, §4.16

### 5.1 §4.6 — Translation audit

The audit rules A-01 through D-03 are divided into three classes: Critical, High, Medium. The classes feed the preflight gates:

- Critical → P-03 (blocking, ignore not possible).
- High → P-04 (mandatory notice, individual decision per location).
- Medium → W-01 (notice, export with warning possible).

Audit findings do not stop the translation flow. They are persisted and carried into the preflight logic.

Violations of document styles, RTL encoding / RTL application, and the digit standard are not part of the audit branch. They are handled guard-near (§3). The style feature is strictly separate.

### 5.2 §4.7 — Export preflight

§4.7 is the canonical source for the preflight layer model (§2), the guard-near prechecks (§3), and the gate occupancy (§4). The gate-check layer contains the occupied P and W gates and the named hadith verification status group.

### 5.3 §4.8 — Work-wide consistency check

K-01 through K-07 are not export-blocking. They generate warnings and are placed as W-02 (§4.4). Exception: if a K violation simultaneously violates a Critical class per §4.6, the audit gate (P-03) applies. Gradual document-style deviations are W-03, not part of §4.8.

### 5.4 §4.16 — Hadith handling

§4.16 defines the location types N-1 through N-10, verification classes H-0 / H-1 / H-2, vocalization classes V-0 / V-1 / V-2, and the seven canonized action types. The mapping of these states to the preflight runs via the named group "hadith verification status" per §4.7 and §4.6 of this document. The hadith verification status is not an audit case per §4.6. It is its own state with its own gate effect.

## 6. Hadith verification status — detailed placement

### 6.1 Location types N-1 through N-10

Each hadith location receives a location type after completion of multi-source verification and after each subsequent user interaction:

- N-1: fully verified and automatically accepted.
- N-2: verified with logging-required residual finding.
- N-3: verified with active user decision.
- N-4: unresolved, actively "marked for later clarification" by user.
- N-5: total verification failure without user decision.
- N-6: author-source conflict unresolved.
- N-7: no hit, no decision.
- N-8: V-2 vocalization conflict unresolved.
- N-9: "treated as not a hadith".
- N-10: "proceed without verification" explicitly chosen.

### 6.2 Mapping to verification classes

- **H-0** (review-internally tolerable, not export-blocking): N-1, N-3, N-9.
- **H-1** (logging-required, not export-blocking, warning-capable): N-2, N-10.
- **H-2** (export-blocking until resolution): N-4, N-5, N-6, N-7, N-8.

### 6.3 Resolution of H-2

Resolution of H-2 happens exclusively via the seven canonized action types in §4.16:

1. Take verified version instead of author wording → `translation_pipeline`.
2. Choose full text instead of short version → `translation_pipeline`.
3. Keep author wording despite conflict → `conflict_resolution`.
4. Change source citation / deliberately not change → `conflict_resolution`.
5. Proceed without robust external verification → `conflict_resolution`.
6. Treat location as not a hadith → `conflict_resolution`.
7. Decide vocalization conflict manually → `conflict_resolution`.

The marker "for later clarification" is not a `decision_event` and does not lift H-2.

### 6.4 Vocalization escalation criterion

- V-0 is automatically tolerable and triggers no location-log entry.
- V-1 is logging-required but triggers no escalation.
- V-2 is escalation-required, no automatic acceptance, active user resolution per the seven canonized action types with `decision_source = conflict_resolution`.

Aggregation rule: with multiple deviations in one location, the highest occurring class applies (V-0 < V-1 < V-2). Fallback rule: on uncertainty, the higher class is applied.

The field `vokalisierungs_konflikt` is strictly binary (no / yes). The class differentiation runs exclusively via the derived `vokalisierungsklasse`.

## 7. Consistency rules K-01 through K-07 — structural placement

### 7.1 Placement

K-01 through K-07 are laid out in Document 1 §4.8 as work-wide consistency checks. They are not export-blocking and generate warnings. Their preflight placement is W-02 (§4.4).

### 7.2 Exception

If a K violation simultaneously violates a Critical class per §4.6, the audit gate P-03 applies, not W-02. This exception follows directly from the peer status of P-03 as an independent blocking gate.

### 7.3 Content of the K rules

The substantive single definitions of K-01 through K-07 are listed as an open point in §13.

## 8. Link to the decision_source enum and the query rule

### 8.1 decision_source

The preflight logic generates Decision-Event-UUIDs after user decisions. The `decision_source` values are chosen from the ten-value, non-overlapping enum canonized in Document 1 §4.10: `ocr_review`, `lock_management`, `conflict_resolution`, `glossary_management`, `export_confirmation`, `preflight_confirmation`, `translation_pipeline`, `audit_resolution`, `consistency_resolution`, `style_management`.

Particularly relevant for preflight/gate operationalization:

- **export_confirmation** — only for OCR-export required questions.
- **preflight_confirmation** — only for the final publication export. Carries in particular the H-1 confirmations of the hadith verification status group per §4.16.
- **audit_resolution** — for audit-finding resolutions (classes Critical / High / Medium).
- **consistency_resolution** — for consistency-group resolution.
- **conflict_resolution** — for conflict resolution, in particular for action types 3 through 7 of the hadith location and for V-2 vocalization conflicts.

### 8.2 active_decision_event_uuids[]

The query rule `active_decision_event_uuids[]` is deterministically defined in Document 1 §4.11 and is binding for the preflight module. It controls which decision events count as active at export and which are superseded by later decisions.

## 9. Interplay with export states

The preflight states move between `nicht_gestartet`, `läuft`, `exportierbar`, `exportierbar_mit_warnungen`, and `blockiert`. For operationalization:

- **exportierbar:** all P gates resolved, all guard-near blockings clean, no active H-2 location in the hadith group. Configuration layer fully confirmed.
- **exportierbar_mit_warnungen:** state reached when W gates carry open warnings (W-01 / W-02 / W-03) or H-1 locations are present. Export only after active `go_with_warning` confirmation.
- **blockiert:** at least one P gate unresolved or at least one H-2 location active or at least one guard-near blocking active.

The preflight dialog opens only when the guard-near blockings (§3) are clean. The configuration layer is dependent on active confirmation and does not replace a gate check.

## 10. Consolidated overview table

| Check stage | Type | Effect |
|---|---|---|
| Digit standard | Guard-near | blocking, system mechanism |
| RTL encoding/application critical | Guard-near | blocking, integrity violation |
| Document-style integrity | Guard-near | blocking, preflight dialog does not open |
| Critical font availability | Guard-near | blocking, preflight dialog does not open |
| 4 required questions | Configuration layer | no gate occupancy, active confirmation needed |
| P-01, P-02, P-05, P-06 | P gate | open |
| P-03 | P gate | blocking, C-01 / D-03 |
| P-04 | P gate | blocking, High audit (A-01, A-04, B-01, B-02, C-02, C-03) |
| W-01 | W gate | warning-based, Medium audit (A-02, A-03, B-03, B-04, D-01, D-02) |
| W-02 | W gate | warning-based, K-01 through K-07 |
| W-03 | W gate | warning-based, gradual document-style deviations |
| W-04 through W-08 | W gate | open |
| Hadith verification status | own group | H-2 blocking, H-1 warning-based, no slot occupancy |

## 11. Style-feature layers (CR-2)

Anchoring of the style-feature audit/conflict/display/learn layers per CR-2 along the concepts canonized in Document 1 §4.12, §4.13, §4.14, §5.3, and §5.6 and the marker/tooltip requirements documented in Document 2 §8.

The corresponding audit-violation classes for the style feature (Critical, High, Medium) are anchored in the Implementation Translation Baseline v1.0 (CR-2 / A.1, A.2, A.3); their P-03- or P-04- or W-01-structurally-analogous effect per Document 1 §4.7 is described there. This section anchors the supplementary layers exclusively assigned to EEB v1.0.

### 11.1 Conflict-detection layer (pre-filter)

Anchoring of a pre-filter inside the audit/gate layers of EEB v1.0 (layers per §2 and §4). The pre-filter checks, when applying a style rule, whether a system rule per Document 1 §4.12 would be violated. On hit, the status effect `unterdrückt_durch_systemregel` per Document 1 §4.14 is triggered. No persistence note is anchored at this point.

### 11.2 Marked open model question B.2 — schema model of conflict types

The schema model of the conflict types is explicitly open. Two model variants are in scope but not decided in this baseline:

- Model 1: extension of `conflict_instance` from T-5.1.2.
- Model 2: own object `stil_konflikt`.

Until the model decision, neither variant is led as anchored in EEB v1.0. The pre-filter from §11.1 runs logically independent of the later schema model. The model decision is part of a later baseline follow-up and is taken there.

### 11.3 §4.12 precedence logic as audit condition

Anchoring of the precedence logic per Document 1 §4.12 (Tier 1 system rules > Tier 2 user style > Tier 3 reference sentences) as an audit condition of the Critical-class style-feature violations from the Implementation Translation Baseline v1.0 (CR-2 / A.1). The subsequent audit effect supplements the pre-filter from §11.1 and triggers, on violation of the precedence hierarchy, at the audit level.

### 11.4 Display layer — style profile markers

Anchoring of style profile markers on the translation output segment: discreet underline in blue tone, hover tooltip with PF-XX label. Connection to `stil_regel_uuid` provenance (schema reference per CR-1 / 1.1). Display setting as account setting (deactivatable per Document 1 §4.14, account scope per CR-1 / 1.3). Shared display layer with the audit-violation markers of the style-feature violations from the Implementation Translation Baseline v1.0 (CR-2 / A.1, A.2, A.3).

### 11.5 Display layer — style-rule provenance in tooltip

Anchoring of the provenance display in the hover tooltip from §11.4: the source class from Document 1 §4.13 (which source class led to the rule) becomes visible as a confidence-value signal. Uses the `erstellt_aus` field on `stil_regel` (schema reference per CR-1 / 1.5).

### 11.6 §5.6 promotion-pipeline logic

Anchoring of the five §5.6 transitions as a logic layer:

- `kandidat → tendenz`;
- `tendenz → präferenz`;
- `präferenz ↔ invariant` (only by explicit user action [CANON]);
- `invariant → präferenz` (only by explicit user action [CANON]);
- any type → `vom_nutzer_gesperrt`.

Behavior-side reference to the `regeltyp` field (schema reference per CR-1 / 1.7) and the `status` field (schema reference per CR-1 / 1.6). No schema change is anchored at this point.

### 11.7 Learning logic layer — learning source asymmetry §4.13

Anchoring of the learning source asymmetry per Document 1 §4.13 as input condition for the promotion transitions from §11.6:

- confirmed reference sentences and manual user rules as upgrade signal;
- accepted AI suggestions as a weak reinforcement signal;
- corrected AI suggestions as a counter-signal (no reinforcement, no upgrade);
- ignored AI suggestions as a null signal.

The learning logic layer feeds the transitions from §11.6.

### 11.8 Test family definition (DoD anchor)

Substantive definition of five style-feature test families:

- Correction-signal tests: check the counter-signal behavior of corrected AI suggestions per Document 1 §4.13 and §11.7.
- Upgrade tests: check the §5.6 transitions from §11.6.
- Conflict tests against precedence logic §4.12: check §11.1 and §11.3.
- PF-12 tests: check the High-class style-feature violations from the Implementation Translation Baseline v1.0 (CR-2 / A.2).
- Status-transition tests: check the effects of the conflict mechanism from §11.1 on the `status` field.

Binding of the test families to the respective architectural layers as audit/learning verification.

## 12. Demarcation — what is operationalized and what is not

**Operationalized and occupied:**

- Preflight layer model (configuration obligations + gate checks).
- Four required questions as configuration layer.
- Guard-near prechecks for digit standard, RTL, document-style integrity, critical font availability.
- Occupancy P-03 / P-04.
- Occupancy W-01 / W-02 / W-03.
- Hadith verification status group as own named group with H-0 / H-1 / H-2.
- Mapping of audit classes to P-03 / P-04 / W-01.
- Exception: K violation with Critical class hits the audit gate P-03.
- Occupancy logic for free P slots (only blocking states established in canon).
- `decision_source` mapping for preflight and audit decisions.
- Query rule `active_decision_event_uuids[]` as binding component of the preflight logic.
- Conflict-detection layer (pre-filter) for style rules (§11.1).
- §4.12 precedence logic as audit condition (§11.3).
- Display/provenance layer for style profile — markers and style-rule provenance in tooltip (§11.4 / §11.5).
- §5.6 promotion-pipeline logic (§11.6).
- Learning-logic layer — learning source asymmetry §4.13 (§11.7).
- Test family definition (DoD anchor) for the style feature (§11.8).

**Not operationalized, still open:**

- Substantive occupancy of slots P-01, P-02, P-05, P-06.
- Substantive occupancy of slots W-04 through W-08.
- Substantive single definitions of K-01 through K-07.
- Schema model of conflict types (model question B.2, marked open in §11.2).
- Persistence decision for the pre-filter from §11.1.

## 13. Open points

The following points are not finally specified in this baseline and are explicitly led as open:

1. Substantive single definitions K-01 through K-07 of the work-wide consistency check.
2. Substantive occupancy of the open P slots P-01, P-02, P-05, P-06.
3. Substantive occupancy of the open W slots W-04 through W-08.
4. Structural relation between Engineering Execution Baseline v1.0 and Implementation Translation Baseline v1.0 with regard to preflight responsibility. Document 1 §4.7 refers to the Engineering Execution Baseline, while parts of the preflight gate semantics are also found in the Implementation Translation Baseline. A clean dividing line is not finally drawn.
5. Internal detail flows of the PREFLIGHT module, the REVISION module, and the EVENTING module beyond the known layer structure from the Implementation Translation Baseline.
6. Schema model of the conflict types in the style feature (model question B.2 per §11.2): Model 1 (extension of `conflict_instance` from T-5.1.2) versus Model 2 (own object `stil_konflikt`). Model decision pending.
7. Persistence decision for the pre-filter from §11.1.

— End of version —