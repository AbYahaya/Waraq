<!-- Converted from "BASELINE DELIVERY PLAN v1.0.docx" via pandoc 3.9.0.2 on 2026-05-02 -->
<!-- The .docx in this directory remains source-of-truth per docs/canon/README.md authority rule -->
<!-- Conversion is content-faithful (text, tables, identifiers, Swiss German ss, Arabic RTL spans, §-refs); Word-specific visual styling is dropped -->

WARAQ BASELINE DELIVERY PLAN Version 1.0 – Überblick

Beschreibt den Arbeitsstand der Waraq-Baselines und der zugehörigen Sprint-/Delivery-Planung. Strukturell ausgearbeitet; keine Coding-Freigabe, keine Implementierungs-Freigabe.

1.  ZUGEHÖRIGE DOKUMENTE

| **Dokument** | **Version** | **Status** |
|----|----|----|
| Waraq Core Architecture Baseline | v1.0 | Eingefroren |
| Waraq Implementation Translation Baseline | v1.0 | Eingefroren |
| Waraq Engineering Execution Baseline | v1.0 | Eingefroren |
| Waraq Delivery Backlog Baseline | v1.0 | Eingefroren |
| Waraq Sprint-0 / Foundation Delivery Plan | v1.0 | Arbeitsgrundlage |
| Waraq Sprint-1 / OCR Review + Lock + Glossary Delivery Plan | v1.0 | Arbeitsgrundlage |
| Waraq Sprint-2 / Release Gate + Translation Core Delivery Plan | v1.0 | Arbeitsgrundlage |
| Waraq Sprint-3 / Audit + Rule-Binding Completion Delivery Plan | v1.0 | Arbeitsgrundlage |
| Waraq Sprint-4 / Consistency + Preflight Delivery Plan | v1.0 | Arbeitsgrundlage |
| Waraq Sprint-5 / Export Artifact + Provenance Handoff Delivery Plan | v1.0 | Arbeitsgrundlage |
| Waraq Sprint-6 / Provenance Readout + History Endpoints Delivery Plan | v1.0 | Arbeitsgrundlage |

Die Baselines sind eingefrorene kanonische Arbeitsgrundlagen. Die Sprint-Pläne sind als Arbeitsgrundlage geführt und stellen keine Umsetzungsnachweise dar.

2.  UMSETZUNGSLOGIK IN KOMPAKTEM ÜBERBLICK

Die Delivery ist in sieben operative Sprints gegliedert, die logisch aufeinander aufbauen. Die Sprints sind strukturell ausgearbeitet; ob und wann sie umgesetzt werden, ist nicht Gegenstand dieser Fassung.

Sprint 0 – Foundation: UUID-Service, INVARIANT-Guard, alle Kernobjekt-Schemas, REVISION/EVENTING/PROVENANCE-Kern, Job-Infrastruktur, Upload-Pipeline, OCR-Kernverarbeitung mit Fehlerklassen-Profiling. Erstes Ende-zu-Ende-lauffähiges Fundament.

Sprint 1 – OCR Review + Lock + Glossary: Lineage-Service, OCR-Review-Status (Go/No-Go pro Seite), Sperrflag-Management mit persistenter conflict_instance, Glossar-/Konzept-ID-Grundlage.

Sprint 2 – Release Gate + Translation Core: Freigabeschranke als Workflow-Gate vor Übersetzungsstart, Übersetzungs-Job mit Checkpoint und Sperrflag-Respektierung, TRANSLATION-PO und Revisions-UUID bei Textänderung. Optional: Glossar-Bindung im Übersetzungspfad (T-7.2.1) und Promotion-Pipeline Stufen 1–2 (T-7.3.1).

Sprint 3 – Audit + Rule-Binding Completion: Audit-Befund-Tabelle und vollständige Regelprüfung A-01 bis D-03. Bedingt: Glossar-Bindung (T-7.2.1, falls nicht Sprint 2) und Promotion-Pipeline Stufe 3 (T-7.3.2, falls T-7.3.1 vorhanden).

Sprint 4 – Consistency + Preflight: Identitäts-/referenzbasierte Konsistenz-Engine K-01 bis K-07 je nach K-Regel gegen den passenden Identitätstyp. Preflight im Umfang des aktuell belegten Kanons:

- Preflight-Konfigurationsschicht getrennt von Gate-Prüfungsschicht.

- Belegte Gates: P-03 (kritische Audit-Verstösse), P-04 (Hoch-Audit-Pflichthinweise), W-01 (Mittel-Audit-Hinweise), W-02 (Konsistenzwarnungen K-01–K-07), W-03 (graduelle Formatvorlagen-Abweichungen).

- Hadith-Verifikationsstatus als eigene benannte Gruppe innerhalb der Gate-Prüfungsschicht (H-2 blockierend, H-1 warnungsbasiert, keine P-/W-Slot-Belegung).

- Offen und nicht inhaltlich belegt: P-01, P-02, P-05, P-06 sowie W-04 bis W-08.

- Guard-nahe Vorprüfungen (Ziffernstandard, RTL, Formatvorlagen-Integrität, kritische Schriftart-Verfügbarkeit) vor dem Preflight-Dialog.

- Exportlauf-Ereignis (Log-ID) erstmals angelegt.

Sprint 5 – Export Artifact + Provenance Handoff: Artefakt-Erzeugung nach grünem Preflight, EXPORT_EVENT atomar und unveränderlich via PROVENANCE-Kern, revision_snapshot\[\] und active_decision_event_uuids\[\] als werkzustandsbezogener Punkt-in-Zeit-Snapshot.

Sprint 6 – Provenance Readout + History Endpoints: Segmentbezogene Provenance-Abfragen, EXPORT_EVENT-Verknüpfung via revision_snapshot\[\]-Lookup, Seiten- und Projekthistorie, vier scope-getrennte Backend-Historien-Endpunkte.

3.  PLANUNGSSTAND IN BEZUG AUF DIE BASELINE

Die Waraq Delivery Backlog Baseline v1.0 ist strukturell vollständig ausgearbeitet. Strukturell vollständig heisst hier: jedes Ticket der Baseline (T-1.1.1 bis T-10.2.1) ist mit Ziel, Scope, Akzeptanzkriterien, Abhängigkeiten und kritischen Risiken beschrieben und in die Sprint-Zuordnung eingepflegt.

Diese strukturelle Vollständigkeit bedeutet nicht:

- dass die Tickets implementiert sind,

- dass sie getestet oder freigegeben sind,

- dass eine Coding-Freigabe erteilt wurde,

- dass die Sprint-Pläne produktiv umgesetzt wurden.

Innerhalb der strukturellen Baseline-Planung haben T-7.3.1 (Promotion-Pipeline Stufen 1–2) und T-7.3.2 (Promotion-Pipeline Stufe 3) eine bedingte Verortung zwischen Sprint 2 und Sprint 3. Je nachdem, wie diese beiden Tickets im tatsächlichen Umsetzungsfall angesteuert werden, bleiben sie entweder regulär in der Sprint-Struktur verortet oder hängen als letzte offene Baseline-Tickets nach.

Alle weiteren Aussagen zur Implementierungsreife, zum Testabschluss oder zur produktiven Freigabe sind nicht Teil dieser Fassung.

4.  WAS BEWUSST AUSSERHALB DER BASELINE LIEGT

Die folgenden Themen sind nicht Teil der Delivery Backlog Baseline v1.0 und bleiben bewusst späteren Phasen vorbehalten:

- Kalibrierung: OCR-Konfidenzgrenzen, Vokalisierungsschwellenwerte, Aggregationslogik-Schwellenwerte, Häufungsschwellenwerte der §4.18-Spur-2-Klasse-B-Generallogik, Konfidenzschwelle für Qurʾān-Erkennung – strukturell angelegt und konfigurierbar gedacht, Kalibrierung nach Gold-Corpus-Tests und realer Messung.

- Live-Testpaket Schnittstelle 5: Die E-5-Testbetriebsfragen sowie die konkreten Werte zu Raten, Backoff, Obergrenzen, Wiederaufnahme und Timeout-/Retry-Werten pro Quelle bleiben als separater Volltext-Arbeitsblock in Block 3 geführt und geparkt bis zur realen Ausführung.

- UI-Ausbau: Why-Panel-Rendering, Historien-Darstellungen, Befund-Verwaltungsoberfläche, Preflight-UI, Export-Dialog. Die strukturelle Backend-Grundlage ist in der Baseline angelegt; die ausgearbeitete UI ist eine Produkt-Ausbaustufe.

- Zusätzliche Exportziele: Adobe InDesign / Affinity Publisher Export und weitere Exportformate.

- Weitere Sprachen und Quellsprachen: Erweiterung auf weitere Ausgangs- oder Zielsprachen über die aktuell kanonisierten Sprachpaare hinaus.

- Stilfeature-Folgearbeiten: Die in Dokument C v1.1 §3 genannten Folgearbeiten (formale Integrationsanalyse, CRs für Core Architecture / Engineering Execution / Delivery Backlog Baseline, Audit-Integration, Ticket-Definition, Sprint-Planung, Kalibrierung der offenen Schwellenwerte, Coding-Freigabe) bleiben ausdrücklich offen.

- Reale Shamela-Ist-Aufnahme (Schnittstelle 6): Inklusive Rückspielung R-1 bis R-7 und hadithbezogenem P-2-Abgleich – geparkt.

- Produktisierung und Skalierung: Gastnutzer-Timeout-Kalibrierung, Upload-Chunk-Grössen, Performance-Optimierungen, Datenbankindizes, Mandantenfähigkeit und alles, was über die Einzelnutzer-Übersetzungsplattform hinausgeht.

5.  ARBEITSREGEL FÜR DIE ZUKUNFT

Für alle weiteren Arbeiten an den Baselines und Sprint-Plänen gelten folgende Regeln:

1.  Keine stillen Änderungen. Jede inhaltliche Änderung an einem kanonischen Dokument wird als expliziter Änderungsantrag geführt, mit Angabe des betroffenen Dokuments, der betroffenen Stelle, des Änderungsgrundes und einer Versionsfortschreibung.

2.  Keine verdeckte Weiterentwicklung. Neue Anforderungen, neue Features oder neue Architekturentscheide werden nicht innerhalb bestehender Versionsnummern untergebracht, sondern als neue Versionen oder neue Dokumente ausgewiesen.

3.  Keine neuen Baselines ohne explizite Freigabe. Jede neue Planungsebene – ob neue Architektur-Schicht, neue Backlog-Version oder neue Sprint-Planung – erfordert eine explizite Freigabeentscheidung.

4.  Explizite Ablösung bei neuem Material. Tauchen später authentischeres Quellmaterial oder authentische Fragmente auf, wird die betroffene Fassung in einem expliziten Schritt durch eine neue bereinigte Fassung auf Basis dieses Materials abgelöst oder erneut bereinigt. Eine stille Umwidmung ist nicht zulässig.

5.  Kein Code und keine Implementierungsfreigabe ohne ausdrücklichen Auftrag. Strukturelle Vollständigkeit der Planung bedeutet nicht Implementierungsfreigabe.

Waraq Baseline Delivery Plan v1.0 – Ende der Fassung
