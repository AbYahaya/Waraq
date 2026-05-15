<!-- Source: Google Drive doc 1Bd4lys9KyVQ6FNUM0b6inODb00cnHO8Tm42iRHWFkkM (Dokument B v1.2 — Erkenne meinen Übersetzungsstil) -->
<!-- Pulled: 2026-05-01. Place at /docs/canon/dokument_b_v1_2_erkenne_meinen_uebersetzungsstil.md -->

# WARAQ — DOKUMENT B v1.2

## Structured feature specification: "Recognize my translation style"

Basis: Dokument A (Canonical user-style corpus v1.0)

No code. No coding release. No silent re-baselining. No new feature broadening. This document does not replace any existing baseline, any handover folder, or any general system rule.

## PRECEDENCE LOGIC (CENTRAL — UNCHANGEABLE)

In every conflict the following order holds. It is not altered anywhere in this document:

1. **Already-released general system rules (Dokument 1 and Baselines v1.0)**
   - Transliteration (EI2 with Q/J adjustment)
   - Glossary (precedence over everything; never automatically overwritable)
   - Terminology index
   - Religious-formulas index
   - Qurʾān reference handling per §4.15 (Arabic Qurʾān reference stock for Arabic reference text and vocalization; quranenc.com or local fallback copy for target-language translations)
   - Hadith handling (verification-source hierarchy)
   - Specialist-term handling (first occurrence / subsequent occurrence)
   - All other canonical standards from Dokument 1 and Baselines v1.0
2. **Canonical user style (Dokument A / this feature)**
   - Hard style invariants (§4 in Dokument A)
   - Strong preferences (§5)
   - Structured style features (§6)
3. **Individual reference sentences (reference corpus from Dokument A)**
   - As structured bilingual style evidence
   - Not as silent replacement for system rules

If a reference sentence contains a spelling that contradicts a system rule:

- the system rule has precedence
- the reference sentence remains stylistically authoritative
- the concrete spelling is adapted to the canonical system rule

## READING AID: MARKERS IN THIS DOCUMENT

Every rule in this document carries one of the following markers:

| Marker | Meaning |
|---|---|
| [KANON] | Hard canonical rule — unchangeable, no discretion |
| [KONFIG] | Product-configurable — product decision, but not changeable by learning logic |
| [KALIB] | Calibratable — threshold not yet fixed; to be determined after gold-corpus tests |

## 1. PURPOSE OF THE FEATURE

### 1.1 Core purpose [KANON]

The feature enables the system to learn the individual translation style of a particular user from confirmed bilingual translation pairs in structured form, and to take this style into account in future AI-supported translation suggestions.

### 1.2 Distinction from Option A [KANON]

Option A (AI standard) is always the starting point. The style feature is an additional layer that refines the AI standard user-specifically. It is not a replacement for Option A.

### 1.3 What the feature does not deliver

→ See §13 (explicit exclusions).

## 2. ACTIVATION LOGIC AND ENABLEMENT CONDITIONS

### 2.1 Account binding [KANON]

The style feature is exclusively and absolutely account-bound:

- user-specific — not global.
- not standard for new accounts — no auto-start.
- not transferable to other accounts — neither automatically nor manually.
- no sharing function planned for this feature.

A possible later sharing function for Stilprofile is not part of this feature and requires a separate CR cycle. It must not be carried over to this feature from the general subscription configuration frame.

### 2.2 Enablement conditions

Hard canonical conditions — always valid, independent of product configuration:

| Condition | Type | Value |
|---|---|---|
| Reference sentences are confirmed final versions | [KANON] | Yes — no drafts, no intermediate states |
| Reference sentences are bilingual (AR + DE) | [KANON] | Yes — both languages complete |
| Explicit activation by user | [KANON] | Mandatory — no auto-activation |
| Minimum number of confirmed reference-sentence pairs | [KALIB] | Not yet fixed |

Product-configurable conditions — product decision, not canon:

| Condition | Type | Note |
|---|---|---|
| Subscription enablement of the feature | [KONFIG] | Yes/No per subscription configuration |
| Permitted account classes | [KONFIG] | Product decision — which classes get access (e.g. Stage 1 / Stage 2); concrete account classes such as Guest, Applicant, Stage 1, Stage 2 are product configuration, not canon |

Important: which account classes concretely get access is product-configurable. Canonical is only that the feature is account-bound and requires explicit user activation. Statements such as "does not apply to Guest accounts" are product configuration, not a hard canonical rule.

### 2.3 Deactivation [KANON]

- The user can deactivate the Stilprofil at any time.
- Already-revised pages are not undone.
- The Stilprofil remains stored and can be reactivated.

## 3. PERMITTED DATA SOURCES AND LEARNING-SOURCE ASYMMETRY

### 3.1 Principle of learning-source asymmetry [KANON]

Not all sources may act on the Stilprofil with equal weight. The following asymmetry is hard canon and may not be overridden by any learning logic:

| Source | May ground new strong rules | May set invariants | May reinforce rules | May produce weak candidates | Signal on non-use |
|---|---|---|---|---|---|
| Confirmed reference sentences / final versions (bilingual) | Yes | No (only via user confirmation) | Yes | Yes | – |
| Manually entered user style rules | Yes | Yes — directly | Yes | Yes | – |
| Accepted AI suggestions | No | No | Yes (existing rules) | Yes (only weakly) | – |
| Corrected AI suggestions | No | No | No | No | Counter-signal / correction signal |
| Ignored AI suggestions | No | No | No | No | Null signal |

Explicit note on manual style rules [KANON]: manually entered user style rules are also fully subject to the precedence logic of this document. They may never overwrite or undermine system rules. If a manually entered style rule collides with a system rule (glossary, transliteration, terminology index, religious formulas, Qurʾān-verse handling, hadith verification logic), the system rule has precedence, the manual style rule moves to the status `unterdrückt_durch_systemregel`, and the user is informed. A manual style rule cannot override this precedence.

### 3.2 Refinement: what accepted AI suggestions may and may not do [KANON]

Accepted AI suggestions may:

- raise the confidence value of an entry already derived from reference sentences.
- produce a weak candidate (status: `in_prüfung`) that as yet has no rule effect.

Accepted AI suggestions may not:

- alone produce a strong preference rule.
- alone produce a hard invariant.
- undermine an existing system rule.
- weaken an existing hard invariant.

### 3.3 Correction signal [KANON]

If the user corrects an AI suggestion, this is a counter-signal:

- the affected style entry is lowered in confidence.
- if the same pattern is repeatedly corrected: entry placed on negative list (status: `vom_nutzer_gesperrt`).
- no automatic inversion without user confirmation.

### 3.4 Non-permitted sources [KANON]

These sources must under no circumstances flow into the Stilprofil:

- unconfirmed drafts or intermediate states.
- foreign user profiles / other accounts.
- ignored AI suggestions.
- glossary entries (system rule, not a style pattern).
- transliteration rules (system rule).
- religious-formulas index (system rule).
- Qurʾān-verse renderings via quranenc.com (external source).
- hadith texts (verification logic).
- vocalization corrections (separately stored, not a style pattern).

## 4. ANALYSIS AND ALIGNMENT LAYER (BILINGUAL)

### 4.1 Principle [KANON]

Style rules do not rest on a loose sentence-pair store. They rest on structured-extracted bilingual evidence following a defined alignment model. Every style rule must rest on at least one such structured Stilbeleg.

### 4.2 Structure of a bilingual Stilbeleg

Each Stilbeleg is a structured record with the following mandatory fields:

| Field | Type | Content |
|---|---|---|
| beleg_uuid | UUID | Unique ID of the Stilbeleg |
| account_uuid | UUID | Owning account (account binding, see §2.1) |
| arabisches_muster | Text | Arabic source pattern (word / construction / particle / phrase) |
| arabischer_kontext | Text | Arabic sentence context in which the pattern occurs |
| deutsche_wiedergabe | Text | Actual German rendering in the confirmed reference sentence |
| phänomenfeld | Enum | One of the 12 phenomenon fields (see §4.3) |
| belegtyp | Enum | `referenzsatz` / `endfassung` / `manuelle_regel` |
| regeltyp | Enum | `invariant` / `präferenz` / `tendenz` / `kandidat` |
| konfidenz | Float 0.0–1.0 | Current confidence |
| referenz_paar_uuid | UUID | Reference to the confirmed AR/DE pair as source |
| nutzer_bestätigt | Boolean | Whether this Stilbeleg was explicitly confirmed by the user |
| erstellt_at | Timestamp | |

The Stilbeleg references via `referenz_paar_uuid` the bilingual reference pair as provenance source. The reference pair is led as an independent object:

| Field | Type | Content |
|---|---|---|
| referenz_paar_uuid | UUID | Unique ID of the pair |
| account_uuid | UUID | Owning account |
| arabischer_text | Text | Arabic original |
| deutscher_text | Text | German final version (confirmed) |
| bestätigt_at | Timestamp | Time of user confirmation |

### 4.3 Phenomenon fields [KANON]

The phenomenon fields correspond to the areas defined in Dokument A §7:

| No. | Phenomenon field |
|---|---|
| PF-01 | Particle handling (وَ / فَ / ثُمَّ / بَل / إِنَّ / لَ etc.) |
| PF-02 | Sentence connection and repetition |
| PF-03 | Idāfa handling (genitive constructions) |
| PF-04 | Masdar / verb relation |
| PF-05 | Specialist equivalences |
| PF-06 | Handling of Qurʾān and Ḥadīṯ citations |
| PF-07 | Isnād / ḥadīṯ-critical specialist language |
| PF-08 | Parenthesis use |
| PF-09 | Religious-polemical terms |
| PF-10 | Juridical-contractual metaphor |
| PF-11 | Register height |
| PF-12 | Errors that must not happen again (negative list) |

### 4.4 Extraction of Stilbelege from reference-sentence pairs

When a new confirmed AR/DE reference pair is taken in, the following sequence runs:

1. System analyses the pair and proposes structured Stilbelege (per recognized phenomenon field, one or more entries).
2. User reviews the proposed Stilbelege and decides for each individually:
   - Confirm — Stilbeleg is taken over unchanged.
   - Reject — Stilbeleg is not taken in; no entry, no signal.
   - Take over precisified — user changes or precisifies the proposed Stilbeleg (e.g. Arabic pattern, German rendering, or phenomenon-field assignment) and then confirms the precisified version; the precisified version counts as the final form of the Stilbeleg.
3. Only confirmed or precisified-taken-over Stilbelege are taken into the alignment layer.
4. Taken-in Stilbelege raise the confidence of existing entries or create new entries.
5. A new Stilprofil version is created.

[KANON]: step 2 (user confirmation or precisification) is non-skippable. No Stilbeleg is taken in without an explicit user action. A rejected Stilbeleg produces no signal — not even a candidate.

### 4.5 Minimum evidence density per phenomenon field [KALIB]

Before a phenomenon-field pattern is classified as a preference rule, a minimum evidence density is required. Concrete thresholds: not yet fixed — to be calibrated after gold-corpus tests.

Fields with insufficient evidence density are shown to the user as "not yet sufficiently learned".

## 5. STRUCTURE OF THE STILPROFIL (STYLE MATRIX)

The Stilprofil is not stored as running text but as a structured style matrix.

### 5.1 Dimensions of the style matrix

**Dimension 1: lexical level**

| Field | Phenomenon fields | Content |
|---|---|---|
| Specialist-term equivalences | PF-05 | AR word → preferred DE rendering |
| Synonym avoidance | PF-05 | Systematically avoided alternatives |
| Parenthesis use | PF-08 | Which parenthetical precisifications are rule-determined |
| Particle handling | PF-01 | Rendering of وَ / فَ / ثُمَّ / بَل / إِنَّ / لَ etc. |

**Dimension 2: syntactic level**

| Field | Phenomenon fields | Content |
|---|---|---|
| Sentence movement | PF-02 | Degree of mirroring of Arabic sentence movement |
| Connection chains | PF-02 | Preferred rendering of connectors |
| Idāfa handling | PF-03 | Preferred pattern for genitive constructions |
| Masdar / verb relation | PF-04 | Noun vs. verb in Masdar constructions |

**Dimension 3: rhetorical level**

| Field | Phenomenon fields | Content |
|---|---|---|
| Repetition behaviour | PF-02 | Whether parallelisms are kept visible |
| Intensity preservation | PF-09 | How emphasis and pointing-up are preserved |
| Imagery | PF-10 | Whether metaphors stay literal or are bracketed |

**Dimension 4: specialist-language level**

| Field | Phenomenon fields | Content |
|---|---|---|
| Hadith-critical language | PF-07 | Preferred rendering of technical termini |
| Juridical-contractual language | PF-10 | Tone and metaphor preservation |
| Polemical-argumentative language | PF-09 | Degree of hardness preservation |
| Register height | PF-11 | Overall register (elevated / text-near / classical) |

**Dimension 5: citation behaviour**

| Field | Phenomenon fields | Content |
|---|---|---|
| Qurʾān citation | PF-06 | Whether verses are written out or only referenced |
| Ḥadīṯ embedding | PF-06 | How citations are integrated into running text |

**Dimension 6: negative list**

| Field | Phenomenon fields | Content |
|---|---|---|
| Locked patterns | PF-12 | Systematically rejected patterns from correction signals |

### 5.2 Metadata stored per style entry

| Field | Type | Content |
|---|---|---|
| stil_regel_uuid | UUID | Unique ID |
| account_uuid | UUID | Owning account (account binding, see §2.1) |
| dimension | Enum | `lexikalisch` / `syntaktisch` / `rhetorisch` / `fachsprachlich` / `zitationsverhalten` / `negativ` |
| phänomenfeld | Enum | PF-01 to PF-12 |
| arabisches_muster | Text | Arabic source pattern |
| bevorzugte_wiedergabe | Text | Preferred German rendering |
| konfidenz | Float 0.0–1.0 | Current confidence |
| belege_uuids[] | UUID[] | References to confirmed bilingual Stilbelege |
| status | Enum | See §8.2 |
| regeltyp | Enum | `invariant` / `präferenz` / `tendenz` / `kandidat` |
| invariant_quelle | Enum | `manuell_nutzer` / `nutzerbestätigung` / `nicht_invariant` |
| erstellt_aus | Enum | `referenzsatz` / `endfassung` / `manuelle_regel` / `akzeptanz_ki` / `korrektur_ki` |
| erstellt_at | Timestamp | |
| zuletzt_aktualisiert_at | Timestamp | |

### 5.3 Account binding of Stilprofil objects [KANON]

All Stilprofil objects (style entry, Stilbeleg, reference pair, Stilprofil version) are bound to `account_uuid`. No cross-account access. No technical sharing to other accounts. Concrete enforcement happens at data and query level and is part of every Stilprofil operation.

## 6. HARD INVARIANTS, PREFERENCE RULES, AND STATISTICAL TENDENCIES

### 6.1 Principle of strict separation [KANON]

The three rule types must never blur into each other. The system must not produce a hard invariant on its own from mere statistics. Transitions between types always require an explicit user action.

### 6.2 Hard invariants (regeltyp = invariant) [KANON]

What they are: rules that are never altered, never lowered, and never overwritten by the learning logic. They can only be changed by an explicit user action.

How an invariant arises — exclusively through:

- explicit manual user fixing (manually entered style rule).
- explicit user confirmation of an invariant proposed by the system.

How an invariant must not arise:

- not through statistical accumulation of accepted AI suggestions.
- not through automatic upgrading from tendencies or preferences.
- not through system logic without user action.

Pre-anchored invariants from Dokument A (apply from feature activation):

- Absolute word fidelity (no silent omissions, no silent simplifications).
- Structural proximity to the Arabic (sentence movement, order).
- Repetitions remain visible.
- No flattening of religious and specialist terms.
- No silent explanations (only open parentheses).
- No modern or casual German (register: elevated, text-near, classical).

These invariants are pre-set with `invariant_quelle = manuell_nutzer` and shown separately in the UI.

### 6.3 Learned preference rules (regeltyp = präferenz)

What they are: patterns with high confidence that are applied as a rule, but can be set aside by contextual signals.

How a preference rule arises:

- from confirmed reference sentences / final versions (sufficient evidence density assumed).
- from manually entered style rules (directly as preference or invariant).
- not from accepted AI suggestions alone.

Confidence threshold for automatic application: [KALIB] — not yet fixed.

### 6.4 Statistical tendencies (regeltyp = tendenz)

What they are: patterns that have been recognized but are too lightly evidenced for a preference rule. The system proposes them but does not apply them automatically.

How a tendency arises:

- from few items of evidence in reference sentences.
- from weak candidates that have been reinforced through accepted AI suggestions.

Confidence threshold: [KALIB] — not yet fixed.

### 6.5 Candidates (regeltyp = kandidat)

What they are: weakest category. Patterns observed once (e.g. through an accepted AI suggestion) but not yet of rule status. No application. No suggestion. Only observation.

Upgrade: only through user confirmation or through new confirmed reference-sentence evidence. Never through further accepted AI suggestions alone.

### 6.6 Upgrade rules (transitions between types)

| From | To | Condition |
|---|---|---|
| kandidat | tendenz | Minimum evidence density from reference sentences [KALIB] or user confirmation |
| tendenz | präferenz | Higher evidence density [KALIB] or user confirmation |
| präferenz | invariant | Only through explicit user action [KANON] |
| invariant | präferenz | Only through explicit user action [KANON] |
| any type | vom_nutzer_gesperrt | Explicit user action or repeated correction signal |

## 7. REFERENCE-SENTENCE BINDING (BILINGUAL)

### 7.1 Requirements for a valid reference sentence [KANON]

| Criterion | Requirement |
|---|---|
| Arabic original | Fully present |
| German final version | Fully present and confirmed by user as final version |
| Confirmation | Explicit user confirmation — no automatic intake |
| Format | Bilingual pair (AR + DE) — not monolingual |
| Status | Final version — no draft, no intermediate state |

### 7.2 Style-signal extraction

→ Sequence: see §4.4.

### 7.3 Reference-sentence versioning [KANON]

When a final version is revised by the user:

- the Stilbelege derived from it are marked and subjected to re-evaluation.
- the user is informed and asked to re-confirm.
- already-applied style patterns on completed pages remain unchanged.

## 8. CONFLICT LOGIC WITH SYSTEM RULES AND STATE MODEL

### 8.1 Principle [KANON]

System rules always have precedence over Stilprofil rules. The Stilprofil must neither overwrite nor undermine system rules. No silent decisions on conflict.

### 8.2 State model for style entries

Every style entry is in exactly one of the following states:

| Status | Meaning |
|---|---|
| aktiv | Rule is active and is applied |
| in_prüfung | Candidate — observed, but not yet rule status; no application |
| unterdrückt_durch_systemregel | Conflict with system rule established; system rule has precedence; user informed |
| nur_kontextuell_zulässig | Rule is valid, but only applicable in certain contexts (e.g. not on Qurʾān verses) |
| deaktiviert | Temporarily deactivated by user; remains stored |
| vom_nutzer_gesperrt | Permanently locked by explicit user action or repeated correction signals |

State transitions are logged and auditable.

### 8.3 Conflict types and resolution

| Conflict type | Resolution | Target state of style entry |
|---|---|---|
| Style rule contradicts glossary entry | Glossary always wins | unterdrückt_durch_systemregel |
| Style rule contradicts transliteration rule | Transliteration rule wins; spelling adapted (not deleted) | unterdrückt_durch_systemregel |
| Style rule contradicts terminology index | Terminology index wins | unterdrückt_durch_systemregel |
| Style rule contradicts religious-formulas index | Formulas index always wins | unterdrückt_durch_systemregel |
| Style rule contradicts Qurʾān-verse handling | External source wins; rule deactivated in Qurʾān-verse context | nur_kontextuell_zulässig |
| Style rule contradicts hadith verification logic | Verification logic wins | unterdrückt_durch_systemregel |
| Reference sentence contains spelling contrary to system rule | Reference sentence remains stylistically authoritative; spelling adapted | No conflict on the style entry itself |
| Conflict not unambiguously categorizable | User asked for explicit decision | Remains in `in_prüfung` until decision |

### 8.4 Conflict logging [KANON]

Every conflict is logged with:

- timestamp.
- conflict type.
- affected style entry (UUID).
- affected system rule.
- state transition.
- user informed: yes/no.
- user decision (if required): pending / made / rejected.

## 9. VERSIONING OF THE STILPROFIL

### 9.1 Principle [KANON]

Every change to the Stilprofil produces a new version. No version is overwritten.

### 9.2 Stilprofil-version fields

| Field | Type | Content |
|---|---|---|
| stilprofil_version_uuid | UUID | Unique ID of the version |
| account_uuid | UUID | Owning account |
| version_nummer | Integer | Monotonically increasing |
| erstellt_at | Timestamp | |
| auslöser | Enum | `neuer_referenzsatz` / `nutzerakzeptanz` / `nutzerkorrektur` / `manuelle_regel` / `deaktivierung` / `konfliktauflösung` |
| delta | JSON | Changed entries relative to predecessor version |
| is_aktiv | Boolean | Only one version can be active |

### 9.3 Unchangeability of applied versions [KANON]

When a particular Stilprofil version has been applied to a page, that application is unchangeable. Later Stilprofil changes never automatically alter completed pages.

### 9.4 Rollback

The Stilprofil rollback function is [KANON] active by default for all users with the style feature enabled. The user can return to an earlier `stilprofil_version`. Rollback affects only future applications, never completed pages (see §9.3 unchangeability of applied versions). The UI design of the rollback control is [KONFIG] product-configurable (cf. Dokument C v1.1 §4.2).

## 10. LEARNING LOGIC AND IMPROVEMENT LOGIC

### 10.1 Adaptive learning system [KANON]

The system learns adaptively. Confidence values rise and fall on the basis of user actions:

- User confirms suggestion → confidence rises.
- User corrects suggestion → confidence falls.
- User ignores suggestion → no signal.

No automatic rule applications without sufficient confidence [KALIB].

### 10.2 What the learning logic must never do [KANON]

- automatically overwrite glossary entries.
- undermine system rules.
- produce an invariant from statistics alone.
- upgrade a candidate to a preference rule without user confirmation or reference-sentence evidence density.

### 10.3 New confirmed reference sentences

→ Sequence: see §4.4.

### 10.4 Phenomenon-field coverage display [KONFIG]

The system shows the user, per phenomenon field, how many confirmed pieces of evidence are present and which fields are still insufficiently covered.

### 10.5 What is not learned [KANON]

- vocalization patterns (separately stored).
- Qurʾān-verse rendering (external: quranenc.com).
- hadith texts (verification logic).
- glossary entries (system rule).
- transliteration rules (system rule).

## 11. QUALITY AND SAFETY LOGIC

### 11.1 Only confirmed material [KANON]

No unconfirmed material flows into the Stilprofil.

### 11.2 No covert style application [KANON]

Every application of a style pattern to a translation suggestion is made identifiable. No silent application without indication.

### 11.3 Transparency toward the user [KONFIG]

The user can at any time inspect:

- the active Stilprofil (organized by dimensions, phenomenon fields, rule types).
- confidence value and status of every entry.
- evidence list of every entry (with reference to AR/DE pair).
- phenomenon-field coverage state.

### 11.4 Audit trail [KANON]

Every Stilprofil application to a translation suggestion is logged:

- which Stilprofil version.
- which concrete style entries influenced the suggestion.
- timestamp.

### 11.5 No sharing without explicit release [KANON]

The Stilprofil of an account is never automatically passed on to other accounts.

### 11.6 Stilprofil marker (visual identification) [KANON]

Style-influenced positions in the editor are marked by a discreet underline (blue tone) + hover tooltip with rule designation (PF-XX). The display of style markers can be deactivated in the display settings. The display setting for style markers is stored at account level.

## 12. LIMITS OF THE FEATURE

### 12.1 Substantive limits [KANON]

- The Stilprofil can only learn what is present in confirmed reference material.
- It cannot learn areas for which no bilingual evidence is present.
- It cannot make decisions that contradict a system rule.

### 12.2 Calibration-dependent limits [KALIB]

- Phenomenon fields with insufficient evidence density remain in status `tendenz` or `kandidat`.
- Confidence thresholds for automatic application not yet fixed.

### 12.3 Application limits

- Completed pages are never automatically altered by later Stilprofil changes [KANON].
- The Stilprofil does not apply to the OCR-export track [KANON].
- Which account classes may use the feature is product-configurable [KONFIG].

## 13. WHAT IS EXPRESSLY NOT PART OF THE FEATURE

| Excluded point | Type | Justification |
|---|---|---|
| Automatic overwriting of glossary entries | [KANON] | System-rule precedence |
| Automatic overwriting of transliteration rules | [KANON] | System-rule precedence |
| Automatic overwriting of religious formulas | [KANON] | System-rule precedence |
| Application to Qurʾān references per §4.15 | [KANON] | External source, system rule |
| Application to hadith texts | [KANON] | Verification logic, system rule |
| Application to OCR-export track | [KANON] | OCR DOCX is source text, not a translation document |
| Application to foreign accounts | [KANON] | Account binding absolute |
| Learning from unconfirmed drafts | [KANON] | Only confirmed material |
| Learning from ignored AI suggestions | [KANON] | Null signal |
| Invariant from statistics alone | [KANON] | Invariant only through explicit user action |
| Covert style application without identification | [KANON] | Transparency obligation |
| Retroactive change of completed pages | [KANON] | Unchangeability |
| Vocalization patterns as style patterns | [KANON] | Separately stored |
| Stilprofil as a replacement for Option A | [KANON] | Supplement, not replacement |

## 14. OPEN POINTS (CALIBRATABLE — NOT YET FIXED)

| Open point | Status |
|---|---|
| Minimum number of reference sentences for activation | [KALIB] |
| Confidence threshold: candidate → tendency | [KALIB] |
| Confidence threshold: tendency → preference | [KALIB] |
| Confidence threshold for automatic application (preference) | [KALIB] |
| Minimum evidence density per phenomenon field | [KALIB] |

The calibration values are fixed after gold-corpus tests.

## 15. CURRENT ACTION STATUS

This document is Dokument B v1.2 — feature specification "Recognize my translation style". It builds on Dokument A (canonical user-style corpus v1.0) and is frozen as the canonical style-feature specification.

Dokument C v1.1 is the integration notice for this feature and was formally confirmed as integration frame. The follow-on work named in Dokument C v1.1 §3 — formal integration analysis, CRs for Core Architecture Baseline / Engineering Execution Baseline / Delivery Backlog Baseline, extension of existing objects (`account`, `decision_event`, translation job/recovery, provenance / EXPORT_EVENT), audit integration into the A-01–D-03 structure, ticket definition, sprint planning, calibration of the open thresholds after gold-corpus tests, coding release — remain expressly open and are not pulled without explicit user instruction.

Not yet:

- No code.
- No coding release.
- No implementation.
- No CR without explicit instruction.
- No new architecture outside the existing canon.

Dokument B v1.2 — feature specification "Recognize my translation style" — canonically frozen. Not to be used as a stand-alone implementation instruction.