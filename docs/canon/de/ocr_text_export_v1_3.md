<!-- Converted from "OCR TEXT EXPORT v1.3.docx" via pandoc 3.9.0.2 on 2026-05-02 -->
<!-- The .docx in this directory remains source-of-truth per docs/canon/README.md authority rule -->
<!-- Conversion is content-faithful (text, tables, identifiers, Swiss German ss, Arabic RTL spans, §-refs); Word-specific visual styling is dropped -->

# **WARAQ – OCR-TEXT-EXPORT: KONSOLIDIERTE ENDFASSUNG v1.3**

> Kein Code. Keine Coding-Freigabe. Modellseitig geschlossene Endfassung vor Implementierungsentscheid.

## **ABSCHNITT 1 – DEFINITIONEN UND ABFRAGEREGELN**

### **1.1 exported_segment_uuids – modelltreue Join-Regel**

Die Zuordnung von ocr_revision_snapshot\[\]-Werten zu Segment-UUIDs hängt an der segments-Tabelle, nicht an der revisions-Tabelle. Die segments-Tabelle ist der kanonische Eigentümer der satz_uuid und führt current_rev_uuid als abgeleitetes Verweis-Feld. Die Revision ist nicht Eigentümerin der Segmentidentität.

Abfrageregel:

exported_segment_uuids =

SELECT satz_uuid FROM segments

WHERE current_rev_uuid IN ocr_revision_snapshot\[\]

AND active = true

ocr_revision_snapshot\[\] enthält Revisions-UUIDs. Die segments-Tabelle verknüpft via current_rev_uuid auf genau das Segment, dessen aktueller Revisionsstand exportiert wurde. Ein Segment ist nur dann enthalten, wenn es zum Exportzeitpunkt aktiv war (active = true).

### **1.2 exported_page_uuids – modelltreue Join-Regel (Variante B)**

export_config.page_range enthält den vom Nutzer gewählten Seitenbereich als Nutzer-Eingabe – also Seitenzahlen, eine Range-Angabe (z.B. 1–50) oder eine Auswahl. Es ist keine voraufgelöste Menge von page_uuid-Werten. Die Auflösung zu page_uuid muss modelltreu über die pages-Tabelle erfolgen.

Seitenzahlen sind eine Anzeigerepräsentation für den Nutzer. page_uuid ist der kanonische Identitätsträger im Modell. Die Auflösung darf nicht implizit in export_config stattfinden, sondern muss explizit über die kanonische Tabelle laufen.

Abfrageregel:

exported_page_uuids =

SELECT page_uuid FROM pages

WHERE page_number IN export_config.page_range

AND project_uuid = current_project_uuid

AND active = true

Erläuterungen:

- page_number: Anzeigefeld in der pages-Tabelle mit der vom Nutzer sichtbaren Seitennummer.

- export_config.page_range: Normalisierte Menge von Seitenzahlen aus der Nutzer-Eingabe (z.B. {1, 2, …, 50} aus einer Range-Angabe 1–50).

- project_uuid: stellt sicher, dass dieselbe Seitenzahl aus einem anderen Projekt nicht irrtümlich eingeschlossen wird.

- active = true: Seiten, die durch Seitenersatz-Vorgänge inaktiviert wurden, gehören nicht zum exportierten Bereich.

export_config.page_range speichert im OCR_EXPORT_EVENT die Nutzer-Eingabe als Seitenzahlen-Menge (nicht als UUID-Menge). Die UUID-Auflösung ist eine Laufzeit-Operation zur Bestimmung der Zwischenmenge exported_page_uuids und wird nicht persistiert.

### **1.3 active_decision_event_uuids\[\] – Positive Allowlist**

Grundprinzip: Die Regel ist eine positive Allowlist. Nur explizit zugelassene decision_source-Werte werden eingeschlossen. Neue decision_source-Werte landen damit nicht versehentlich im Snapshot.

Allowlist für OCR_EXPORT_EVENT:

| **decision_source** | **Zugelassen** | **Begründung** |
|----|----|----|
| ocr_review | Ja | OCR-Fehlerklassen-Auflösungen bestimmen den exportierten Textzustand mit |
| lock_management | Ja | Sperrflag-Entscheidungen auf exportierten Segmenten sind Teil des wirksamen Textzustands |
| conflict_resolution | Ja | Konflikt-Auflösungen auf exportierten Segmenten bestimmen den wirksamen Textzustand |
| export_confirmation | Ja, eingegrenzt | Nur die Pflichtfragen-Bestätigungen des aktuellen OCR-Exports, gebunden an related_export_attempt_id |
| glossary_management | Nein | Glossar-Management betrifft terminologische Steuerung im Übersetzungspfad, nicht den OCR-Quelltextzustand |
| translation_pipeline | Nein | Übersetzungsdomäne, zum OCR-Export-Zeitpunkt nicht wirksam |
| audit_resolution | Nein | Betrifft Übersetzungsausgaben |
| consistency_resolution | Nein | Betrifft werkweite Übersetzungsterminologie |
| preflight_confirmation | Nein | Betrifft den finalen Publikationsexport, nicht den OCR-Export |
| style_management | Nein | Stilprofil-Entscheidungen wirken in der Übersetzungsphase, nicht auf den OCR-Quelltextzustand |

Präzisierung für export_confirmation: Projektweite Decision Events aus export_confirmation dürfen nicht pauschal eingeschlossen werden. Nur die Pflichtfragen-Bestätigungen des aktuellen OCR-Exports gehören in den Snapshot. Ältere OCR-Export-Bestätigungen oder Bestätigungen aus anderen Domänen bleiben draussen. Dafür wird eine explizite Zwischenmenge geführt:

current_export_confirmation_uuids =

SELECT decision_event_uuid FROM decision_events

WHERE decision_source = 'export_confirmation'

AND related_export_attempt_id = current_export_attempt_id

AND is_superseded = false

related_export_attempt_id ist eine Laufzeit-Referenz auf den aktuellen Exportversuch. Sie stellt sicher, dass nur die Pflichtfragen-Bestätigungen dieses konkreten Exports eingeschlossen werden.

### **1.4 Abgrenzung OCR_EXPORT_EVENT und EXPORT_EVENT**

OCR_EXPORT_EVENT und EXPORT_EVENT sind verschiedene PO-Typen mit verschiedener Semantik. Sie dürfen nie still vermischt, nie typologisch zusammengeführt und nie unter derselben semantischen Behandlung aggregiert werden. Eine gemeinsame Darstellung (z.B. in einer Projekthistorie) ist nur dann zulässig, wenn beide Typen explizit getrennt und mit ihrem jeweiligen po_type ausgewiesen sind.

### **1.5 Keine T-5.2.1-Kopplung**

Der OCR-Export hat keinen Glossar-Laufzeitbezug. glossary_management ist aus der Allowlist ausgeschlossen. Damit entfällt jede Kopplung an T-5.2.1. T-5.2.1 ist keine Startvoraussetzung für Sprint-OCR.

## **ABSCHNITT 2 – CHANGE-REQUEST-PASSAGEN**

### **CR-1.1: Core Architecture Baseline v1.0 → v1.1 – Neuer PO-Typ OCR_EXPORT_EVENT**

Einfügestelle: Tabelle der PO-Typen, direkt nach dem EXPORT_EVENT-Eintrag. Art: Ergänzung.

OCR_EXPORT_EVENT-Felder:

| **Feld** | **Typ** | **Pflicht** | **Bedeutung** |
|----|----|----|----|
| ocr_export_uuid | UUID | Ja | Eigene UUID via IDENTITY-Service |
| project_uuid | UUID | Ja | FK auf Projekt |
| export_mode | Enum | Ja | arbeitsstand oder freigegebener_stand |
| gate_mode | Enum | Ja | exportierbar oder exportierbar_mit_warnungen – expliziter Gate-Zustand zum Exportzeitpunkt |
| export_config | JSON | Ja | Aktiv beantwortete Pflichtfragen (Seitenbereich als Seitenzahlen-Menge, Blocktypen, Markierungen, Exportmodus) |
| ocr_revision_snapshot\[\] | Array\[UUID\] | Ja | Aktive current_rev_uuid-Werte der exportierten Segmente |
| active_decision_event_uuids\[\] | Array\[UUID\] | Ja | Gemäss Positivmenge-Regel aus Abschnitt 1.3 / Abschnitt 3 |
| export_warnings\[\] | Array\[Object\] | Ja | Liste der aktiven Warnungen (leer, wenn gate_mode = exportierbar) |
| artefact_ref | Ref | Ja | Referenz auf das DOCX-Artefakt |
| active_stilprofil_version_uuid | UUID | Nein (nullable) | Aktive stilprofil_version zum Exportzeitpunkt, sofern einschlägig |
| created_at | Timestamp | Ja | Zeitpunkt der Anlage |

Zum Feld active_stilprofil_version_uuid: Das Feld ist im Schema formal angelegt. Für den OCR-Quelltextexport ist es semantisch typischerweise irrelevant und in der Regel null, da das Stilprofil in der Übersetzungsphase wirkt und den OCR-Rohtextzustand nicht verändert. Das Feld bleibt dennoch Teil des unveränderlichen Schemas und darf nicht stillschweigend weggelassen werden; es gewährleistet die einheitliche Struktur zwischen EXPORT_EVENT und OCR_EXPORT_EVENT und erlaubt eine eindeutige spätere Auswertung.

Abgrenzungsformulierung: OCR_EXPORT_EVENT und EXPORT_EVENT sind verschiedene PO-Typen mit verschiedener Semantik. Sie dürfen nie still vermischt, nie typologisch zusammengeführt und nie unter derselben semantischen Behandlung aggregiert werden. Eine gemeinsame Darstellung ist nur dann zulässig, wenn beide Typen explizit getrennt und mit ihrem jeweiligen po_type ausgewiesen sind.

Unangetastet: EXPORT_EVENT-Definition. Alle anderen PO-Typen.

### **CR-1.2: Core Architecture Baseline – OCR-Export-Freigabeschranke**

Einfügestelle: Unterabschnitt „Freigabeschranken" der Core Architecture Baseline. Art: Ergänzung.

Inhalt: Die OCR-Export-Freigabeschranke (OCR-Export-Gate) wird als eigenständige Freigabeschranke neben der bestehenden Publikationsexport-Freigabeschranke geführt.

- Zwei Gate-Zustände: exportierbar und exportierbar_mit_warnungen.

- Blockierende Zustände (Gate nicht exportierbar): F-06-QR ohne Auflösung, F-07 kritisch, F-08 unentschieden, kritische RTL-Encoding-Probleme, conflict_instance mit unklarem Textzustand, inaktive Segmente ohne Lineage-Auflösung.

- go_with_warning im Arbeitsstand-Modus: doppelte Warnung (Grund + explizite Bestätigung).

- Vier Pflichtfragen aktiv zu beantworten (Seitenbereich, Blocktypen, Markierungen, Exportmodus).

- Kein Profil-Bypass: Ein gespeichertes Profil kann Pflichtfragen vorausfüllen, ersetzt aber nie eine aktive Bestätigung.

### **CR-1.3: Core Architecture Baseline – Niemals-Automatisch-Liste**

Einfügestelle: „Niemals-Automatisch-Liste" der Core Architecture Baseline. Art: Ergänzung.

Zwei neue Einträge:

1.  Ein OCR_EXPORT_EVENT darf nie ohne ein vollständig erfolgreiches DOCX-Artefakt angelegt werden.

2.  Ein OCR_EXPORT_EVENT darf nie ausserhalb des PROVENANCE-Kerns (create_po()) angelegt werden.

### **CR-1.4: Core Architecture Baseline – Ereignisklassifikation OCR-Export**

Einfügestelle: Ereignisklassifikations-Tabelle. Art: Ergänzung.

Vier OCR-Export-Ereignistypen:

| **Aufruf** | **Gate-Zustand** | **Job gestartet** | **Log-Eintrag** | **OCR_EXPORT_EVENT** |
|----|----|----|----|----|
| check_ocr_export_gate() | beliebig | Nein | Nein | Nein |
| start_ocr_export() | blockiert | Nein | Nein | Nein |
| start_ocr_export() | exportierbar | Ja, schlägt fehl | Ja (FAILED) | Nein |
| start_ocr_export() | exportierbar | Ja, erfolgreich | Ja (SUCCESS) | Ja |
| start_ocr_export() | exportierbar_mit_warnungen + Bestätigung | Ja, erfolgreich | Ja (SUCCESS) | Ja |

### **CR-1.5: Core Architecture Baseline – Decision-Event-Objekt: Feld decision_source**

Einfügestelle: Schema-Definition des Decision-Event-Objekts. Art: Ergänzung (neues Pflichtfeld).

Neues Feld:

| **Feld** | **Typ** | **Pflicht** | **Bedeutung** |
|----|----|----|----|
| decision_source | Enum | Ja | Klassifiziert, aus welcher Prozessdomäne ein Decision Event stammt |

Vollständige Enum-Werte (überschneidungsfrei):

| **Wert** | **Prozessdomäne** |
|----|----|
| ocr_review | OCR-Fehlerklassen-Auflösung |
| lock_management | Sperrflag-Setzen/Aufheben |
| conflict_resolution | Konflikt-Auflösung (Terminologie-vs.-Sperrflag, Qurʾān-Stellen-Konflikte, Hadith-Konflikte, sonstige kanonisierte Konflikt-Handlungstypen) |
| glossary_management | Glossar-Eintragsänderung |
| export_confirmation | Pflichtfragen-Bestätigung beim OCR-Quelltext-Export (T-OCR-EX-1). Nur OCR-Export; finaler Export explizit ausgeschlossen |
| preflight_confirmation | Pflichtfragen-Bestätigung beim finalen Publikationsexport (P-01, T-9.1.1). Nur finaler Export; OCR-Export explizit ausgeschlossen |
| translation_pipeline | Übersetzungs- und RULE_BINDING-Phase |
| audit_resolution | Audit-Befund-Auflösung |
| consistency_resolution | Konsistenz-Gruppen-Auflösung |
| style_management | Stilprofil-Entscheidungen (Stilregel-Zustandsänderungen, Nutzerbestätigungen, Rollbacks) |

Die Trennung export_confirmation ↔ preflight_confirmation ist durch die Enum-Tabelle eindeutig abgesichert. Kein finaler Export-Entscheid kann versehentlich in den OCR-Export-Snapshot gelangen, und umgekehrt.

Migrationsregel für bestehende Decision Events: Alle Decision Events, die vor diesem CR ohne decision_source angelegt wurden, werden in einem separaten Migrationsarbeitsstand auf die zehn oben genannten Enum-Werte klassifiziert. Die Endfassung führt ausschliesslich diese zehn Werte; ein zusätzlicher Enum-Wert wird nicht eingeführt. Die konkrete Klassifikationsheuristik und die Behandlung nicht klassifizierbarer Altbestände liegen ausserhalb dieser Endfassung und bleiben dem separaten Migrationsarbeitsstand vorbehalten. Die Migration ist formale Voraussetzung für die Baseline-Integrität, aber kein Sprint-OCR-Scope.

Gleiche Ergänzung in: Implementation Translation Baseline v1.0 → v1.1, Abschnitt Kernobjekte, Decision-Event-Eintrag.

### **CR-1.6: Core Architecture Baseline – Decision-Event-Objekt: Feld related_export_attempt_id**

Einfügestelle: Schema-Definition des Decision-Event-Objekts. Art: Ergänzung (neues optionales Feld).

Neues Feld:

| **Feld** | **Typ** | **Pflicht** | **Bedeutung** |
|----|----|----|----|
| related_export_attempt_id | UUID | Nein (nullable) | Verknüpft einen Decision Event mit einem konkreten Exportversuch. Nur gesetzt, wenn decision_source = 'export_confirmation'. Für alle anderen decision_source-Werte: null. |

Zweck: Verhindert, dass Pflichtfragen-Bestätigungen aus früheren Exportversuchen in den active_decision_event_uuids\[\]-Snapshot eines späteren Exports gelangen. Die Bindung erfolgt ausschliesslich über dieses Feld – nicht über Zeitfenster oder andere heuristische Filter.

Setzungsregel: related_export_attempt_id wird beim Anlegen eines export_confirmation-Decision-Events gesetzt und ist danach unveränderlich.

Gleiche Ergänzung in: Implementation Translation Baseline v1.0 → v1.1.

### **CR-2.1: Implementation Translation Baseline v1.0 → v1.1 – Kernobjekte**

Einfügestelle: Kernobjekt-Tabelle, direkt nach EXPORT_EVENT. Art: Ergänzung.

Inhalt: OCR_EXPORT_EVENT mit vollständigem Feld-Schema gemäss CR-1.1 (inklusive gate_mode und active_stilprofil_version_uuid). Decision-Event-Felder decision_source und related_export_attempt_id gemäss CR-1.5 und CR-1.6. Abgrenzungsformulierung gemäss Abschnitt 1.4.

### **CR-2.2: Implementation Translation Baseline – Zustandsmaschinen OCR-Export-Gate und Export-Job**

Einfügestelle: Zustandsmaschinen-Abschnitt. Art: Ergänzung.

Inhalt: Zwei neue Zustandsmaschinen.

- OCR-Export-Gate: Zustände exportierbar, exportierbar_mit_warnungen, blockiert. Übergänge ausschliesslich aus geprüften OCR-Zuständen abgeleitet. Keine manuellen Gate-Zustandssetzungen.

- OCR-Export-Job: Zustände gestartet, erfolgreich, fehlgeschlagen. Ein OCR_EXPORT_EVENT wird nur aus erfolgreich atomar angelegt.

### **CR-2.3: Implementation Translation Baseline – Ereignis- und PO-Typ-Einträge**

Einfügestelle: Ereignis- und PO-Typ-Registrierung. Art: Ergänzung.

Inhalt: Neue Ereignistypen OCR_EXPORT_SUCCESS und OCR_EXPORT_FAILED, registriert mit zugehöriger Gate-Zustands- und Job-Zustands-Semantik. Neuer PO-Typ-Eintrag OCR_EXPORT_EVENT gemäss CR-1.1.

### **CR-3.1: Engineering Execution Baseline – Arbeitspakete**

Einfügestelle: Arbeitspaket-Tabelle. Art: Ergänzung.

Inhalt: Vier neue Arbeitspakete:

- AP-OCR-EX-1: OCR-Export-Gate-Logik und Pflichtfragen-Flow.

- AP-OCR-EX-2: DOCX-Artefakt-Erzeugung (RTL per-paragraph, Blocktypen, Vokalisation wie vorliegend, Fussnotenstruktur, editorische Markierungen).

- AP-OCR-EX-3: OCR_EXPORT_EVENT-Anlage via PROVENANCE-Kern.

- AP-OCR-EX-4: Projekthistorie- und Lookup-Erweiterung (get_ocr_exports_for_segment()); nicht Teil Sprint-OCR.

### **CR-3.2: Engineering Execution Baseline – Build-Order**

Einfügestelle: Build-Order-Matrix. Art: Ergänzung.

Inhalt: Zwei neue Build-Order-Stufen:

- Stufe 2b (M-OCR-Export): T-OCR-EX-1 → T-OCR-EX-2 → T-OCR-EX-3.

- Stufe 10b (M-Provenance-OCR): T-OCR-EX-4 (setzt T-OCR-EX-3 und T-10.2.1 voraus).

### **CR-4.1: Delivery Backlog Baseline – Ticketgruppe**

Einfügestelle: Ticket-Backlog. Art: Ergänzung.

Inhalt: Neue Ticketgruppe T-OCR-EX-1 bis T-OCR-EX-4 mit Umfang gemäss Abschnitt 5 dieses Dokuments.

### **CR-4.2: Delivery Backlog Baseline – Meilensteine**

Einfügestelle: Meilenstein-Tabelle. Art: Ergänzung.

Inhalt: Zwei neue Meilensteine:

- M-OCR-Export: T-OCR-EX-1 bis T-OCR-EX-3 grün; DOCX-Artefakt reproduzierbar erzeugt; OCR_EXPORT_EVENT atomar angelegt.

- M-Provenance-OCR: T-OCR-EX-4 grün; get_ocr_exports_for_segment() funktional; Projekthistorie-Ansicht OCR-Export-fähig.

Keines dieser CRs definiert ein bestehendes Ticket, einen bestehenden Meilenstein oder einen bestehenden PO-Typ um. Alle CRs sind Ergänzungen.

## **ABSCHNITT 3 – VOLLSTÄNDIGE CODIERBARE ABFRAGEREGEL**

-- Schritt 1: Exportierte Segmente (via segments-Tabelle, modelltreu)

exported_segment_uuids =

SELECT satz_uuid FROM segments

WHERE current_rev_uuid IN ocr_revision_snapshot\[\]

AND active = true

-- Schritt 2: Exportierte Seiten (via pages-Tabelle, Seitenzahl -\> UUID aufgelöst)

exported_page_uuids =

SELECT page_uuid FROM pages

WHERE page_number IN export_config.page_range

AND project_uuid = current_project_uuid

AND active = true

-- Schritt 3: Pflichtfragen-Bestätigungen des aktuellen OCR-Exportversuchs

current_export_confirmation_uuids =

SELECT decision_event_uuid FROM decision_events

WHERE decision_source = 'export_confirmation'

AND related_export_attempt_id = current_export_attempt_id

AND is_superseded = false

-- Schritt 4: Vollständige active_decision_event_uuids\[\]

active_decision_event_uuids\[\] =

SELECT decision_event_uuid FROM decision_events

WHERE is_superseded = false

AND decision_source IN ('ocr_review', 'lock_management', 'conflict_resolution')

AND (

(scope_type = 'segment' AND scope_uuid IN exported_segment_uuids)

OR (scope_type = 'page' AND scope_uuid IN exported_page_uuids)

)

UNION

current_export_confirmation_uuids

Garantien dieser Regel:

- export_confirmation und preflight_confirmation sind eindeutig getrennt; keine Doppelklassifizierung.

- exported_segment_uuids modelltreu über die segments-Tabelle; keine Anleihe an die revisions-Tabelle.

- exported_page_uuids modelltreu über die pages-Tabelle, Seitenzahl → UUID aufgelöst, auf aktuelles Projekt eingegrenzt.

- Inaktive Segmente und inaktive Seiten ausgeschlossen.

- Positive Allowlist: neue decision_source-Werte (style_management, translation_pipeline, audit_resolution, consistency_resolution, glossary_management, preflight_confirmation) können nicht versehentlich im Snapshot landen.

- Nur Pflichtfragen-Bestätigungen des aktuellen Exportversuchs via related_export_attempt_id.

## **ABSCHNITT 4 – CR-ÜBERBLICK**

| **CR** | **Dokument** | **Art** | **Inhalt** |
|----|----|----|----|
| CR-1.1 | Core Architecture Baseline | Ergänzung | Neuer PO-Typ OCR_EXPORT_EVENT inkl. gate_mode und active_stilprofil_version_uuid; Abgrenzungsformulierung |
| CR-1.2 | Core Architecture Baseline | Ergänzung | OCR-Export-Freigabeschranke |
| CR-1.3 | Core Architecture Baseline | Ergänzung | Niemals-Automatisch-Liste: zwei neue Einträge |
| CR-1.4 | Core Architecture Baseline | Ergänzung | Ereignisklassifikation: vier OCR-Export-Ereignistypen |
| CR-1.5 | Core Architecture Baseline | Ergänzung | Decision-Event-Objekt: neues Pflichtfeld decision_source (Enum mit 10 Werten inkl. style_management) |
| CR-1.6 | Core Architecture Baseline | Ergänzung | Decision-Event-Objekt: neues optionales Feld related_export_attempt_id |
| CR-2.1 | Implementation Translation Baseline | Ergänzung | Neues Kernobjekt OCR_EXPORT_EVENT; Decision-Event-Felder decision_source und related_export_attempt_id |
| CR-2.2 | Implementation Translation Baseline | Ergänzung | Zustandsmaschinen OCR-Export-Gate und Export-Job |
| CR-2.3 | Implementation Translation Baseline | Ergänzung | Neue Ereignis- und PO-Typ-Einträge |
| CR-3.1 | Engineering Execution Baseline | Ergänzung | Arbeitspakete AP-OCR-EX-1 bis AP-OCR-EX-4 |
| CR-3.2 | Engineering Execution Baseline | Ergänzung | Build-Order-Stufen 2b (M-OCR-Export) und 10b (M-Provenance-OCR) |
| CR-4.1 | Delivery Backlog Baseline | Ergänzung | Ticketgruppe T-OCR-EX-1 bis T-OCR-EX-4 |
| CR-4.2 | Delivery Backlog Baseline | Ergänzung | Meilensteine M-OCR-Export und M-Provenance-OCR |

Alle CRs sind Ergänzungen. Kein bestehendes Ticket, kein bestehender Meilenstein und kein bestehender PO-Typ wird umdefiniert.

## **ABSCHNITT 5 – SPRINTPLAN SPRINT-OCR v1.3**

Startbedingung: Sprint 1 vollständig abgeschlossen (T-4.3.1, T-5.1.1, T-5.1.2, T-4.2.1, T-4.2.2 grün; T-1.6.1 grün). T-5.2.1 ist keine Startvoraussetzung. T-OCR-EX-4 ist nicht Teil dieses Sprints. CR-1.5 und CR-1.6 sind als Schema-Migration vorhanden, bevor T-OCR-EX-1 startet.

### **1. Scope**

| **Ticket** | **Bezeichnung** |
|----|----|
| T-OCR-EX-1 | OCR-Export-Gate (Freigabeschranke, zwei Modi, vier Pflichtfragen) |
| T-OCR-EX-2 | OCR-Text-Artefakt-Erzeugung DOCX (RTL per-paragraph, Blocktypen, Vokalisation wie vorliegend, Markierungen) |
| T-OCR-EX-3 | OCR_EXPORT_EVENT-Anlage (atomar, via PROVENANCE-Kern, Positivmenge-Snapshot, unveränderlich) |

Bewusst nicht in diesem Sprint: T-OCR-EX-4 (nach Sprint 6), T-5.2.1 (keine Kopplung), Übersetzungs-Pipeline, Audit, Preflight, EXPORT_EVENT.

### **2. Sprint-Zielzustand**

T-OCR-EX-1 – OCR-Export-Gate:

- check_ocr_export_gate() berechnet den Gate-Zustand on-demand, kein Log-Eintrag.

- start_ocr_export() prüft das Gate als erste Aktion; bei blockiertem Gate kein Log-Eintrag, kein Job-Start.

- Harte Blockaden: F-06-QR unaufgelöst, F-07 kritisch, F-08 unentschieden, kritische RTL-Encoding-Probleme, conflict_instance mit unklarem Textzustand, inaktive Segmente ohne Lineage-Auflösung.

- go_with_warning im Arbeitsstand-Modus: doppelte Warnung (Grund + explizite Bestätigung).

- Vier Pflichtfragen aktiv zu beantworten (Seitenbereich, Blocktypen, Markierungen, Exportmodus).

- Decision-Event-UUID bei Bestätigung mit decision_source = 'export_confirmation' und related_export_attempt_id = current_export_attempt_id.

- Log-Eintrag nur bei tatsächlich gestartetem Job (Gate war grün, Job gestartet).

T-OCR-EX-2 – DOCX-Artefakt-Erzeugung:

- Arabischer Quelltext aus dem current_rev_uuid-Textzustand aller exportierten Segmente (gesperrte Segmente: manuell korrigierter Text, nie roher OCR-Text).

- RTL-Absatzmarkierung pro Absatz (nicht nur dokument-global).

- Blocktypen-Formatvorlagen: MT, UE; optional FN, QR, HD, RN.

- Echte DOCX-Fussnotenstruktur bei aktiviertem FN.

- Vokalisation exakt wie vorliegend – keine Ergänzung, keine Unterdrückung.

- Editorische Markierungen (Nutzerentscheidung): DOCX-Kommentare auf gesperrten Segmenten, offenen Konflikten, Vokalisierungsunsicherheiten.

- Export-Protokoll immer: Seitenbereich, Modus, Blocktypen, Vokalisations-Statistik, Warnliste.

- DOCX öffnet in Word ohne Warnmeldungen oder Reparaturhinweise.

- Kein neuer Revisions-UUID durch die DOCX-Erzeugung.

T-OCR-EX-3 – OCR_EXPORT_EVENT-Anlage:

- Atomar nach vollständig erfolgreichem DOCX via PROVENANCE-Kern (create_po()).

- po_type = OCR_EXPORT_EVENT, scope_type = artefact.

- ocr_revision_snapshot\[\]: alle aktiven current_rev_uuid-Werte der exportierten Segmente.

- active_decision_event_uuids\[\]: gemäss Positivmenge-Regel (Schritt 1–4 aus Abschnitt 3).

- gate_mode: explizit gesetzt (exportierbar oder exportierbar_mit_warnungen).

- active_stilprofil_version_uuid: im OCR-Export-Kontext typischerweise null; Feld wird dennoch gemäss Schema geführt.

- Unveränderlich nach Anlage.

- Bei fehlgeschlagenem DOCX: kein OCR_EXPORT_EVENT, nur Log-Eintrag (OCR_EXPORT_FAILED).

Neue Objekte am Sprint-Ende:

| **Objekt** | **Eingeführt durch** | **Zweck** |
|----|----|----|
| OCR_EXPORT_EVENT | T-OCR-EX-3 | Persistentes, unveränderliches Provenance-Objekt |
| decision_source (Feld) | T-OCR-EX-1 | Klassifiziert die Prozessdomäne jedes Decision Events |
| related_export_attempt_id (Feld) | T-OCR-EX-1 | Bindet export_confirmation-Entscheide an einen konkreten Versuch |
| gate_mode (Feld in OCR_EXPORT_EVENT) | T-OCR-EX-3 | Expliziter Gate-Zustand, direkt lesbar |
| export_warnings\[\] | T-OCR-EX-3 | Konkrete Warnungen zum Exportzeitpunkt |

Bewusst noch nicht vorhanden: get_ocr_exports_for_segment() (T-OCR-EX-4), Projekthistorie-Erweiterung (T-OCR-EX-4), UI-Flow.

### **3. Ticket-Reihenfolge**

Startbedingungen: T-4.3.1 (ocr_status), T-5.1.1 (Sperrflag), T-5.1.2 (conflict_instance), T-4.2.1 und T-4.2.2 (Lineage), T-1.6.1 (PROVENANCE-Kern) grün. T-5.2.1 nicht erforderlich. CR-1.5 und CR-1.6 als Schema-Migration vorhanden.

Sequenz:

T-OCR-EX-1 (Gate + decision_source / related_export_attempt_id)

\|

v

T-OCR-EX-2 (DOCX-Erzeugung)

\|

v

T-OCR-EX-3 (OCR_EXPORT_EVENT atomar)

Strikt sequenziell. Kein Parallelfenster.

### **4. Pflicht-Tests**

| **Test-ID** | **Ticket** | **Prüfinhalt** | **Setup-Hinweis** |
|----|----|----|----|
| OCR-Gate-Blockiert-F06-Test | T-OCR-EX-1 | F-06-QR ohne Auflösung → Gate blockiert | F-06-QR ohne resolution_type |
| OCR-Gate-Blockiert-F07-Test | T-OCR-EX-1 | F-07 kritisch → Gate blockiert | F-07 mit Kritisch-Klassifizierung |
| OCR-Gate-Blockiert-F08-Test | T-OCR-EX-1 | F-08 unentschieden → Gate blockiert | F-08 ohne Auflösung |
| OCR-Gate-Vorabpruefung-Kein-Log-Test | T-OCR-EX-1 | check_ocr_export_gate() → kein Log-Eintrag | Delta-Prüfung: Log-Tabelle unverändert |
| OCR-Gate-Blockiert-Start-Kein-Log-Test | T-OCR-EX-1 | start_ocr_export() bei blockiertem Gate → kein Log-Eintrag | Delta-Prüfung |
| OCR-Gate-Go-With-Warning-Doppelwarnung-Test | T-OCR-EX-1 | go_with_warning im Arbeitsstand → doppelte Warnung + Bestätigung | – |
| OCR-Gate-Pflichtfragen-Aktiv-Test | T-OCR-EX-1 | Export ohne aktiv beantwortete Pflichtfragen → blockiert | – |
| OCR-Gate-Kein-Profil-Bypass-Test | T-OCR-EX-1 | Gespeichertes Profil ersetzt nicht aktive Bestätigung | Profil vorausgefüllt; Bestätigung fehlt → blockiert |
| OCR-Gate-Decision-Event-Source-Test | T-OCR-EX-1 | Pflichtfragen-Bestätigung → Decision-Event mit decision_source = 'export_confirmation' | Nachweis in Decision-Event-Tabelle |
| OCR-Gate-Export-Attempt-ID-Test | T-OCR-EX-1 | related_export_attempt_id korrekt auf current_export_attempt_id gesetzt | Nachweis in Decision-Event-Tabelle |
| RTL-Absatz-Test | T-OCR-EX-2 | Jeder Absatz hat explizite RTL-Markierung (nicht nur dokument-global) | DOCX-Strukturprüfung auf Absatzebene |
| DOCX-Integritaets-Test | T-OCR-EX-2 | DOCX öffnet in Word ohne Warnmeldungen oder Reparaturhinweise | Word-kompatible Validierung |
| Blocktypen-Filter-Test | T-OCR-EX-2 | Nur aktivierte Blocktypen im DOCX; deaktivierte im Protokoll | QR deaktiviert; QR fehlt im DOCX; Protokolleintrag vorhanden |
| Vokalisation-Wie-Vorliegend-Test | T-OCR-EX-2 | Harakāt im OCR-Stand erscheinen im DOCX; keine künstliche Ergänzung | Segment mit Harakāt; Segment ohne Harakāt |
| Gesperrtes-Segment-Manueller-Text-Test | T-OCR-EX-2 | Segment mit manual_local enthält manuell korrigierten Text, nicht rohen OCR-Text | H-1-Nachweis |
| Fussnotenstruktur-Test | T-OCR-EX-2 | FN-Blöcke als echte DOCX-Fussnoten, nicht als Inline-Text | FN aktiviert; DOCX-Struktur geprüft |
| Export-Protokoll-Immer-Test | T-OCR-EX-2 | Protokoll immer erzeugt; enthält Vokalisations-Statistik und Warnliste | – |
| Kein-Rev-UUID-DOCX-Test | T-OCR-EX-2 | DOCX-Erzeugung erzeugt keinen neuen Revisions-UUID | Delta-Prüfung Revisions-Tabelle |
| OCR-EXPORT_EVENT-Nur-Bei-Erfolg-Test | T-OCR-EX-3 | OCR_EXPORT_EVENT nur bei erfolgreichem DOCX | Delta-Prüfung |
| OCR-EXPORT_EVENT-Kein-Eintrag-Bei-Fehler-Test | T-OCR-EX-3 | Fehlgeschlagener DOCX → kein neuer OCR_EXPORT_EVENT | Simulierter Artefakt-Fehler |
| OCR-EXPORT_EVENT-Atomaritaet-Test | T-OCR-EX-3 | Kein Teilzustand; alle Pflichtfelder nach Anlage gesetzt | – |
| OCR-Snapshot-Vollstaendigkeit-Test | T-OCR-EX-3 | ocr_revision_snapshot\[\] enthält alle aktiven current_rev_uuid-Werte | N Segmente → N Einträge |
| OCR-Snapshot-Segments-Join-Test | T-OCR-EX-3 | exported_segment_uuids via segments.current_rev_uuid, nicht via revisions-Tabelle | Code-Review-Nachweis |
| OCR-Snapshot-Pages-Join-Test | T-OCR-EX-3 | Abfrage läuft via page_number IN export_config.page_range mit project_uuid-Filter und active = true; kein direkter UUID-Vergleich gegen export_config | Code-Review-Nachweis |
| OCR-Decision-Snapshot-Allowlist-Test | T-OCR-EX-3 | active_decision_event_uuids\[\] enthält nur Allowlist-Quellen; kein glossary_management; kein preflight_confirmation; kein style_management; kein alter export_confirmation-Eintrag | Bekannte Menge; Array geprüft |
| OCR-Decision-Snapshot-Attempt-Bindung-Test | T-OCR-EX-3 | Nur export_confirmation-Einträge mit aktuellem related_export_attempt_id; ältere ausgeschlossen | Zwei Einträge mit verschiedenen attempt_id-Werten; nur aktueller im Array |
| OCR-Gate-Mode-Test | T-OCR-EX-3 | gate_mode korrekt gesetzt | go_with_warning → gate_mode = exportierbar_mit_warnungen |
| OCR-EXPORT_EVENT-Via-PROVENANCE-Kern-Test | T-OCR-EX-3 | create_po() via PROVENANCE-Kern; kein direkter Tabellen-Insert | Code-Review-Nachweis |
| OCR-EXPORT_EVENT-Unveraenderlichkeit-Test | T-OCR-EX-3 | Update-Versuch → Fehler | Versuch, artefact_ref zu ändern → Fehler |
| OCR-EXPORT_EVENT-Scope-Test | T-OCR-EX-3 | po_type = OCR_EXPORT_EVENT, scope_type = artefact in der Provenance-Tabelle | – |
| Log-Eintrag-Bei-Gestarteten-Job-Test | T-OCR-EX-3 | Log-Eintrag (SUCCESS oder FAILED) bei jedem tatsächlich gestarteten Job | Fehlgeschlagener DOCX: OCR_EXPORT_FAILED-Log vorhanden |

Invarianten:

- H-1: Gesperrte Segmente im Export mit manuell korrigiertem Text.

- H-3 (analog): Keine Artefakterzeugung ohne aktiv beantwortete Pflichtfragen.

- H-4: Kein Revisions-UUID durch DOCX-Erzeugung oder OCR_EXPORT_EVENT-Anlage.

- H-5: ocr_export_uuid unveränderlich nach Anlage.

Neue Regressionen ab diesem Sprint:

- OCR_EXPORT_EVENT bei blockiertem oder fehlgeschlagenem Export angelegt.

- DOCX öffnet mit Warnmeldungen in Word.

- RTL nur auf Dokumentebene.

- Gesperrtes Segment mit rohem OCR-Text exportiert.

- Vorabprüfung erzeugt Log-Eintrag.

- OCR_EXPORT_EVENT nicht via PROVENANCE-Kern angelegt.

- glossary_management-, preflight_confirmation- oder style_management-Entscheid in active_decision_event_uuids\[\].

- Alter export_confirmation-Entscheid aus früherem Export in active_decision_event_uuids\[\].

- decision_source-Feld nicht gesetzt bei neuem Decision Event.

- exported_page_uuids enthält inaktive Seiten oder Seiten ausserhalb des aktuellen Projekts.

### **5. Definition of Done**

Code:

- T-OCR-EX-1, T-OCR-EX-2, T-OCR-EX-3 implementiert, reviewt und gemergt.

- CR-1.5 und CR-1.6 (decision_source, related_export_attempt_id) als Schema-Migration in der Datenbank vorhanden.

- Kein offener Review-Kommentar, der eine Baseline-Verletzung beschreibt.

- Sprint-0- bis Sprint-1-Regressionstests weiterhin grün.

OCR-Export-Gate:

- OCR-Gate-Blockiert-F06/F07/F08-Tests grün.

- OCR-Gate-Vorabpruefung-Kein-Log-Test grün.

- OCR-Gate-Blockiert-Start-Kein-Log-Test grün.

- OCR-Gate-Go-With-Warning-Doppelwarnung-Test grün.

- OCR-Gate-Pflichtfragen-Aktiv-Test grün.

- OCR-Gate-Kein-Profil-Bypass-Test grün.

- OCR-Gate-Decision-Event-Source-Test grün.

- OCR-Gate-Export-Attempt-ID-Test grün.

DOCX-Artefakt:

- RTL-Absatz-Test grün.

- DOCX-Integritaets-Test grün.

- Blocktypen-Filter-Test grün.

- Vokalisation-Wie-Vorliegend-Test grün.

- Gesperrtes-Segment-Manueller-Text-Test grün.

- Fussnotenstruktur-Test grün.

- Export-Protokoll-Immer-Test grün.

- Kein-Rev-UUID-DOCX-Test grün.

OCR_EXPORT_EVENT:

- OCR-EXPORT_EVENT-Nur-Bei-Erfolg-Test grün.

- OCR-EXPORT_EVENT-Kein-Eintrag-Bei-Fehler-Test grün.

- OCR-EXPORT_EVENT-Atomaritaet-Test grün.

- OCR-Snapshot-Vollstaendigkeit-Test grün.

- OCR-Snapshot-Segments-Join-Test grün (Code-Review).

- OCR-Snapshot-Pages-Join-Test grün (Code-Review).

- OCR-Decision-Snapshot-Allowlist-Test grün.

- OCR-Decision-Snapshot-Attempt-Bindung-Test grün.

- OCR-Gate-Mode-Test grün.

- OCR-EXPORT_EVENT-Via-PROVENANCE-Kern-Test grün (Code-Review).

- OCR-EXPORT_EVENT-Unveraenderlichkeit-Test grün.

- OCR-EXPORT_EVENT-Scope-Test grün.

- Log-Eintrag-Bei-Gestarteten-Job-Test grün.

### **6. Risiken**

OCR-R01 – RTL nur Dokumentebene. Wahrscheinlichkeit: Hoch. Konsequenz: DOCX-Absätze ohne eigene RTL-Markierung; Darstellung in Word unzuverlässig. Review-Pflicht: RTL-Absatz-Test muss die Absatzebene prüfen.

OCR-R02 – Gesperrtes Segment mit rohem OCR-Text. Wahrscheinlichkeit: Mittel. Konsequenz: Manuelle Korrekturen gehen im Export verloren. Review-Pflicht: Gesperrtes-Segment-Manueller-Text-Test grün; Code-Review prüft die Textzustands-Quelle.

OCR-R03 – OCR_EXPORT_EVENT als Fortschrittsmarker missverstanden. Wahrscheinlichkeit: Hoch. Konsequenz: Provenance-Einträge für blockierte oder fehlgeschlagene Exporte. Review-Pflicht: Atomaritaets- und Fehler-Tests grün.

OCR-R04 – Vorabprüfung erzeugt Log-Eintrag. Wahrscheinlichkeit: Mittel. Konsequenz: Log-Rauschen; Ereignisklassifikation verfälscht. Review-Pflicht: Vorabpruefung-Kein-Log-Test und Blockiert-Start-Kein-Log-Test grün.

OCR-R05 – Snapshot unvollständig. Wahrscheinlichkeit: Mittel. Konsequenz: ocr_revision_snapshot\[\] deckt exportierte Segmente nicht vollständig ab. Review-Pflicht: Snapshot-Vollstaendigkeit-Test mit bekannter Segmentanzahl grün.

OCR-R06 – DOCX-Bibliothek ohne per-paragraph RTL. Wahrscheinlichkeit: Mittel. Konsequenz: Technisch nicht erreichbarer Zielzustand. Review-Pflicht: Bibliotheks-Vorprüfung vor Sprint-Start.

OCR-R07 – glossary_management versehentlich im Snapshot. Wahrscheinlichkeit: Mittel. Konsequenz: OCR_EXPORT_EVENT enthält semantisch falsche Decision-Events, die nicht den OCR-Quelltextzustand betreffen. Review-Pflicht: OCR-Decision-Snapshot-Allowlist-Test muss explizit prüfen, dass kein glossary_management-Eintrag im Array ist.

OCR-R08 – Alter export_confirmation-Eintrag im Snapshot. Wahrscheinlichkeit: Mittel. Konsequenz: Pflichtfragen-Bestätigungen aus früheren Exporten landen im Snapshot des aktuellen Exports. Review-Pflicht: OCR-Decision-Snapshot-Attempt-Bindung-Test grün.

OCR-R09 – decision_source-Feld nicht bei allen neuen Decision Events gesetzt. Wahrscheinlichkeit: Mittel. Konsequenz: decision_source ist null; Allowlist-Abfrage liefert falsche Ergebnisse oder schlägt fehl. Review-Pflicht: OCR-Gate-Decision-Event-Source-Test grün; Code-Review prüft alle Stellen im Sprint, die Decision Events anlegen.

OCR-R10 – exported_page_uuids enthält inaktive Seiten oder Seiten ausserhalb des aktuellen Projekts. Wahrscheinlichkeit: Mittel. Konsequenz: Page-scoped Decision Events inaktiver oder fremdprojektlicher Seiten landen im Snapshot. Review-Pflicht: OCR-Snapshot-Pages-Join-Test grün; Code-Review bestätigt active = true- und project_uuid-Filter.

### **7. Übergang zu T-OCR-EX-4**

T-OCR-EX-4 setzt T-OCR-EX-3 und T-10.2.1 voraus. Die ocr_revision_snapshot\[\]-Befüllung aus T-OCR-EX-3 ist die technische Grundlage für den späteren Lookup in T-OCR-EX-4 (get_ocr_exports_for_segment()).

### **A. Hard Gates**

HG-1 – T-OCR-EX-2 nicht ohne grünes T-OCR-EX-1. HG-2 – OCR-EXPORT_EVENT-Atomaritaet-Test und OCR-EXPORT_EVENT-Kein-Eintrag-Bei-Fehler-Test grün vor T-OCR-EX-3-Merge. HG-3 – RTL-Absatz-Test muss die Absatzebene nachweisen (nicht nur Dokumentebene). HG-4 – OCR-Gate-Vorabpruefung-Kein-Log-Test und OCR-Gate-Blockiert-Start-Kein-Log-Test grün vor T-OCR-EX-1-Merge. HG-5 – OCR-EXPORT_EVENT-Via-PROVENANCE-Kern-Test (Code-Review) grün. HG-6 – OCR-Decision-Snapshot-Allowlist-Test und OCR-Decision-Snapshot-Attempt-Bindung-Test grün vor T-OCR-EX-3-Merge. Kein glossary_management, kein preflight_confirmation, kein style_management, kein alter export_confirmation-Eintrag im Snapshot. HG-7 – CR-1.5 und CR-1.6 als Datenbankschema-Migration vorhanden, bevor T-OCR-EX-1 gestartet wird. Kein Sprint-Start ohne diese Schemaerweiterung.

### **B. Was bewusst nicht in diesem Sprint gehört**

T-OCR-EX-4, T-5.2.1-Kopplung, UI-Flow, Kalibrierung, DOCX-Bibliotheks-Entscheid (vor Sprint-Start zu treffen), Übersetzungs-Pipeline, Audit, Preflight, EXPORT_EVENT.

Migration bestehender Decision Events (decision_source-Feld auf bestehende Einträge): formal erforderlich (CR-1.5 Migrationsregel), aber kein Sprint-OCR-Scope. Wird als separater Migrationsschritt vor Sprint-Start eingeplant.

## **OFFEN GEBLIEBENE / NICHT BELASTBAR REKONSTRUIERBARE RESTPUNKTE**

1.  Ausformulierte Langfassungen der CRs CR-1.2, CR-1.3, CR-2.2, CR-2.3, CR-3.1, CR-3.2, CR-4.1 und CR-4.2 liegen in den drei Vorversionen nur in Form des CR-Überblicks und indirekter Verweise vor. In Abschnitt 2 dieses Dokuments sind sie in der Form dokumentiert, die aus dem Versionenkontext und dem aktuellen Waraq-Kanon belastbar ableitbar ist (Einfügestelle, Art, strukturelle Inhaltsbeschreibung). Wortgleiche Ursprungsfassungen sind nicht verfügbar und werden nicht rekonstruiert.

2.  Migrationsdetails für bestehende Decision Events (Heuristik für die Zuordnung von Altbeständen auf die zehn kanonischen Enum-Werte gemäss CR-1.5 sowie die Behandlung nicht klassifizierbarer Altbestände) sind in keiner der drei Vorversionen ausformuliert und bleiben einem separaten Migrationsarbeitsstand vorbehalten.

*Waraq OCR-Text-Export Konsolidierte Endfassung v1.3 – Ende*
