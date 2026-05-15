<!-- Converted from "DELIVERY BACKLOG BASELINE v1.0.docx" via pandoc 3.9.0.2 on 2026-05-02 -->
<!-- The .docx in this directory remains source-of-truth per docs/canon/README.md authority rule -->
<!-- Conversion is content-faithful (text, tables, identifiers, Swiss German ss, Arabic RTL spans, §-refs); Word-specific visual styling is dropped -->

*WARAQ DELIVERY BACKLOG BASELINE Version 1.0 – Ticketfähige Delivery-Struktur*

*Alle Begriffe, Modulnamen, Objektnamen und Invariantenbezeichnungen folgen ausschliesslich dem belegten Kanon (Dokument 1, Dokument 2, Block 3) und der Engineering Execution Baseline v1.0. Keine neuen Features. Keine neue Terminologie. Keine Änderung an der Kanon-Logik.*

*DEFINITION OF DONE (DoD) Vorangestellt, weil jedes Ticket gegen diese DoD geprüft wird. Ein Ticket gilt als done, wenn alle folgenden Bedingungen erfüllt sind:*

| ***Kriterium*** | ***Anforderung*** |
|----|----|
| *Code* | *Implementiert, reviewed, gemergt.* |
| *Tests* | *Alle für dieses Ticket verpflichtenden Tests grün. Kein Merge bei rotem T-H-Test.* |
| *Persistenz* | *Alle betroffenen Kernobjekte korrekt in Tabellen geschrieben. Kein Datenverlust bei Neustart.* |
| *Logs* | *Alle vorgeschriebenen Log-Einträge (Log-ID via EVENTING) erzeugt. Keine Revisions-UUID für Prüfoperationen.* |
| *Guard-Verhalten* | *INVARIANT-Guard ist aktiv und blockiert alle relevanten Verletzungen. Guard ist nicht deaktivierbar.* |
| *Scope-Korrektheit* | *Alle POs tragen korrektes scope_type + scope_uuid. Kein hard-coded satz_uuid-Pflichtfeld.* |
| *Nicht-Ziele eingehalten* | *Kein einziges Nicht-Ziel des Tickets wurde implementiert.* |
| *Regressionstests* | *Alle Regressionstests aus dem vorherigen Meilenstein bleiben grün.* |
| *Stilfeature-Test-Familien (CR-3)* | *Für Tickets der Familien F2 (Promotion / Stilregel-Entwicklung) und F3 (Audit / Konflikt / Marker) gemäss Abschnitt 7.1 sind die in CR-2 materiell definierten Stilfeature-Test-Familien als Akzeptanzkriterien zu erfüllen. Reine Verweis-Einbindung in die DBB-Planungslogik; keine inhaltliche Wiederholung der Test-Familien-Definition in dieser Baseline.* |

*TICKETFÄHIGE BACKLOG-EINHEITEN*

*Ticket-ID-Schema: T-{WS}.{AP}.{Seq} – z.B. T-1.1.1 = Workstream 1, AP 1.1, erstes Ticket.*

*WS-1: Fundament*

*T-1.1.1 – UUID-Vergabe-Service implementieren AP: AP-1.1 \| Meilenstein: M-1 \| Critical Path: Ja (Schritt 1) Ziel: new_uuid() als deterministischen, kollisionsfreien UUID-Generator implementieren. Scope: Reine Logik-Schicht. Keine eigene Datenbanktabelle. Betroffene Module: IDENTITY Betroffene Kernobjekte: Keine eigenen – liefert UUIDs für alle späteren Objekte. Betroffene Zustände / Transitionen: Keine. Betroffene Events / Provenance: Keine. Akzeptanzkriterien: ✓ new_uuid() erzeugt jedes Mal eine neue, einmalige UUID ✓ Zwei aufeinanderfolgende Aufrufe erzeugen immer verschiedene UUIDs ✗ Keine eigene Persistenz Nicht-Ziele: Keine Validierung externer UUIDs. Keine Datenbanktabelle. Abhängigkeiten: Keine. Kritische Risiken: Kollisionen bei parallelen Aufrufen, wenn kein kryptografisch sicherer Generator verwendet wird.*

*T-1.1.2 – UUID-Unveränderlichkeit und Inaktivierungslogik implementieren AP: AP-1.1 \| Meilenstein: M-1 \| Critical Path: Ja (Schritt 1) Ziel: assert_immutable(uuid) und mark_inactive(uuid) implementieren. UUID wird nie gelöscht, nur inaktiviert. Scope: Logik-Schicht. Wirkt auf alle späteren Tabellen mit UUID-Primärschlüssel + active-Flag. Betroffene Module: IDENTITY Betroffene Kernobjekte: Wird von Page, Block, Segment, Job konsumiert (active-Flag-Konvention). Betroffene Zustände / Transitionen: Keine eigene Zustandsmaschine. Betroffene Events / Provenance: Keine. Akzeptanzkriterien: ✓ mark_inactive(uuid) setzt active-Flag auf false, löscht nie ✓ assert_immutable(uuid) wirft Fehler, wenn versucht wird, eine vergebene UUID zu ändern ✗ Keine UUID wird jemals gelöscht oder recycelt Invarianten: H-5 Tests: T-H5-01, T-H5-02 Nicht-Ziele: Keine eigene Tabelle. Keine Validierung von Fremd-UUIDs. Abhängigkeiten: T-1.1.1. Kritische Risiken: active = false irrtümlich als Löschung behandelt; UUID-Feld in Tabellen als nullable angelegt, was spätere Recycling-Fehler ermöglicht.*

*T-1.2.1 – INVARIANT-Guard: Sperrflag-Schutz (H-1, H-2) AP: AP-1.2 \| Meilenstein: M-1 \| Critical Path: Ja (Schritt 2) Ziel: Guard-Funktion für H-1 und H-2: jede automatische Schreiboperation auf einem Segment mit aktivem lock_flag wird blockiert. Scope: Sperrschicht. Kein eigenes Datenbankschema. Prüft lock_flag-Feld im Segment-Schema (wird in T-1.3.1 angelegt). Betroffene Module: INVARIANT Betroffene Kernobjekte: Segment (lock_flag) Betroffene Zustände / Transitionen: Keine. Betroffene Events / Provenance: Bei Blockierung: internes technisches Log (kein Ereignis-Log-Eintrag). Akzeptanzkriterien: ✓ Automatische Schreiboperation auf Segment mit lock_flag = manual_local → blockiert ✓ Automatische Schreiboperation auf Segment mit lock_flag = manual_editorial → blockiert ✓ Manuelle Schreiboperation mit explizitem Bestätigungs-Kontext → erlaubt ✗ Guard ist nicht deaktivierbar Invarianten: H-1, H-2 Tests: T-H1-01, T-H1-02 Nicht-Ziele: Keine Auflösungslogik. Keine UI-Meldung direkt aus Guard. Abhängigkeiten: T-1.1.1, T-1.1.2. Kritische Risiken: Guard wird als optionales Middleware-Layer implementiert, das per Konfiguration ausschaltbar ist.*

*T-1.2.2 – INVARIANT-Guard: Revisions-UUID-Schutz (H-4), UUID-Schutz (H-5), Konfliktmeldung (H-6), Promotion-Schutz (H-7) AP: AP-1.2 \| Meilenstein: M-1 \| Critical Path: Ja (Schritt 2) Ziel: H-4 (keine Revisions-UUID für Prüfoperationen), H-5 (UUID-Unveränderlichkeit), H-6 (kein stilles Auflösen von Terminologie/Sperrflag-Konflikten), H-7 (kein automatisches Promote) als Guard-Schicht. Scope: Erweiterung des Guards aus T-1.2.1 um die verbleibenden Invarianten. Betroffene Module: INVARIANT Betroffene Kernobjekte: Revision (Typ-Check), alle UUID-Objekte (Unveränderlichkeit) Betroffene Zustände / Transitionen: Keine. Betroffene Events / Provenance: Keine POs. Bei H-6-Verletzungsversuch: Konflikt als offen markieren, nicht still auflösen. Akzeptanzkriterien: ✓ Versuch Revisions-UUID für Prüfoperation → blockiert (H-4) ✓ Versuch UUID zu ändern → blockiert (H-5) ✓ Terminologie-Anwendung auf gesperrtes Segment → Konflikt gemeldet, nie still aufgelöst (H-6) ✓ Automatische Stilregel-Ableitung ohne Promotion-Pipeline → blockiert (H-7) ✗ Guard ist nicht deaktivierbar Tests: T-H2-01, T-H2-02, T-H4-01, T-H4-02, T-H6-01, T-H7-01 Nicht-Ziele: Keine Konfliktauflösung. Keine UI-Meldungen. Abhängigkeiten: T-1.2.1. Kritische Risiken: H-6 als „Warnung" statt Blockade implementiert; H-4 nur für manuelle Operationen geprüft, nicht für automatische Pipelines.*

*T-1.3.1 – Kernobjekt-Schemas: Project, Page, Block, Segment AP: AP-1.3 \| Meilenstein: M-1 \| Critical Path: Ja (Schritt 3) Ziel: Datenbank-Schemas für Project, Page, Block, Segment anlegen. Project als kanonisches Wurzelobjekt mit project_uuid. Scope: Nur Schema-Definition und Migrationen. Keine Anwendungslogik. Betroffene Module: IDENTITY (UUID-Felder), keine Anwendungsmodule Betroffene Kernobjekte:*

- *Project (project_uuid, display_name, created_at, active)*

- *Page (page_uuid, project_uuid FK, ocr_status, completion_mark, active)*

- *Block (block_uuid, page_uuid FK, block_type, sequence, active)*

- *Segment (satz_uuid, block_uuid FK, lock_flag, active, current_rev_uuid, translation_uuid) Betroffene Zustände / Transitionen: Keine Logik – nur Schema. Betroffene Events / Provenance: Keine. Akzeptanzkriterien: ✓ Alle vier Tabellen mit korrekten FKs angelegt ✓ project_uuid ist Primärschlüssel der Project-Tabelle, nicht nullable ✓ lock_flag-Enum in Segment-Tabelle: none \| manual_local \| manual_editorial ✓ Decision-Event-Schema akzeptiert scope_type = project mit gültiger project_uuid ✗ Keine Anwendungslogik in diesem Ticket Nicht-Ziele: Kein Befüllen der Tabellen. Keine Indizes für Query-Optimierung (folgt später). Abhängigkeiten: T-1.1.1, T-1.2.1. Kritische Risiken: project_uuid als nullable angelegt; lock_flag als freier String statt Enum.*

*T-1.3.2 – Kernobjekt-Schemas: Revision, Decision Event, Log-Eintrag, EXPORT_EVENT AP: AP-1.3 \| Meilenstein: M-1 \| Critical Path: Ja (Schritt 3) Ziel: Schemas für die drei Identitätstypen und EXPORT_EVENT. Strikte Trennung in separaten Tabellen. Scope: Schema-Definition. Keine Anwendungslogik. EXPORT_EVENT-Tabelle wird angelegt, aber erst in WS-9 befüllt. Betroffene Module: REVISION, EVENTING, EXPORT (Schema-Vorbereitung) Betroffene Kernobjekte:*

- *Revision (rev_uuid, satz_uuid FK, text_before, text_after, change_source Enum, confidence?, created_at)*

- *Decision Event (decision_event_uuid, scope_type Enum, scope_uuid, decision_type, content JSONB, created_at)*

- *Log-Eintrag (log_id, operation_type Enum, scope_uuid?, result JSONB, created_at)*

- *EXPORT_EVENT (export_uuid, project_uuid FK, export_type, export_config JSONB, revision_snapshot UUID\[\], active_decision_event_uuids UUID\[\], artefact_ref, created_at) Betroffene Zustände / Transitionen: Keine Logik. Betroffene Events / Provenance: Keine. Akzeptanzkriterien: ✓ Revision, Decision Event, Log-Eintrag sind in drei getrennten Tabellen ✓ change_source in Revision ist Enum: manual \| ocr \| re_translate \| style_profile ✓ scope_type in Decision Event ist Enum: segment \| page \| block \| account \| project ✓ EXPORT_EVENT-Tabelle angelegt, noch nicht befüllt ✗ Kein gemeinsames „Events"-Schema, das alle drei Typen vermischt Nicht-Ziele: Kein Befüllen. Keine Abfragelogik. Abhängigkeiten: T-1.3.1. Kritische Risiken: Alle drei Identitätstypen in einer Tabelle mit type-Diskriminator zusammengefasst – dies bricht die konzeptuelle Trennung.*

*T-1.3.3 – Kernobjekt-Schemas: Job, Checkpoint, Konzept-ID / Glossar-Eintrag, Provenance-Tabelle AP: AP-1.3 \| Meilenstein: M-1 \| Critical Path: Ja (Schritt 3) Ziel: Schemas für Job, Checkpoint, Konzept-ID und generische Provenance-Tabelle. Scope: Schema-Definition. Keine Anwendungslogik. Betroffene Module: JOB, PROVENANCE, GLOSSARY (Schema-Vorbereitung) Betroffene Kernobjekte:*

- *Job (job_uuid, job_type Enum, scope_type, scope_uuid, state Enum, retry_budget, retry_count, parent_job_uuid?, started_at, updated_at, terminal_at?)*

- *Checkpoint (checkpoint_uuid, job_uuid FK, checkpoint_type Enum, progress_marker, resume_state JSONB, created_at)*

- *Konzept-ID (concept_id, display_forms String\[\], translation, entry_type Enum, binding_level Enum, created_at, updated_at)*

- *Provenance (po_uuid, po_type Enum, scope_type Enum, scope_uuid, payload JSONB, created_at) Betroffene Zustände / Transitionen: Keine Logik. Betroffene Events / Provenance: Keine. Akzeptanzkriterien: ✓ Job-state ist Enum mit allen definierten Zuständen ✓ Provenance-Tabelle hat scope_type + scope_uuid, kein satz_uuid-Pflichtfeld ✓ Checkpoint hat resume_state JSONB für serialisierten Wiederaufnahmezustand ✗ Kein satz_uuid NOT NULL in der Provenance-Tabelle Nicht-Ziele: Kein Befüllen. Keine Anwendungslogik. Abhängigkeiten: T-1.3.2. Kritische Risiken: Provenance-Tabelle mit satz_uuid NOT NULL angelegt – bricht Scope-Modell für page-scoped und project-scoped POs.*

*T-1.4.1 – REVISION-Service: create_revision implementieren AP: AP-1.4 \| Meilenstein: M-1 \| Critical Path: Ja (Schritt 4) Ziel: create_revision(satz_uuid, before, after, source) implementieren. Revisions-UUID nur bei tatsächlicher Textänderung. Scope: Service-Logik. Schreibt in Revision-Tabelle. Betroffene Module: REVISION, IDENTITY, INVARIANT Betroffene Kernobjekte: Revision Betroffene Zustände / Transitionen: Keine. Betroffene Events / Provenance: Keine POs. Akzeptanzkriterien: ✓ create_revision() mit identischem before/after → kein Eintrag, kein Fehler ✓ create_revision() mit abweichendem after → Revisions-UUID angelegt ✓ change_source-Pflichtfeld muss gefüllt sein ✗ Keine Revisions-UUID bei reiner Prüfoperation Invarianten: H-4 Tests: T-H4-01 Nicht-Ziele: Kein Textdiff im Service. Keine Decision-Event-Logik. Abhängigkeiten: T-1.3.2, T-1.2.1. Kritische Risiken: before/after-Vergleich auf Byte-Ebene statt semantisch – führt zu Phantom-Revisionen bei Encoding-Unterschieden.*

*T-1.4.2 – REVISION-Service: create_decision_event implementieren AP: AP-1.4 \| Meilenstein: M-1 \| Critical Path: Ja (Schritt 4) Ziel: create_decision_event(scope_type, scope_uuid, decision_type, content) implementieren. Erzeugt Decision-Event-UUID. Nie für Textrevisionen. Scope: Service-Logik. Schreibt in Decision-Event-Tabelle. Betroffene Module: REVISION, IDENTITY, INVARIANT Betroffene Kernobjekte: Decision Event Betroffene Zustände / Transitionen: Keine. Betroffene Events / Provenance: Keine POs. Akzeptanzkriterien: ✓ Decision-Event-UUID erzeugt für scope_type = segment, page, block, account, project ✓ Kein Textrevisions-Feld in Decision Event ✗ Keine Decision-Event-UUID für Textrevisionen Invarianten: H-4 Tests: T-H4-02 Nicht-Ziele: Kein Log-ID-Management. Abhängigkeiten: T-1.4.1. Kritische Risiken: Decision Event mit optionalem text_after-Feld angelegt „für den Fall" – bricht konzeptuelle Trennung.*

*T-1.5.1 – EVENTING-Service: log_event implementieren AP: AP-1.5 \| Meilenstein: M-1 \| Critical Path: Nein (parallel zu T-1.4.x möglich) Ziel: log_event(operation_type, scope_uuid?, result) implementieren. Log-ID-Vergabe. Strikt getrennt von Revision- und Decision-Event-Tabellen. Scope: Service-Logik. Schreibt ausschliesslich in Log-Eintrag-Tabelle. Betroffene Module: EVENTING, IDENTITY Betroffene Kernobjekte: Log-Eintrag Betroffene Zustände / Transitionen: Keine. Betroffene Events / Provenance: Keine POs. Akzeptanzkriterien: ✓ log_event() schreibt in Log-Eintrag-Tabelle, nirgendwo sonst ✓ Log-ID ist eine UUID (kein Autoincrement-Integer) ✗ Kein Schreiben in Revision- oder Decision-Event-Tabellen Tests: Trennungs-Test: Log-Eintrag anlegen → nicht in Revisions- oder Decision-Event-Tabelle. Nicht-Ziele: Kein Schreiben in andere Tabellen. Abhängigkeiten: T-1.3.2. Kritische Risiken: EVENTING und REVISION teilen sich eine gemeinsame „Events"-Tabelle mit type-Diskriminator.*

*T-1.6.1 – PROVENANCE-Kern: create_po implementieren AP: AP-1.6 \| Meilenstein: M-1 \| Critical Path: Ja (Schritt 5) Ziel: create_po(po_type, scope_type, scope_uuid, payload) implementieren. POs nach Anlage unveränderlich. scope_type + scope_uuid korrekt gesetzt. Scope: Service-Logik. Schreibt in Provenance-Tabelle. Betroffene Module: PROVENANCE (Kern), IDENTITY Betroffene Kernobjekte: Provenance (generische Tabelle) Betroffene Zustände / Transitionen: Keine. Betroffene Events / Provenance: Ist selbst der PO-Erzeuger. Akzeptanzkriterien: ✓ PO wird mit korrektem po_type, scope_type, scope_uuid angelegt ✓ PO nach Anlage unveränderlich: Änderungsversuch → Fehler ✓ scope_type = page akzeptiert; scope_type = project akzeptiert; scope_type = artefact akzeptiert ✗ Kein satz_uuid-Pflichtfeld in der PO-Tabelle Tests: Smoke-Test: PO anlegen, Änderungsversuch → Fehler. Nicht-Ziele: Kein Abfragen. Kein Why-Panel. Kein EXPORT_EVENT. Abhängigkeiten: T-1.3.3, T-1.4.2, T-1.5.1. Kritische Risiken: create_po() nimmt satz_uuid als Pflichtparameter statt scope_type + scope_uuid – schliesst page-scoped POs strukturell aus.*

*WS-2: Job-Infrastruktur*

*T-2.1.1 – Job-Zustandsmaschine implementieren AP: AP-2.1 \| Meilenstein: M-1 \| Critical Path: Ja (Schritt 6) Ziel: Job-Tabelle befüllen. Alle erlaubten Zustandsübergänge aus ITB 3.1/3.2/3.5 implementieren. Transient vs. terminal klar getrennt. Scope: Job-Service-Logik. Schreibt in Job-Tabelle. Betroffene Module: JOB, IDENTITY, EVENTING Betroffene Kernobjekte: Job (alle Felder) Betroffene Zustände / Transitionen: pending → aktiv → deferred → pausiert → teilweise_fehlgeschlagen → abgeschlossen \| fehlgeschlagen \| bereinigt. Deferred → Auto-Retry. Fehlgeschlagen → kein Auto-Retry. Betroffene Events / Provenance: Log-Eintrag bei relevanten Zustandsänderungen (EVENTING). Akzeptanzkriterien: ✓ Alle erlaubten Übergänge implementiert ✓ Deferred löst Auto-Retry aus (bis retry_budget erschöpft, dann → fehlgeschlagen) ✓ Fehlgeschlagen löst keinen Auto-Retry aus ✓ job_uuid bleibt bei Wiederaufnahme unverändert ✗ Kein erzwungener Neustart Tests: T-REC-05 Nicht-Ziele: Kein Upload-Logik. Kein OCR-Logik. Abhängigkeiten: T-1.3.3, T-1.5.1. Kritische Risiken: Fehlgeschlagen erhält Auto-Retry-Mechanismus „weil Deferred ja auch funktioniert".*

*T-2.1.2 – Checkpoint-Schreiben und -Lesen implementieren AP: AP-2.1 \| Meilenstein: M-1 \| Critical Path: Ja (Schritt 6) Ziel: Checkpoint nach jeder definierten Einheit persistent schreiben. Wiederaufnahme liest letzten Checkpoint. Nie Neustart ab Job-Beginn. Scope: Checkpoint-Service-Logik. Schreibt in Checkpoint-Tabelle. Betroffene Module: JOB Betroffene Kernobjekte: Checkpoint (alle Felder inkl. resume_state JSONB) Betroffene Zustände / Transitionen: Wiederaufnahme ab letztem Checkpoint: Job-state wechselt von pausiert → aktiv, liest letzten Checkpoint-Eintrag. Betroffene Events / Provenance: Keine. Akzeptanzkriterien: ✓ Nach Unterbrechung: Wiederaufnahme ab letztem Checkpoint, nicht ab Jobstart ✓ resume_state JSONB korrekt serialisiert und deserialisiert ✓ Mehrere Checkpoints für denselben Job: letzter wird verwendet ✗ Kein Neustart von null Tests: T-REC-01, T-REC-02 Nicht-Ziele: Kein Upload oder OCR in diesem Ticket. Abhängigkeiten: T-2.1.1. Kritische Risiken: resume_state nicht atomisch geschrieben – Checkpoint korrupt nach Absturz während des Schreibens.*

*WS-3: Upload-Pipeline*

*T-3.1.1 – Chunked Upload: Chunk-Empfang, Hash-Prüfung und Page-Materialisierung AP: AP-3.1 \| Meilenstein: M-2 \| Critical Path: Nein (ermöglicht OCR, aber Upload selbst nicht auf critical path) Ziel: Server empfängt Chunks, prüft Hash-Prüfsumme, speichert Chunk persistent. Upload-Job und Chunk-Checkpoints werden angelegt. Page-Objekte für alle Seiten des Uploads werden materialisiert und erhalten ihre kanonischen page_uuids. Scope: Upload-Empfang, Chunk-Persistenz und Page-Materialisierung. Betroffene Module: UPLOAD, JOB, IDENTITY Betroffene Kernobjekte: Job (job_type = upload), Checkpoint (checkpoint_type = chunk, progress_marker = Chunk-Nummer), Page (page_uuid, project_uuid FK) Betroffene Zustände / Transitionen: Upload-Job: pending → aktiv. Checkpoint nach jedem bestätigten Chunk. Page-Materialisierung: Page-Objekte werden aus der Dokumentstruktur (PDF-Seitenanzahl oder Scan-Dateiliste) beim Upload-Start angelegt – jede Seite erhält eine page_uuid. Betroffene Events / Provenance: Keine POs in diesem Ticket (SCAN-PO folgt in T-3.1.2 nach Upload-Abschluss). Page-Materialisierungs-Entscheidung:*

- *Quelle: Seitenliste aus dem hochgeladenen Dokument (PDF-Seitenanzahl oder geordnete Scan-Dateiliste)*

- *Zeitpunkt: Page-Objekte werden beim ersten Empfang der Upload-Metadaten angelegt, bevor die eigentlichen Chunks ankommen*

- *page_uuids werden via IDENTITY-Service generiert*

- *Bei erneutem Upload derselben Datei (Seitenersatz): bestehende page_uuids bleiben erhalten (Lineage-Logik, folgt WS-4). Kein Neuanlegen von Page-Objekten für bereits bekannte Seiten.*

- *Page-Objekte werden mit ocr_status = ausstehend angelegt Akzeptanzkriterien: ✓ Jeder Chunk nach Hash-Bestätigung in Checkpoint persistiert ✓ Fehlerhafter Hash → Chunk abgelehnt, Job bleibt aktiv ✓ Alle Page-Objekte mit page_uuid angelegt, bevor Chunks verarbeitet werden ✓ page_uuid ist nicht nullable, referenziert project_uuid als FK ✓ ocr_status der Page bei Anlage = ausstehend ✓ Bei Seitenersatz: keine neuen page_uuids für bereits existierende Seiten ✗ UPLOAD schreibt keine POs ✗ Kein OCR-Start Nicht-Ziele: Kein SCAN-PO (folgt T-3.1.2). Kein Block- oder Segment-Schreiben. Abhängigkeiten: T-2.1.2, T-1.3.1 (Page-Schema). Kritische Risiken: Page-Objekte werden erst nach Upload-Abschluss angelegt statt beim Upload-Start – T-3.1.2 (SCAN-PO) und T-4.1.1 (OCR) benötigen page_uuids bereits beim Start. Ausserdem: Chunks in Memory gepuffert statt nach jedem Chunk persistiert – Datenverlust bei Absturz.*

*T-3.1.2 – Chunked Upload: Wiederaufnahme und SCAN-PO-Anlage AP: AP-3.1 \| Meilenstein: M-2 \| Critical Path: Nein Ziel: Wiederaufnahme ab letztem bestätigtem Chunk. Nach Upload-Abschluss: PROVENANCE-Kern legt SCAN-PO an (scope_type = page). Scope: Upload-Recovery und Post-Upload-Event. Betroffene Module: UPLOAD, JOB, PROVENANCE Betroffene Kernobjekte: Checkpoint (letzter bestätigter Chunk), Page (page_uuid für SCAN-PO), Provenance (SCAN-PO) Betroffene Zustände / Transitionen: Upload-Job: pausiert → aktiv (Wiederaufnahme). Nach letztem Chunk: abgeschlossen. Danach SCAN-PO-Anlage. Betroffene Events / Provenance: SCAN-PO (po_type = SCAN, scope_type = page, scope_uuid = page_uuid, payload = Metadaten). Angelegt von PROVENANCE-Kern, nicht von UPLOAD. Akzeptanzkriterien: ✓ Wiederaufnahme startet ab Chunk N+1, nicht von Chunk 1 ✓ Nach Abschluss: SCAN-PO angelegt mit scope_type = page ✗ UPLOAD schreibt selbst keine POs Tests: T-REC-01 Nicht-Ziele: Kein OCR-Start. Kein Schreiben von Block- oder Segment-Tabellen. Abhängigkeiten: T-3.1.1, T-1.6.1. Kritische Risiken: SCAN-PO wird synchron im Upload-Handler geschrieben statt nach Job-Abschluss-Event durch PROVENANCE-Kern.*

*WS-4: OCR-Pipeline*

*T-4.1.1 – OCR-Job: Seitenverarbeitung und Block-/Segment-Anlage AP: AP-4.1 \| Meilenstein: M-2 \| Critical Path: Ja (Schritt 7) Ziel: OCR-Durchlauf pro Seite, Block- und Satz-UUIDs anlegen, Checkpoint nach jeder Seite. Scope: OCR-Kernverarbeitung. Schreibt Block- und Segment-Tabellen. Betroffene Module: OCR, JOB, IDENTITY Betroffene Kernobjekte: Job (job_type = ocr), Checkpoint (checkpoint_type = page), Block, Segment Betroffene Zustände / Transitionen: OCR-Job: pending → aktiv. Checkpoint nach jeder Seite. Betroffene Events / Provenance: Keine POs in diesem Ticket (folgt T-4.1.2). Akzeptanzkriterien: ✓ Block- und Satz-UUIDs für jede Seite korrekt angelegt ✓ Checkpoint nach jeder Seite persistent ✗ Kein Sperrflag-Setzen ✗ Kein automatischer Übersetzungsstart nach OCR Tests: T-REC-02 Nicht-Ziele: Kein OCR-PO (folgt T-4.1.2). Keine Fehlerklassen-Erkennung (folgt T-4.1.3). Abhängigkeiten: T-3.1.2, T-2.1.2. Kritische Risiken: Block- und Satz-UUIDs werden nach Seiten-Neuberechnung recycelt statt neue UUIDs vergeben oder inaktiviert.*

*T-4.1.2 – OCR-Job: OCR-PO-Anlage und Revisions-UUID bei Textänderung AP: AP-4.1 \| Meilenstein: M-2 \| Critical Path: Ja (Schritt 7) Ziel: OCR-PO nach jedem Durchlauf via PROVENANCE-Kern anlegen. Revisions-UUID nur, wenn OCR-Text von vorherigem Stand abweicht. Scope: Provenance-Schreiben aus OCR-Pipeline. Betroffene Module: OCR, PROVENANCE, REVISION, EVENTING Betroffene Kernobjekte: Provenance (OCR-PO), Revision (wenn Textänderung), Log-Eintrag (je Durchlauf) Betroffene Zustände / Transitionen: Keine eigenen – wird nach T-4.1.1-Verarbeitung ausgeführt. Betroffene Events / Provenance: OCR-PO (po_type = OCR, scope_type = segment, scope_uuid = satz_uuid, payload = engine, konfidenz, fehlerklassen\[\]). Log-Eintrag je Durchlauf. Akzeptanzkriterien: ✓ OCR-PO nach jedem Durchlauf angelegt ✓ Revisions-UUID nur, wenn OCR-Text ≠ vorheriger Text ✓ Kein OCR-PO bei reinem Prüflauf ohne Textausgabe ✗ Keine Revisions-UUID für OCR-Qualitätsprüflauf Invarianten: H-4 Tests: T-H4-01 Nicht-Ziele: Keine Fehlerklassen-Erkennung (folgt T-4.1.3). Abhängigkeiten: T-4.1.1, T-1.6.1, T-1.4.1, T-1.5.1. Kritische Risiken: OCR-Prüflauf ohne Textänderung erzeugt trotzdem Revisions-UUID „zur Dokumentation".*

*T-4.1.3 – OCR-Fehlerklassen-Profiling (F-01 bis F-09) AP: AP-4.1 \| Meilenstein: M-2 \| Critical Path: Ja (Schritt 7) Ziel: Fehlerklassen F-01 bis F-09 pro Seite erkennen, als ocr_error_instance persistieren. Scope: Fehlerklassen-Erkennung und Persistenz. Betroffene Module: OCR Betroffene Kernobjekte: ocr_error_instance (error_class, page_uuid, block_uuid?, severity, resolved = false) Betroffene Zustände / Transitionen: OCR-Freigabestatus pro Page bleibt ausstehend (wird in T-4.3.1 berechnet). Betroffene Events / Provenance: Keine neuen POs. Fehlerklassen werden im OCR-PO-Payload mitgeführt (via T-4.1.2). Akzeptanzkriterien: ✓ Alle neun Fehlerklassen (F-01 bis F-09) erkennbar ✓ Schweregrad (kritisch / hoch / mittel) korrekt zugeordnet ✓ ocr_error_instance korrekt angelegt mit resolved = false ✗ Kein automatisches Auflösen von Fehlerklassen Nicht-Ziele: Kein OCR-Review-Status (folgt T-4.3.1). Abhängigkeiten: T-4.1.2. Kritische Risiken: Schweregrade hart kodiert statt aus konfigurierbarer Tabelle gelesen – macht spätere Kalibrierung unmöglich.*

*T-4.2.1 – Lineage: 1→1-Matching und Inaktivierung (1→0) AP: AP-4.2 \| Meilenstein: M-2 \| Critical Path: Nein (parallel zu T-4.1.x) Ziel: Bei Seitenersatz oder Re-Segmentierung: 1→1-Matching auf bestehende Satz-UUIDs. Verschwundene Segmente → inaktiv (nie gelöscht). LINEAGE_EVENT-PO für beide Typen. Scope: UUID-Matching-Logik für die häufigsten Lineage-Typen. Betroffene Module: LINEAGE, IDENTITY, EVENTING, PROVENANCE Betroffene Kernobjekte: Segment (active-Flag), Provenance (LINEAGE_EVENT-PO) Betroffene Zustände / Transitionen: Segment: active = true → active = false (1→0). Segment: UUID bleibt erhalten (1→1). Betroffene Events / Provenance: LINEAGE_EVENT-PO (scope_type = segment, automatisch: true). Log-Eintrag (EVENTING). Akzeptanzkriterien: ✓ 1→1: bestehende satz_uuid bleibt erhalten ✓ 1→0: satz_uuid auf active = false gesetzt, nicht gelöscht ✓ LINEAGE_EVENT-PO mit automatisch: true, keine Decision-Event-UUID ✗ Keine UUID-Löschung Invarianten: H-5 Tests: T-H5-01, T-H5-02 Nicht-Ziele: Kein 1→n oder n→1 (folgt T-4.2.2). Abhängigkeiten: T-4.1.1, T-1.6.1. Kritische Risiken: Inaktivierte Segmente werden bei Neuberechnung als „neu" behandelt und erhalten neue satz_uuids statt Reaktivierung.*

*T-4.2.2 – Lineage: Aufspaltung (1→n), Zusammenführung (n→1), Reaktivierung AP: AP-4.2 \| Meilenstein: M-2 \| Critical Path: Nein Ziel: Aufspaltung und Zusammenführung mit korrekten Herkunfts-UUID-Metadaten. Reaktivierung inaktiver UUIDs vor Neuanlage versucht. Scope: Erweiterte Lineage-Typen. Betroffene Module: LINEAGE, IDENTITY, EVENTING, PROVENANCE Betroffene Kernobjekte: Segment (Reaktivierung: active = false → true), Provenance (LINEAGE_EVENT-PO mit herkunft_uuid\[\], ziel_uuid\[\]) Betroffene Zustände / Transitionen: Reaktivierung: active = false → true. Aufspaltung: alte UUID → inaktiv. Zusammenführung: beide alten UUIDs → inaktiv. Betroffene Events / Provenance: LINEAGE_EVENT-PO mit vollständigen herkunft_uuid\[\] und ziel_uuid\[\]. Akzeptanzkriterien: ✓ 1→n: Herkunfts-UUID in LINEAGE_EVENT-PO referenziert ✓ n→1: beide Herkunfts-UUIDs referenziert ✓ Reaktivierung: inaktive UUID vor Neuanlage geprüft und reaktiviert, wenn plausibel ✗ Keine Decision-Event-UUID für automatische Vorgänge Tests: T-H5-01 Nicht-Ziele: Manuelle Zuordnungsentscheidung (folgt separatem Ticket, falls erforderlich). Abhängigkeiten: T-4.2.1. Kritische Risiken: Reaktivierungslogik fehlt – jede Re-Segmentierung erzeugt neue UUIDs und bricht die Revisionshistorie.*

*T-4.3.1 – OCR-Review-Status: Go/No-Go-Berechnung pro Seite AP: AP-4.3 \| Meilenstein: M-2 \| Critical Path: Ja (wird von AP-6.1 benötigt) Ziel: Page-OCR-Status (go / go_with_warning / no_go) aus Fehlerklassen-Profil berechnen. Aggregationslogik konfigurierbar. Scope: Statusberechnung und Persistenz am Page-Objekt. Betroffene Module: OCR, JOB Betroffene Kernobjekte: Page (ocr_status), ocr_error_instance (resolved-Flag) Betroffene Zustände / Transitionen: OCR-Review: ausstehend → in_review → go \| go_with_warning \| no_go. Betroffene Events / Provenance: Decision-Event-UUID, wenn Nutzer Auflösung trifft (scope_type = page, via REVISION). Log-Eintrag für Prüfläufe. Akzeptanzkriterien: ✓ Seite mit offener kritischer Fehlerklasse → ocr_status = no_go ✓ Seite ohne kritische, mit nicht-kritischer Fehlerklasse → go_with_warning ✓ Alle aufgelöst → go ✓ Aggregations-Schwellenwert konfigurierbar, nicht hart kodiert ✗ Kein automatisches Setzen von go ohne Nutzeraktion bei no_go Tests: Integrations-Test: F-01 → no_go; alle resolved → go. Nicht-Ziele: Keine Freigabeschranke (folgt WS-6). Abhängigkeiten: T-4.1.3. Kritische Risiken: Schwellenwert für Aggregationslogik hart kodiert – verhindert spätere Kalibrierung ohne Code-Änderung.*

*WS-5: Schutz- und Entscheidungsschicht*

*T-5.1.1 – LOCK: Sperrflag setzen und aufheben AP: AP-5.1 \| Meilenstein: M-3 \| Critical Path: Ja (Teil des gemeinsamen Gates für AP-6.1) Ziel: set_lock(satz_uuid, level) und release_lock(satz_uuid) implementieren. Sperrflag-Setzen erzeugt Decision-Event-UUID. Scope: Sperrflag-Verwaltung. Betroffene Module: LOCK, INVARIANT, REVISION Betroffene Kernobjekte: Segment (lock_flag), Decision Event (scope_type = segment) Betroffene Zustände / Transitionen: lock_flag: none → manual_local \| manual_editorial. Aufheben: manual_local → none (kein Dialog). manual_editorial → none (mit Bestätigungs-Dialog erforderlich). Betroffene Events / Provenance: Decision-Event-UUID bei Sperrflag-Setzen und Aufheben (via REVISION). MANUAL\_-PO via PROVENANCE-Kern. Akzeptanzkriterien: ✓ Sperrflag-Setzen erzeugt Decision-Event-UUID ✓ Aufheben von Sperrebene 2 erfordert Bestätigungs-Dialog-Kontext ✓ MANUAL\_-PO korrekt angelegt ✗ Kein automatisches Aufheben von Sperrflags Invarianten: H-1, H-2 Tests: T-H1-01, T-H1-02 Nicht-Ziele: Keine Konfliktbehandlung (folgt T-5.1.2). Abhängigkeiten: T-1.4.2, T-1.6.1. Kritische Risiken: Sperrflag-Setzen ohne Decision-Event-UUID implementiert – macht Entscheidungshistorie lückenhaft.*

*T-5.1.2 – LOCK: Konflikt-Erkennung und persistente Konflikt-Instanz AP: AP-5.1 \| Meilenstein: M-3 \| Critical Path: Ja (Teil des gemeinsamen Gates für AP-6.1) Ziel: detect_conflict(satz_uuid, rule_source) implementieren. Jeder erkannte Konflikt wird als persistenter conflict_instance-Eintrag gespeichert (Zustand = offen). Nie still aufgelöst. Decision-Event-UUID erst bei Auflösung. Scope: Konflikterkennungs-Logik und Konflikt-Persistenz. Betroffene Module: LOCK, INVARIANT, REVISION, EVENTING Betroffene Kernobjekte:*

- *Segment (lock_flag)*

- *conflict_instance (neuer persistenter Eintrag): conflict_uuid, satz_uuid FK, rule_source (Konzept-ID oder Regelkennung), conflict_type Enum (glossar_vs_sperrflag \| terminologie_vs_sperrflag \| ...), state Enum (offen \| aufgelöst), resolution_type Enum? (lokale_ausnahme \| glossar_anpassen \| sperrflag_aufheben), decision_event_uuid? FK → Decision Event (nur bei Auflösung), detected_at Timestamp, resolved_at Timestamp?*

- *Decision Event (scope_type = segment, nur bei Auflösung) Betroffene Zustände / Transitionen: conflict_instance.state: offen → aufgelöst (drei Auflösungsoptionen). Kein automatischer Übergang. Betroffene Events / Provenance: Keine POs für die Erkennung selbst. Decision-Event-UUID bei Auflösung (via REVISION). Log-Eintrag bei Konflikt-Erkennung (EVENTING). Akzeptanzkriterien: ✓ Terminologie-Anwendung auf gesperrtes Segment → conflict_instance mit state = offen angelegt ✓ Kein automatischer Sieger bei Konflikt ✓ Drei Auflösungsoptionen: (a) lokale Ausnahme, (b) Glossareintrag anpassen, (c) Sperrflag aufheben ✓ Bei Auflösung: conflict_instance.state → aufgelöst, resolution_type gesetzt, decision_event_uuid gesetzt ✓ Offene conflict_instances sind jederzeit abfragbar (Query: alle offenen Konflikte für ein Segment / für ein Projekt) ✗ Kein stilles Auflösen: state = offen bleibt ohne explizite Nutzeraktion Invarianten: H-6 Tests: T-H2-01, T-H2-02, T-H6-01 Nicht-Ziele: Keine automatische Auflösung unter keiner Bedingung. conflict_instance ist kein PO – kein Schreiben via PROVENANCE-Kern. Abhängigkeiten: T-5.1.1. Kritische Risiken: Konflikt nur in-memory gehalten statt persistent – nach Server-Neustart gehen offene Konflikte verloren und gesperrte Segmente könnten unbemerkt überschrieben werden. Zweites Risiko: conflict_instance mit Decision-Event-UUID bei Erkennung statt erst bei Auflösung angelegt.*

*T-5.2.1 – GLOSSARY: Konzept-IDs und Verzeichniseinträge verwalten AP: AP-5.2 \| Meilenstein: M-3 \| Critical Path: Ja (Teil des gemeinsamen Gates für AP-6.1) Ziel: lookup(surface_form), get_entry(concept_id), create_entry(), update_entry() implementieren. Einträge gewinnen gegen alle automatischen Systemkomponenten. Scope: Glossar-Service-Logik. Betroffene Module: GLOSSARY Betroffene Kernobjekte: Konzept-ID / Glossar-Eintrag Betroffene Zustände / Transitionen: Keine. Betroffene Events / Provenance: RULE_BINDING-PO, wenn Eintrag auf Segment angewandt wird (folgt T-7.2.1). Decision-Event-UUID bei Eintrag-Änderung. Akzeptanzkriterien: ✓ lookup() liefert Konzept-ID für Oberflächenform ✓ Eintrag-Änderung erzeugt Decision-Event-UUID ✗ Kein automatisches Überschreiben von gesperrten Segmenten durch Glossar ✗ Kein automatisches Erzeugen von Einträgen aus externen Quellen Tests: T-KE-01 Nicht-Ziele: Kein Durchsetzen in der Übersetzungspipeline (folgt T-7.2.1). Abhängigkeiten: T-1.4.2. Kritische Risiken: lookup() gibt bei Nicht-Treffer silent null zurück statt explizit „kein Eintrag" – führt zu unerkannten fehlenden Verzeichniseinträgen.*

*WS-6: Freigabeschranke*

*T-6.1.1 – Freigabeschranken-Logik: Freigabebedingungen prüfen AP: AP-6.1 \| Meilenstein: M-3 \| Critical Path: Ja (Schritt 9) Ziel: Alle fünf Freigabebedingungen (D.2) prüfen. Kein automatischer Übersetzungsstart. Scope: Zustandslogik. Kein eigenes Modul. Betroffene Module: Logik zwischen OCR-Review-Status (WS-4) und TRANSLATE (WS-7) Betroffene Kernobjekte: Page (ocr_status), ocr_error_instance, Decision Event (scope_type = project bei Freigabe) Betroffene Zustände / Transitionen: nicht_erreichbar → freigabeschranken_prüfung → übersetzungsreif \| übersetzbar_mit_warnung \| blockiert. Betroffene Events / Provenance: Decision-Event-UUID bei Freigabeentscheidung (scope_type = project). Log-Eintrag für Prüflauf. Akzeptanzkriterien: ✓ Offene kritische Fehlerklasse auf irgendeiner Seite → blockiert ✓ F-06-QR ohne Auflösung → blockiert ✓ Alle Bedingungen erfüllt → übersetzungsreif ✓ Nicht-kritische offen + Nutzer bestätigt explizit → übersetzbar_mit_warnung ✗ Kein automatischer Übersetzungsstart, auch wenn alle Seiten go Tests: Gate-Test: offenes F-06-QR → Übersetzungsstart blockiert. Nicht-Ziele: Keine Übersetzungslogik. Abhängigkeiten: T-4.3.1, T-5.1.2, T-5.2.1. Kritische Risiken: Freigabe automatisch ausgelöst, wenn letzter go-Status gesetzt wird, ohne aktive Nutzerbestätigung.*

*WS-7: Übersetzungs-Pipeline*

*T-7.1.1 – TRANSLATE: Übersetzungs-Job mit Checkpoint und Sperrflag-Prüfung AP: AP-7.1 \| Meilenstein: M-4 \| Critical Path: Ja (Schritt 10) Ziel: Übersetzungs-Job mit Checkpoint nach jedem Chunk. Kontext-Puffer in resume_state. Sperrflag-Prüfung vor jedem Segment. Scope: Übersetzungs-Job-Kernlogik. Betroffene Module: TRANSLATE, JOB, INVARIANT, LOCK Betroffene Kernobjekte: Job (job_type = translation), Checkpoint (translation_chunk, resume_state mit Kontext-Puffer), Segment (lock_flag-Prüfung) Betroffene Zustände / Transitionen: Translation-Job: pending → aktiv → deferred \| pausiert → abgeschlossen. Sperrflag-Prüfung vor jedem Segment-Schreiben. Betroffene Events / Provenance: Log-Eintrag je Chunk-Lauf. Kein TRANSLATION-PO in diesem Ticket (folgt T-7.1.2). Akzeptanzkriterien: ✓ Checkpoint nach jedem Chunk mit Kontext-Puffer in resume_state ✓ Wiederaufnahme: Kontext-Puffer korrekt deserialisiert ✓ Segment mit aktivem lock_flag → übersprungen (nicht übersetzt) ✗ Kein Überschreiben gesperrter Segmente Invarianten: H-1, H-2 Tests: T-H1-01, T-H1-02, T-REC-03 Nicht-Ziele: Kein TRANSLATION-PO (folgt T-7.1.2). Keine Glossar-Bindung (folgt T-7.2.1). Abhängigkeiten: T-6.1.1, T-5.1.1, T-2.1.2. Kritische Risiken: Kontext-Puffer nicht in resume_state serialisiert – Wiederaufnahme erzeugt inkonsistente Übersetzung.*

*T-7.1.2 – TRANSLATE: TRANSLATION-PO und Revisions-UUID bei Textänderung AP: AP-7.1 \| Meilenstein: M-4 \| Critical Path: Ja (Schritt 10) Ziel: TRANSLATION-PO nach jedem Segment via PROVENANCE-Kern. Revisions-UUID nur, wenn Ausgabe von vorherigem Stand abweicht. Bei Wiederaufnahme mit abweichendem Ergebnis: neue Textrevision. Scope: Provenance-Schreiben aus Übersetzungspipeline. Betroffene Module: TRANSLATE, PROVENANCE, REVISION, EVENTING Betroffene Kernobjekte: Provenance (TRANSLATION-PO), Revision (wenn Textänderung) Betroffene Zustände / Transitionen: Keine eigenen. Betroffene Events / Provenance: TRANSLATION-PO (scope_type = segment). Revisions-UUID, wenn neu ≠ vorherig. Akzeptanzkriterien: ✓ TRANSLATION-PO nach jedem Segment angelegt ✓ Wiederaufnahme mit abweichendem Ergebnis → neue Revisions-UUID, kein stilles Überschreiben ✗ Keine Revisions-UUID, wenn Übersetzungsausgabe identisch mit vorheriger Invarianten: H-1 Tests: T-REC-04 Nicht-Ziele: Keine Glossar-Bindung (folgt T-7.2.1). Abhängigkeiten: T-7.1.1, T-1.6.1, T-1.4.1. Kritische Risiken: Jede Übersetzungsausgabe erzeugt Revisions-UUID, unabhängig davon, ob Text identisch ist.*

*T-7.2.1 – RULE_BINDING: Glossar-Bindung in Übersetzungspipeline AP: AP-7.2 \| Meilenstein: M-4 \| Critical Path: Nein (parallel zu T-7.1.x) Ziel: Glossar- und Formelverzeichniseinträge bei Übersetzungsausgabe durchsetzen. Konflikte erkennen, nicht still auflösen. RULE_BINDING-PO anlegen. Scope: Glossar-Bindungs-Logik innerhalb der Übersetzungspipeline. Betroffene Module: TRANSLATE, GLOSSARY, LOCK, INVARIANT, PROVENANCE Betroffene Kernobjekte: Provenance (RULE_BINDING-PO), conflict_instance (bei Konflikt Glossar vs. Sperrflag: state = offen), Decision Event (bei lokaler Ausnahme: Auflösung der conflict_instance) Betroffene Zustände / Transitionen: Bei Konflikt (Glossar vs. Sperrflag): conflict_instance mit state = offen angelegt (via LOCK / T-5.1.2-Mechanismus). Nie still aufgelöst. Betroffene Events / Provenance: RULE_BINDING-PO (scope_type = segment, mit concept_id, ausnahme_flag). Decision-Event-UUID, wenn lokale Ausnahme. Akzeptanzkriterien: ✓ Glossareintrag korrekt auf Segment angewandt ✓ Konflikt mit Sperrflag → erkannt, als offen markiert, kein automatischer Sieger ✓ RULE_BINDING-PO mit korrektem ausnahme_flag und decision_event_uuid, wenn Ausnahme ✗ Kein automatisches Überschreiben gesperrter Segmente Invarianten: H-2, H-6 Tests: T-H2-01, T-KE-01 Nicht-Ziele: Keine Promotion-Pipeline (folgt T-7.3.1). Abhängigkeiten: T-5.2.1, T-7.1.1, T-1.6.1. Kritische Risiken: Glossar „gewinnt stillschweigend" gegen gesperrtes Segment mit Kommentar „Terminologie hat Vorrang laut Architektur" – bricht H-2 und H-6.*

*T-7.3.1 – Promotion-Pipeline: Beobachtung und Musterkandidat (Stufen 1–2) AP: AP-7.3 \| Meilenstein: M-4 \| Critical Path: Nein Ziel: Manuelle Korrekturen als lokale Beobachtungen registrieren (Stufe 1). System aggregiert passiv zu Musterkandidaten (Stufe 2). Musterkandidat wird nicht angewandt, nur dem Nutzer angeboten. Scope: Promotion-Pipeline Stufen 1 und 2. Betroffene Module: TRANSLATE, EVENTING Betroffene Kernobjekte: Log-Eintrag (Musterkandidat-Erkennung), Segment (MANUAL\_\*-PO als Quelle) Betroffene Zustände / Transitionen: Stufe 1 → Stufe 2: passive Aggregation, keine eigene Zustandsmaschine. Betroffene Events / Provenance: Log-Eintrag bei Musterkandidat-Erkennung (EVENTING). Akzeptanzkriterien: ✓ Manuelle Korrektur → als lokale Beobachtung gespeichert ✓ Musterkandidat erkannt → nur dem Nutzer angeboten, nicht angewandt ✗ Kein automatisches Anwenden des Musterkandidaten Invarianten: H-7 Nicht-Ziele: Kein Promote zu Stufe 3 (folgt T-7.3.2). Abhängigkeiten: T-7.1.1. Kritische Risiken: Schwellenwert für Musterkandidaten-Erkennung löst automatisch Stufe 3 aus bei ausreichend vielen Beobachtungen.*

*T-7.3.2 – Promotion-Pipeline: Bestätigung als Stilregel (Stufe 3) AP: AP-7.3 \| Meilenstein: M-4 \| Critical Path: Nein Ziel: Nutzer bestätigt Musterkandidat → Decision-Event-UUID anlegen → bestätigte Stilregel. Kein automatisches Promote. Scope: Promotion Stufe 3. Betroffene Module: TRANSLATE, REVISION Betroffene Kernobjekte: Decision Event (scope_type = project, Stilregel-Bestätigung) Betroffene Zustände / Transitionen: Musterkandidat → bestätigte Stilregel (nur nach expliziter Nutzeraktion). Betroffene Events / Provenance: Decision-Event-UUID bei Bestätigung. Akzeptanzkriterien: ✓ Stilregel-Bestätigung erzeugt Decision-Event-UUID ✗ Kein automatisches Promote von Stufe 2 → Stufe 3 Invarianten: H-7 Tests: T-H7-01 Nicht-Ziele: Keine Anwendung der Stilregel ohne weitere explizite Aktionen. Abhängigkeiten: T-7.3.1, T-1.4.2. Kritische Risiken: Stufe 3 wird als automatisch ausgelöst implementiert, wenn Musterkandidat „offensichtlich korrekt" ist.*

*WS-8: Audit und Konsistenz*

*T-8.1.1 – AUDIT: Befund-Tabelle und Audit-Lauf-Logik AP: AP-8.1 \| Meilenstein: M-5 \| Critical Path: Nein (parallel zu T-8.2.x möglich nach Schema) Ziel: Befund-Tabelle implementieren. Audit-Lauf erzeugt Befunde, keine Korrekturen, keine Revisions-UUIDs. Scope: Audit-Kern. Betroffene Module: AUDIT, EVENTING Betroffene Kernobjekte: Befund-Tabelle (satz_uuid FK, regelkennung, verstossklasse, schweregrad, auflösungsstatus) Betroffene Zustände / Transitionen: nicht_gestartet → läuft → befunde_vorhanden. Betroffene Events / Provenance: Log-Eintrag je Audit-Lauf. Akzeptanzkriterien: ✓ Audit-Lauf erzeugt Befunde in Befund-Tabelle ✓ Log-Eintrag je Lauf (Log-ID via EVENTING) ✗ Keine Revisions-UUID durch Audit-Lauf ✗ Kein automatisches Korrigieren Tests: T-H4-02 Nicht-Ziele: Keine Regelprüfung (folgt T-8.1.2). Abhängigkeiten: T-7.1.2, T-5.2.1, T-1.5.1. Kritische Risiken: Befund-Tabelle teilt sich Schema mit Revisions-Tabelle über FK-Verknüpfung, die suggeriert, dass Befunde Textrevisionen sind.*

*T-8.1.2 – AUDIT: Regelprüfung A-01 bis D-03 AP: AP-8.1 \| Meilenstein: M-5 \| Critical Path: Nein Ziel: Alle Audit-Regeln A-01 bis D-03 implementieren. Kritische Verstösse als blockierend klassifiziert. Pflichthinweise als Einzelentscheidungs-pflichtig markiert. Scope: Regelprüfungs-Logik. Betroffene Module: AUDIT, GLOSSARY Betroffene Kernobjekte: Befund-Tabelle (schweregrad, verstossklasse) Betroffene Zustände / Transitionen: befunde_vorhanden → alles_aufgelöst (nach Nutzerauflösung). Betroffene Events / Provenance: Decision-Event-UUID bei Nutzerauflösung (scope_type = segment). Akzeptanzkriterien: ✓ C-01-Verstoss → Schweregrad Kritisch → Auflösungsstatus = blockierend ✓ A-01-Verstoss → Schweregrad Hoch → Pflichthinweis (Einzelentscheidung) ✓ D-01-Verstoss → Schweregrad Mittel → Hinweis (Export möglich) ✗ Keine automatische Quittierung Tests: Audit-Test: C-01-Verstoss → Status blockierend. Nicht-Ziele: Kein Preflight (folgt T-9.1.1). Abhängigkeiten: T-8.1.1. Kritische Risiken: Kritische Verstösse als Warnungen klassifiziert, um Export nicht zu blockieren.*

*T-8.2.1 – CONSISTENCY: Konsistenz-Befund-Tabelle und identitäts-/referenzbasierter Prüflauf K-01 bis K-07 AP: AP-8.2 \| Meilenstein: M-5 \| Critical Path: Nein (teilparallel zu T-8.1.x) Ziel: Konsistenz-Befund-Tabelle anlegen. K-01 bis K-07 als identitäts-/referenzbasierte Konsistenzprüfung implementieren – je K-Regel gegen den passenden Identitätstyp (Konzept-ID, Formel-/Verzeichnisidentität, Entitäten-ID, Transliterationsmuster, Quellenidentität, strukturelles Muster). Vorschläge nie automatisch angewandt. Scope: Konsistenz-Engine-Kern. Betroffene Module: CONSISTENCY, GLOSSARY, EVENTING Betroffene Kernobjekte: Konsistenz-Befund-Tabelle (subject_type Enum, subject_key, verstossklasse, betroffene Segment-UUIDs, vorschlag). subject_type deckt je nach K-Regel ab: concept_id (K-01, K-07), formel_verzeichnis_id (K-02), entity_id (K-03), transliterations_muster (K-04), source_identity (K-05), structural_key (K-06). Betroffene Zustände / Transitionen: Keine eigene Job-Zustandsmaschine. Primär vor Export. Betroffene Events / Provenance: Log-Eintrag je Prüflauf. Decision-Event-UUID, wenn Nutzer Gruppe verbindlich festlegt (scope_type = project). Akzeptanzkriterien: ✓ K-01 / K-07: Inkonsistenz auf Konzept-ID-Basis erkannt (nicht Oberflächen-String) ✓ K-02: Inkonsistenz auf Formel-/Verzeichnisidentität erkannt ✓ K-03: Inkonsistenz auf Entitäten-ID erkannt ✓ K-04: Inkonsistenz auf Transliterationsmuster erkannt ✓ K-05: Inkonsistenz auf Quellenidentität erkannt ✓ K-06: Inkonsistenz auf strukturellem Muster / Strukturtyp erkannt ✓ Jede K-Regel prüft gegen ihren passenden Identitätstyp; keine pauschale Reduktion auf Konzept-ID ✓ Konsistenz-Verstösse werden an PREFLIGHT übergeben und dort gemäss §4.7 / §4.8 verortet (W-02 für Konsistenzwarnungen; P-03, wenn gleichzeitig eine Kritisch-Klasse im Sinne von §4.6 verletzt wird) ✗ Kein automatisches Normalisieren ✗ Kein automatisches Erzeugen von Glossareinträgen Tests: T-KA-01, T-KA-02 (indirekt) Nicht-Ziele: Kein Preflight. Abhängigkeiten: T-5.2.1, T-7.2.1. (AP-8.1-Schema muss definiert sein; kein Vollabschluss nötig.) Kritische Risiken: K-01 prüft auf String-Gleichheit statt Konzept-ID – löst falsche Alarme bei bewusst verschiedenen Übersetzungen derselben Oberflächenform. Zweites Risiko: Alle K-Regeln werden pauschal auf Konzept-ID generalisiert – K-02 bis K-06 werden dadurch strukturell falsch oder gar nicht geprüft, weil ihr Identitätstyp (Formel-/Verzeichnisidentität, Entitäten-ID, Transliterationsmuster, Quellenidentität, struktureller Schlüssel) in der Engine nicht abbildbar ist.*

*WS-9: Preflight und Export*

*T-9.1.1 – PREFLIGHT: Pflichtfragen-Bestätigung der Konfigurationsschicht, P-03 und P-04, Exportlauf-Ereignis AP: AP-9.1 \| Meilenstein: M-5 \| Critical Path: Ja (Schritt 11) Ziel: Aktive Bestätigung der vier Pflichtfragen der Preflight-Konfigurationsschicht (belegt keinen P-Slot), P-03 (kritische Audit-Verstösse aufgelöst), P-04 (Pflichthinweise einzeln entschieden). Exportlauf-Ereignis immer. Scope: Preflight-Kernlogik für die belegten blocking-relevanten Bedingungen. Betroffene Module: PREFLIGHT, AUDIT, REVISION, EVENTING Betroffene Kernobjekte: Decision Event (scope_type = project, für Pflichtfragen-Bestätigungen), Log-Eintrag (Exportlauf-Ereignis) Betroffene Zustände / Transitionen: nicht_gestartet → läuft → exportierbar \| blockiert. Betroffene Events / Provenance: Exportlauf-Ereignis (Log-ID, EVENTING) immer. Decision-Event-UUIDs für Pflichtfragen-Bestätigungen. Akzeptanzkriterien: ✓ Export blockiert, wenn die vier Pflichtfragen der Konfigurationsschicht nicht aktiv beantwortet sind ✓ Gespeichertes Profil füllt vor, ersetzt nicht aktive Bestätigung ✓ Exportlauf-Ereignis (Log-ID) wird immer erzeugt, auch bei blockiertem Export ✗ Kein Export ohne aktive Bestätigung der vier Pflichtfragen Nicht-Ziele: Keine Warnungs-Checks (folgt T-9.1.2). Kein Artefakt-Export (folgt T-9.2.1). Abhängigkeiten: T-8.1.2, T-8.2.1. Kritische Risiken: Gespeichertes Export-Profil wird als aktive Bestätigung gewertet – umgeht die Pflichtfragen-Bestätigung der Konfigurationsschicht.*

*T-9.1.2 – PREFLIGHT: Belegte W-Gates und exportierbar_mit_warnungen AP: AP-9.1 \| Meilenstein: M-5 \| Critical Path: Ja (Schritt 11) Ziel: Belegte Warnungs-Checks W-01 (Mittel-Audit), W-02 (K-01–K-07 Konsistenzwarnungen), W-03 (graduelle Formatvorlagen-Abweichungen) implementieren. exportierbar_mit_warnungen-Zustand. W-04 bis W-08 sowie P-01, P-02, P-05, P-06 sind im aktuellen Kanon offen und werden in diesem Ticket nicht inhaltlich belegt. Scope: Vollständige Preflight-Logik im Rahmen der heute belegten Gates. Betroffene Module: PREFLIGHT, CONSISTENCY Betroffene Kernobjekte: Decision Event (Warnungsbestätigungen), Log-Eintrag (Exportlauf-Ereignis) Betroffene Zustände / Transitionen: blockiert → exportierbar_mit_warnungen \| exportierbar (nach Auflösung bzw. Bestätigung). Betroffene Events / Provenance: Decision-Event-UUID für jede aktive Warnungsbestätigung. Akzeptanzkriterien:*

*✓ Konsistenz-Verstoss der Kritisch-Klasse im Sinne von §4.6 → P-03 (Audit-Gate), nicht W-02*

*✓ Konsistenz-Verstoss ohne Kritisch-Klasse → W-02 (warnungsbasiert, nicht blockierend)*

*✓ W-01, W-02, W-03 korrekt als Warnungen (nicht blockierend)*

*✓ Export mit Warnungen nur nach expliziter Bestätigung*

*✗ Kein Pflichthinweis als allgemeine Warnung mitlaufen lassen*

*Hinweis zum Scope dieses Tickets: Die Hadith-Verifikationsstatus-Gruppe gemäss §4.7 und §4.16 ist Teil der Preflight-Gate-Prüfungsschicht und im Rahmen von T-9.1.2 mitzuberücksichtigen, soweit sie den Zustand exportierbar_mit_warnungen betrifft. H-1-Stellen sind warnungsbasiert und erfordern eine aktive go_with_warning-Bestätigung. H-2-Stellen bleiben blockierend und dürfen nicht über T-9.1.2 als Warnung behandelt werden; ihre blockierende Wirkung ist im Preflight-Zustand blockiert zu berücksichtigen.*

*Nicht-Ziele: Kein Artefakt-Export. Abhängigkeiten: T-9.1.1. Kritische Risiken: Pflichthinweis-Klasse (P-04) als W-Warnung behandelt – blockiert Export nicht mehr, wenn nötig.*

*T-9.2.1 – EXPORT: Artefakterzeugung und EXPORT_EVENT AP: AP-9.2 \| Meilenstein: M-5 \| Critical Path: Ja (Schritt 12) Ziel: Artefakt erzeugen. EXPORT_EVENT nur bei Erfolg, atomar angelegt. Exportlauf-Ereignis immer. Exportprotokoll nach Abschluss unveränderlich. Scope: Export-Artefakt und EXPORT_EVENT-Anlage. Betroffene Module: EXPORT, PREFLIGHT, IDENTITY, PROVENANCE, EVENTING Betroffene Kernobjekte: EXPORT_EVENT (export_uuid, revision_snapshot\[\], active_decision_event_uuids\[\], export_config, artefakt_ref), Log-Eintrag (Exportlauf-Ereignis) Betroffene Zustände / Transitionen: Export-Job: pending → aktiv → abgeschlossen \| fehlgeschlagen. Betroffene Events / Provenance: EXPORT_EVENT (po_type = EXPORT_EVENT, scope_type = artefact, werkweit) – nur bei Erfolg, atomar. Exportlauf-Ereignis (Log-ID) immer. Akzeptanzkriterien: ✓ EXPORT_EVENT nur nach vollständig erfolgreichem Artefakt-Abschluss (atomare Operation) ✓ revision_snapshot\[\] korrekt befüllt mit allen aktiven Revisions-UUIDs ✓ active_decision_event_uuids\[\] korrekt befüllt mit allen aktiven Decision-Event-UUIDs ✓ Fehlgeschlagener Export → Exportlauf-Ereignis vorhanden, kein EXPORT_EVENT ✓ EXPORT_EVENT nach Abschluss unveränderlich ✗ Kein EXPORT_EVENT bei Fehlschlag oder Blockierung Tests: Test: blockierter Export → Log-Eintrag, kein EXPORT_EVENT. Nicht-Ziele: Kein Verändern des EXPORT_EVENTs. Abhängigkeiten: T-9.1.2. Kritische Risiken: EXPORT_EVENT wird vor Artefakt-Abschluss angelegt „als Fortschrittsmarker" – führt zu EXPORT_EVENTs ohne gültiges Artefakt.*

*WS-10: Provenance-Auswertung und Historie*

*T-10.1.1 – PROVENANCE-Auswertung: get_pos_for_segment und EXPORT_EVENT-Verknüpfung AP: AP-10.1 \| Meilenstein: M-6 \| Critical Path: Nein Ziel: get_pos_for_segment(satz_uuid) liefert nur segment-scoped POs. get_export_events_for_segment(satz_uuid) findet EXPORT_EVENTs über revision_snapshot\[\]. Kein Erzeugen neuer POs. Scope: Provenance-Abfrageschicht. Betroffene Module: PROVENANCE (Auswertung) Betroffene Kernobjekte: Provenance (Lesen), EXPORT_EVENT (Lesen über revision_snapshot\[\]) Betroffene Zustände / Transitionen: Keine. Betroffene Events / Provenance: Keine neuen POs. Akzeptanzkriterien: ✓ get_pos_for_segment() gibt nur POs mit scope_type = segment und scope_uuid = satz_uuid zurück ✓ get_export_events_for_segment() findet EXPORT_EVENTs über revision_snapshot\[\], nicht über direkten Segment-FK im EXPORT_EVENT ✓ EXPORT_EVENT erscheint als werkweite Referenz, nicht als segmenteigener Export ✗ Keine page-scoped POs in Segment-Abfrage ✗ Keine neuen POs durch Auswertungsschicht Tests: Scope-Test: page-scoped PO darf nicht in Segment-Abfrage erscheinen. Nicht-Ziele: Kein Why-Panel-Rendering. Abhängigkeiten: T-1.6.1, T-9.2.1. Kritische Risiken: get_export_events_for_segment() implementiert direkten Segment-FK im EXPORT_EVENT statt revision_snapshot\[\]-Lookup – bricht werkweites Scope-Modell.*

*T-10.1.2 – PROVENANCE-Auswertung: get_page_history und get_project_history AP: AP-10.1 \| Meilenstein: M-6 \| Critical Path: Nein Ziel: get_page_history(page_uuid) liefert page-scoped Decision Events. get_project_history(project_uuid) liefert project-scoped Decision Events und EXPORT_EVENTs. Scope: Seiten- und Projekthistorie-Abfragen. Betroffene Module: PROVENANCE (Auswertung), REVISION Betroffene Kernobjekte: Decision Event (scope_type = page / project), EXPORT_EVENT Betroffene Zustände / Transitionen: Keine. Betroffene Events / Provenance: Keine neuen. Akzeptanzkriterien: ✓ get_page_history() gibt nur page-scoped Decision Events zurück ✓ get_project_history() gibt project-scoped Decision Events + EXPORT_EVENTs zurück ✗ Keine segment-scoped Events in Seitenhistorie Tests: eigener Scope-Test. Nicht-Ziele: Kein Rendering. Abhängigkeiten: T-10.1.1. Kritische Risiken: Seitenhistorie zeigt alle Decision Events aller Segmente der Seite statt nur page-scoped.*

*T-10.2.1 – Historien-Scope-Trennung: Backend-Endpunkte AP: AP-10.2 \| Meilenstein: M-6 \| Critical Path: Nein Ziel: Vier scope-getrennte Backend-Endpunkte: Segmenthistorie, Seitenhistorie, Projekthistorie, Ereignis-Log. Strikte Scope-Trennung. Scope: API-Endpunkte für Historien-Ausgabe. Betroffene Module: PROVENANCE (Auswertung), REVISION, EVENTING Betroffene Kernobjekte: Alle Revisions-, Decision-Event-, Log- und EXPORT_EVENT-Tabellen (Lesen) Betroffene Zustände / Transitionen: Keine. Betroffene Events / Provenance: Keine neuen. Akzeptanzkriterien: ✓ Segmenthistorie: nur segment-scoped Revisions-UUIDs + Decision-Event-UUIDs + EXPORT_EVENT-Referenzen ✓ Seitenhistorie: nur page-scoped Decision Events (keine Segment-Events) ✓ Projekthistorie: project-scoped Decision Events + EXPORT_EVENTs ✓ Ereignis-Log: nur Log-IDs (Log-Einträge), separat, nicht in anderen Historien ✓ EXPORT_EVENT in Segmenthistorie als werkweite Referenz, nicht als segmenteigener Export ✗ Log-IDs erscheinen nicht in Segment- oder Seitenhistorie ✗ Keine eigene Logik in der UI – alle Scope-Trennungen Backend-seitig erzwungen Tests: Historien-Test: project-scoped Decision Event nicht in Segmenthistorie; Log-Eintrag nicht in Seitenhistorie. Nicht-Ziele: Kein Rendering. Keine UI-Logik. Abhängigkeiten: T-10.1.2. Kritische Risiken: Ereignis-Log-Einträge werden in Seitenhistorie eingeblendet „für bessere Übersicht" – bricht Scope-Trennung.*

*GRANULARITÄT Jedes Ticket ist so geschnitten, dass ein Engineering-Team es in einem Review-Zyklus umsetzen, reviewen und testen kann. Die Tickets sind kleiner als Arbeitspakete, grösser als einzelne Funktionen. Jedes Ticket hat genau eine testbare Kernaussage in den Akzeptanzkriterien.*

*KANONISCHE ZUORDNUNG*

| ***Ticket*** | ***AP*** | ***Invarianten*** | ***Testfamilien (Mindest)*** | ***Critical Path*** |
|----|----|----|----|----|
| *T-1.1.1* | *AP-1.1* | *H-5* | *T-H5-01* | *Ja* |
| *T-1.1.2* | *AP-1.1* | *H-5* | *T-H5-01, T-H5-02* | *Ja* |
| *T-1.2.1* | *AP-1.2* | *H-1, H-2* | *T-H1-01, T-H1-02* | *Ja* |
| *T-1.2.2* | *AP-1.2* | *H-4, H-5, H-6, H-7* | *T-H2-01, T-H2-02, T-H4-01, T-H4-02, T-H6-01, T-H7-01* | *Ja* |
| *T-1.3.1* | *AP-1.3* | *–* | *Schema-Test* | *Ja* |
| *T-1.3.2* | *AP-1.3* | *H-4* | *T-H4-01, T-H4-02* | *Ja* |
| *T-1.3.3* | *AP-1.3* | *H-5* | *Scope-Test (satz_uuid NOT NULL verboten)* | *Ja* |
| *T-1.4.1* | *AP-1.4* | *H-4* | *T-H4-01* | *Ja* |
| *T-1.4.2* | *AP-1.4* | *H-4* | *T-H4-02* | *Ja* |
| *T-1.5.1* | *AP-1.5* | *–* | *Trennungs-Test* | *Nein* |
| *T-1.6.1* | *AP-1.6* | *–* | *Smoke-Test* | *Ja* |
| *T-2.1.1* | *AP-2.1* | *–* | *T-REC-05* | *Ja* |
| *T-2.1.2* | *AP-2.1* | *–* | *T-REC-01, T-REC-02* | *Ja* |
| *T-3.1.1* | *AP-3.1* | *–* | *–* | *Nein* |
| *T-3.1.2* | *AP-3.1* | *–* | *T-REC-01* | *Nein* |
| *T-4.1.1* | *AP-4.1* | *H-5* | *T-REC-02* | *Ja* |
| *T-4.1.2* | *AP-4.1* | *H-4* | *T-H4-01* | *Ja* |
| *T-4.1.3* | *AP-4.1* | *–* | *F-Klassen-Test* | *Ja* |
| *T-4.2.1* | *AP-4.2* | *H-5* | *T-H5-01, T-H5-02* | *Nein* |
| *T-4.2.2* | *AP-4.2* | *H-5* | *T-H5-01* | *Nein* |
| *T-4.3.1* | *AP-4.3* | *–* | *Integrations-Test* | *Ja (Gate für AP-6.1)* |
| *T-5.1.1* | *AP-5.1* | *H-1, H-2* | *T-H1-01, T-H1-02* | *Ja (gemeinsames Gate)* |
| *T-5.1.2* | *AP-5.1* | *H-6* | *T-H2-01, T-H2-02, T-H6-01* | *Ja (gemeinsames Gate)* |
| *T-5.2.1* | *AP-5.2* | *H-6* | *T-KE-01* | *Ja (gemeinsames Gate)* |
| *T-6.1.1* | *AP-6.1* | *–* | *Gate-Test* | *Ja* |
| *T-7.1.1* | *AP-7.1* | *H-1, H-2* | *T-H1-01, T-H1-02, T-REC-03* | *Ja* |
| *T-7.1.2* | *AP-7.1* | *H-1* | *T-REC-04* | *Ja* |
| *T-7.2.1* | *AP-7.2* | *H-2, H-6* | *T-H2-01, T-KE-01* | *Nein* |
| *T-7.3.1* | *AP-7.3* | *H-7* | *T-H7-01* | *Nein* |
| *T-7.3.2* | *AP-7.3* | *H-7* | *T-H7-01* | *Nein* |
| *T-8.1.1* | *AP-8.1* | *H-4* | *T-H4-02* | *Nein* |
| *T-8.1.2* | *AP-8.1* | *–* | *Audit-Test* | *Nein* |
| *T-8.2.1* | *AP-8.2* | *–* | *T-KA-01* | *Nein* |
| *T-9.1.1* | *AP-9.1* | *–* | *Preflight-Test* | *Ja* |
| *T-9.1.2* | *AP-9.1* | *–* | *Preflight-Test* | *Ja* |
| *T-9.2.1* | *AP-9.2* | *–* | *Export-Test* | *Ja* |
| *T-10.1.1* | *AP-10.1* | *–* | *Scope-Test* | *Nein* |
| *T-10.1.2* | *AP-10.1* | *–* | *Scope-Test* | *Nein* |
| *T-10.2.1* | *AP-10.2* | *–* | *Historien-Test* | *Nein* |

*DELIVERY-REIHENFOLGE*

*Schritt 1 (sequenziell – Fundament): T-1.1.1 → T-1.1.2 → T-1.2.1 → T-1.2.2 → T-1.3.1 → T-1.3.2 → T-1.3.3 → T-1.4.1 → T-1.4.2 T-1.5.1 (parallel zu T-1.4.x möglich) → T-1.6.1 (nach T-1.4.2 und T-1.5.1)*

*Schritt 2 (Job-Infrastruktur): T-2.1.1 → T-2.1.2*

*Schritt 3 (Upload): T-3.1.1 → T-3.1.2*

*Schritt 4 (OCR): T-4.1.1 → T-4.1.2 → T-4.1.3 T-4.2.1 (parallel zu T-4.1.x, nach T-4.1.1) T-4.2.2 (nach T-4.2.1) T-4.3.1 (nach T-4.1.3)*

*Schritt 5 (Schutzschicht – gemeinsames Gate): T-5.1.1 ║ T-5.2.1 (parallel, beide nach T-4.3.1) T-5.1.2 (nach T-5.1.1)*

*Schritt 6 (Freigabeschranke): T-6.1.1 (nach T-5.1.2 UND T-5.2.1 – beide Gates müssen grün sein)*

*Schritt 7 (Übersetzung): T-7.1.1 → T-7.1.2 T-7.2.1 (parallel zu T-7.1.x, nach T-7.1.1) T-7.3.1 → T-7.3.2 (parallel zu T-7.2.1)*

*Schritt 8 (Audit + Konsistenz): T-8.1.1 → T-8.1.2 T-8.2.1 (nach T-8.1.1-Schema definiert, teilparallel)*

*Schritt 9 (Preflight + Export): T-9.1.1 → T-9.1.2 → T-9.2.1*

*Schritt 10 (Provenance-Auswertung): T-10.1.1 → T-10.1.2 → T-10.2.1*

*Harte Gate-Tickets (kein Weitergehen ohne diese grün):*

- *T-1.2.2 (alle H-Tests) → Gate für Schritt 2*

- *T-4.3.1 (OCR-Review-Status) → Gate für Schritt 5*

- *T-5.1.2 + T-5.2.1 (gemeinsames Gate) → Gate für T-6.1.1*

- *T-6.1.1 (Freigabeschranke) → Gate für Schritt 7*

- *T-9.1.1 (Pflichtfragen-Bestätigung der Konfigurationsschicht + P-03/P-04) → Gate für T-9.2.1*

*MINIMALER ERSTER DELIVERY-CUT*

*Tickets: T-1.1.1, T-1.1.2, T-1.2.1, T-1.2.2, T-1.3.1, T-1.3.2, T-1.3.3, T-1.4.1, T-1.4.2, T-1.5.1, T-1.6.1, T-2.1.1, T-2.1.2, T-3.1.1, T-3.1.2, T-4.1.1, T-4.1.2, T-4.1.3*

*Was damit Ende-zu-Ende nachweisbar funktioniert:*

- *Datei hochladen mit Wiederaufnahme-Garantie*

- *OCR-Durchlauf mit Checkpoint-Recovery*

- *Block- und Satz-UUIDs korrekt angelegt und unveränderlich*

- *SCAN-PO und OCR-PO korrekt via PROVENANCE-Kern angelegt*

- *Fehlerklassen F-01 bis F-09 erkannt und persistiert*

- *INVARIANT-Guard blockiert nachweislich alle H-1 bis H-7-Verletzungen*

- *Revisions-UUID / Decision-Event-UUID / Log-ID korrekt getrennt*

*Was bewusst noch fehlt:*

- *Kein Sperrflag-Management (WS-5)*

- *Keine Freigabeschranke (WS-6)*

- *Keine Übersetzung (WS-7)*

- *Kein Audit (WS-8)*

- *Kein Export (WS-9)*

- *Keine Provenance-Auswertung (WS-10)*

*Kernrisiken, die im ersten Cut bereits abgesichert sein müssen:*

- *Alle T-H-Tests grün*

- *T-REC-01 und T-REC-02 grün*

- *Kein satz_uuid-Pflichtfeld in Provenance-Tabelle*

*A. HARTE DELIVERY-GATES*

*Diese Tickets dürfen niemals übersprungen oder provisorisch umgangen werden:*

| ***Ticket*** | ***Warum unumgehbar*** |
|----|----|
| *T-1.2.1 + T-1.2.2 (INVARIANT-Guard)* | *Ohne Guard kann jedes spätere Ticket versehentlich Baseline-Verletzungen einführen. Kein anderes Ticket darf vor grünem Guard gestartet werden.* |
| *T-1.3.3 (Provenance-Schema)* | *scope_type + scope_uuid muss vor dem ersten PROVENANCE-Schreiben korrekt im Schema stehen. Nachträgliche Migration bricht alle bereits geschriebenen POs.* |
| *T-1.6.1 (PROVENANCE-Kern)* | *Alle Module ab WS-3 schreiben POs. Ohne PROVENANCE-Kern fehlt jede Provenance-Spur.* |
| *T-2.1.2 (Checkpoint)* | *Ohne Checkpoint-Persistenz gibt es keine Recovery-Garantie. Alle Recovery-Tests können nicht bestehen.* |
| *T-5.1.2 (Konflikt-Erkennung + conflict_instance)* | *Ohne persistente conflict_instance-Einträge gehen offene Konflikte nach Server-Neustart verloren. Gesperrte Segmente könnten dann unbemerkt überschrieben werden. H-6 wäre nur bis zum nächsten Neustart aktiv.* |
| *T-6.1.1 (Freigabeschranke)* | *Ohne aktive Freigabeschranke kann die Übersetzung ohne OCR-Review starten.* |
| *T-9.1.1 (Pflichtfragen-Bestätigung + P-03/P-04)* | *Ohne aktive Bestätigung der vier Pflichtfragen der Konfigurationsschicht und ohne Auflösung kritischer (P-03) und pflichthinweispflichtiger (P-04) Audit-Verstösse kann der Export strukturell nicht sauber ablaufen.* |
| *T-9.2.1 (EXPORT_EVENT-Atomarität)* | *EXPORT_EVENT darf niemals teilweise geschrieben werden. Atomare Operation ist unverhandelbar.* |

*B. TYPISCHE FALSCHE ABKÜRZUNGEN*

*Abkürzung 1: INVARIANT-Guard als optionale Middleware Versuchung: Guard als konfigurierbaren Middleware-Layer implementieren, der in Tests deaktiviert werden kann. Konsequenz: Guard wird unter Zeitdruck deaktiviert und vergessen. Alle H-Verletzungen sind dann möglich.*

*Abkürzung 2: Provenance-Tabelle mit satz_uuid NOT NULL Versuchung: Für Einfachheit satz_uuid als Pflichtfeld anlegen, weil 90 % der POs segment-scoped sind. Konsequenz: page-scoped und project-scoped POs können nicht korrekt angelegt werden. SCAN-PO, page-scoped OCR-Diagnostik und EXPORT_EVENT brechen.*

*Abkürzung 3: Drei Identitätstypen in einer gemeinsamen Events-Tabelle Versuchung: Revision, Decision Event und Log-Eintrag in eine Tabelle mit type-Diskriminator. Konsequenz: H-4-Prüfung wird strukturell unmöglich. Jeder Prüflauf „könnte" eine Textrevision sein.*

*Abkürzung 4: EXPORT_EVENT vor Artefakt-Abschluss schreiben Versuchung: EXPORT_EVENT als Fortschrittsmarker früh anlegen, artefakt_ref später nachpflegen. Konsequenz: EXPORT_EVENTs ohne gültiges Artefakt. Nach Fehlschlag existiert ein EXPORT_EVENT für eine nie erzeugte Datei.*

*Abkürzung 5: Freigabeschranke automatisch auslösen, wenn alle Seiten go Versuchung: Übersetzungsstart automatisch triggern, sobald letzter OCR-Status auf go wechselt. Konsequenz: Übersetzung startet ohne aktive Nutzerfreigabe. Baseline-Bedingung (kein automatischer Start) ist gebrochen.*

*Abkürzung 6: Konflikt bei „offensichtlich korrektem" Glossareintrag still auflösen Versuchung: Glossar gewinnt immer gegen Sperrflag „weil das ja die Architektur vorsieht". Konsequenz: H-6 ist faktisch deaktiviert. Manuelle Korrekturen werden still überschrieben.*

*Abkürzung 7: Upload-Handler schreibt SCAN-PO direkt Versuchung: Für Einfachheit SCAN-PO synchron im Upload-Code schreiben statt PROVENANCE-Kern nach Job-Abschluss-Event aufzurufen. Konsequenz: UPLOAD hat direkte PROVENANCE-Abhängigkeit entgegen der definierten Modulabgrenzung. Bei Upload-Fehler entsteht ein SCAN-PO ohne gültigen Upload.*

*Abkürzung 8: Lineage-Matching erzeugt Decision-Event-UUIDs Versuchung: UUID-Matching als „Entscheidung" modellieren und in Decision-Event-Tabelle schreiben „weil es wichtig ist". Konsequenz: Decision-Event-Tabelle wird mit technischen Ereignissen geflutet. Nutzer-Entscheidungen sind nicht mehr von System-Matching-Ereignissen unterscheidbar.*

*Abkürzung 9: Checkpoint in Memory puffern statt atomar persistieren Versuchung: Checkpoints im Arbeitsspeicher halten und nur periodisch schreiben für bessere Performance. Konsequenz: Bei Absturz zwischen zwei Schreibvorgängen geht Fortschritt verloren. Recovery-Garantie bricht.*

*Abkürzung 10: K-01 auf String-Gleichheit prüfen statt Konzept-ID Versuchung: Einfacherer String-Vergleich statt Konzept-ID-Lookup für terminologische Konsistenz. Konsequenz: Bewusst verschiedene Übersetzungen derselben Oberflächenform lösen Fehlalarme aus. Legitime lokale Ausnahmen werden als Verstösse markiert.*

*Abkürzung 11: Konflikt-Instanz nur in-memory halten statt persistieren Versuchung: Offene Konflikte als transiente In-Memory-Zustände verwalten statt als conflict_instance-Einträge persistieren – „der Nutzer muss ja sowieso reagieren, bevor er weitermacht". Konsequenz: Nach Server-Neustart oder Session-Timeout gehen alle offenen Konflikte verloren. Gesperrte Segmente können dann unbemerkt von automatischen Operationen überschrieben werden. H-6 ist faktisch nur bis zum nächsten Neustart aktiv.*

*STILFEATURE-STRANG – BACKLOG-SCHICHT (CR-3)*

*Verankerung des Stilfeature-Strangs in der Delivery Backlog Baseline gemäss CR-3. Diese Schicht ergänzt die bestehende DBB-Struktur (Workstreams, Arbeitspakete, Tickets, Meilensteine, Critical-Path-Logik) und ersetzt nichts davon. Konkrete Einzeltickets pro Familie und konkrete Sprintnummerierung sind nicht Gegenstand dieses Abschnitts.*

*7.1 Strukturverankerung der fünf Stilfeature-Ticketfamilien*

*Aufnahme des Stilfeature-Strangs entlang von fünf Ticketfamilien als Backlog-Ordnungsschicht:*

- *F1 – Objekt-/Schema-Fundament*

- *F2 – Promotion / Stilregel-Entwicklung*

- *F3 – Audit / Konflikt / Marker*

- *F4 – Anzeige / Provenance / Tooltip*

- *F5 – Konfiguration / Kalibrierung*

*Die fünf Familien dienen ausschliesslich der Backlog-Ordnung des Stilfeature-Strangs in der DBB. Sie ziehen keine neue Architektur ein.*

*7.2 Delivery-Verortungslogik*

*Die Familien aus 7.1 werden relativ zur bestehenden DBB-Delivery-Logik (Schritte / Meilensteine / harte Delivery-Gates gemäss Abschnitt 4 und Abschnitt A) verortet, ohne Einführung einer neuen Sprint-Systematik:*

- *F1 (Objekt-/Schema-Fundament) reiht sich in das Identitäts-/Schema-Sprint-Umfeld der DBB ein und gilt als Voraussetzung für alle weiteren Familien des Stilfeature-Strangs.*

- *F2 und F4 folgen nach F1 und sind grundsätzlich parallelisierbar.*

- *F3 folgt nach F1 und nach der DBB-Audit-Schicht.*

- *F5 ist späte, nicht-critical-path-Arbeitsfront.*

- *T-7.3.1 / T-7.3.2 bleiben in ihrer bestehenden DBB-Verortung (AP-7.3 / M-4 / Critical Path: Nein) unberührt; siehe 7.4.*

*Konkrete Sprintnummern für die Familien F1–F5 sind nicht Gegenstand dieses Abschnitts.*

*7.3 Konfigurationsschicht (F5-Inhalte)*

*Verankerung der Stilfeature-Konfigurationsarbeit als Backlog-Schicht im Rahmen der Familie F5 aus 7.1. Inhalte der Schicht:*

- *Persistenzort der Schwellenwerte (Schicht-Aussage; konkreter Persistenzort offen).*

- *Änderbarkeit (Rollenfrage; konkrete Rollenzuordnung offen).*

- *Laufzeitwirkung von Schwellenwertänderungen (Schicht-Aussage, dass eine Wirkung existiert; konkretes Wirkungsmodell offen).*

- *Protokollierung von Schwellenwertänderungen als decision_event mit decision_source = style_management (referenziert die in CR-1 verankerte Enum-Erweiterung).*

*Ausdrücklich nicht Gegenstand dieser Schicht und dieses Abschnitts: keine Default-Werte, keine Initial-Werte, keine konkreten Schwellenwerte; keine stille Vorwegnahme späterer Kalibrierung; die Werte selbst sind als Gruppe C zu kennzeichnen mit Verweis auf Dokument 1 §4.14-Schlusssatz „Kalibrierungswerte werden nach Gold-Corpus-Tests festgelegt".*

*7.4 Querbezug zu T-7.3.1 / T-7.3.2*

*T-7.3.1 (Promotion-Pipeline: Beobachtung und Musterkandidat, Stufen 1–2) und T-7.3.2 (Promotion-Pipeline: Bestätigung als Stilregel, Stufe 3) bleiben in ihrer bestehenden DBB-Form (AP-7.3 / M-4 / Critical Path: Nein) erhalten. Die in Dokument 2 §8 separat geführte bedingte Sprint-Verortung dieser Tickets bleibt davon unberührt.*

*Die Ticketfamilie F2 (Promotion / Stilregel-Entwicklung) aus 7.1 nimmt T-7.3.1 / T-7.3.2 auf, ohne sie umzustrukturieren, umzubenennen oder ihre AP-/Meilenstein-/Critical-Path-Zuordnung zu verändern. Kein Eingriff in T-7.3.x in diesem Abschnitt.*

*7.5 Markiert offene Modellfrage B.3 – Granularität der Lernquellen-Asymmetrie §4.13 in F2*

*Die Granularität der Lernquellen-Asymmetrie gemäss Dokument 1 §4.13 innerhalb der Familie F2 ist ausdrücklich offen. Offen bleibt insbesondere:*

- *ob die fünf Quellklassen aus Dokument 1 §4.13 (bestätigte Referenzsätze, manuelle Nutzerregeln, akzeptierte KI-Vorschläge, korrigierte KI-Vorschläge, ignorierte KI-Vorschläge) in F2 als ein einziges Ticket oder als fünf Sub-Tickets implementiert werden;*

- *ob die Lernquellen-Asymmetrie später ausschliesslich regelbezogen oder zusätzlich belegbezogen / profilversionsbezogen verfeinert wird.*

*Die Modellfrage wird im Backlog nur als offen markierte spätere Arbeitsfrage mitgeführt. Keine Entscheidung in diesem Abschnitt. Granularität und Verfeinerungsachse sind in der späteren Ticketdetaillierung zu klären.*

*Waraq Delivery Backlog Baseline v1.0 – Ende der Fassung*
