<!-- Converted from "DOKUMENT C v1.1 - Integrationsnachricht Stilfeature.docx" via pandoc 3.9.0.2 on 2026-05-02 -->
<!-- The .docx in this directory remains source-of-truth per docs/canon/README.md authority rule -->
<!-- Conversion is content-faithful (text, tables, identifiers, Swiss German ss, Arabic RTL spans, §-refs); Word-specific visual styling is dropped -->

**WARAQ – DOKUMENT C v1.1 Integrationsnachricht: „Erkenne meinen Übersetzungsstil" Nachfolgefassung von Dokument C v1.0**

**Kein Code. Keine Coding-Freigabe. Keine stille Architekturänderung. Kein stilles Re-Baselining. Keine neue Feature-Ausweitung. Dieses Dokument ist die Integrationsnachricht. Es enthält keine Implementierung und keinen Code. Es ist die Grundlage, auf deren Basis danach die eigentlichen Änderungsanträge und die Implementierungsreife weitergeführt werden.**

**Einordnung dieser Fassung: Dokument C v1.1 ist die Nachfolgefassung von Dokument C v1.0. Dokument C v1.1 ist keine neue Baseline-Verschiebung, keine Implementierungsfreigabe und führt keine neue Architektur ein. Dokument A und Dokument B v1.2 bleiben unverändert eingefroren. Die OCR-Export-Endfassung v1.3 bleibt separat eingefroren und vom Stilfeature getrennt.**

**VORRANGLOGIK (UNVERÄNDERLICH – WIRD IN DIESEM DOKUMENT AN KEINER STELLE VERSCHOBEN)**

1.  **Bereits freigegebene allgemeine Systemregeln (Dokument 1 und Baselines v1.0)\**

2.  **Kanonischer Nutzerstil (Dokument A + Dokument B v1.2)\**

3.  **Einzelne Referenzsätze (Referenzkorpus aus Dokument A – als strukturierte zweisprachige Stilbelege)\**

4.  **EINORDNUNG DES FEATURES IN DEN BESTEHENDEN WARAQ-KANON\**

**1.1 Was jetzt neu gilt**

**Mit Einfrierung von Dokument A und Dokument B v1.2 gilt:**

| **Dokument** | **Status** | **Rang in der Vorranglogik** |
|----|----|----|
| **Waraq Core Architecture Baseline v1.0** | **Eingefroren, kanonisch** | **Rang 1 (Systemregeln)** |
| **Waraq Implementation Translation Baseline v1.0** | **Eingefroren, kanonisch** | **Rang 1 (Systemregeln)** |
| **Waraq Engineering Execution Baseline v1.0** | **Eingefroren, kanonisch** | **Rang 1 (Systemregeln)** |
| **Waraq Delivery Backlog Baseline v1.0** | **Eingefroren, kanonisch** | **Rang 1 (Systemregeln)** |
| **OCR-Export-Endfassung v1.3** | **Eingefroren, kanonisch, vom Stilfeature getrennt** | **Nicht Teil der Vorranglogik dieses Features** |
| **Dokument A – Kanonischer Nutzerstil-Korpus v1.0** | **Eingefroren, kanonisch** | **Rang 2 (Nutzerstil)** |
| **Dokument B v1.2 – Feature-Spezifikation „Erkenne meinen Übersetzungsstil"** | **Eingefroren, kanonisch** | **Rang 2 (Nutzerstil)** |
| **Einzelne Referenzsätze (Referenzkorpus Dokument A)** | **Gültig als Stilbelege** | **Rang 3** |

**1.2 Einordnung innerhalb des bestehenden Produktworkflows**

**Das Feature „Erkenne meinen Übersetzungsstil" ist dem bestehenden Produktworkflow zuzuordnen:**

- **Phase 5 – Übersetzung: Das Stilprofil wirkt als zusätzliche Schicht auf den KI-Übersetzungsvorschlag. Option A (KI-Standard) bleibt Ausgangslage.**

- **Stilprofil Option B (gemäss Dokument B v1.2): Das Feature ist die strukturierte Operationalisierung dieses Konzepts. Es ersetzt das Konzept nicht, sondern definiert, wie das Stilprofil aufgebaut, gelernt, versioniert und angewendet wird.**

- **„Erkenne meinen Stil"-Algorithmus: Dokument B v1.2 ist für Stilfragen innerhalb von Rang 2 massgeblich. Allgemeine Systemregeln aus Rang 1 werden dadurch nicht berührt und nicht übersteuert. Eine allgemeine Vorrangregel zwischen Dokument B v1.2 und einer übergeordneten Quelle wird daraus nicht abgeleitet.**

**1.3 Was das Feature nicht ist**

- **Kein Ersatz für Option A (KI-Standard)**

- **Kein Eingriff in die OCR-Phase oder den OCR-Export-Strang**

- **Keine Neudefinition von Glossar, Transliteration, Terminologie-Verzeichnis, religiösen Formeln oder Koranvers-/Hadith-Behandlung**

- **Keine neue Baseline für das Gesamtsystem**

- **Kein eigenständiges Übersetzungsmodul**

2.  **BESTÄTIGUNG: KEINE ÜBERSCHREIBUNG BESTEHENDER SYSTEMREGELN**

**2.1 Ausdrückliche Bestätigung \[KANON\]**

**Dokument A und Dokument B v1.2 überschreiben keine bestehenden Systemregeln. Im Einzelnen:**

| **Systemregel** | **Status nach Einfrierung von Dok. A + B v1.2** |
|----|----|
| **Transliteration EI2 (Q/J)** | **Unverändert. Stilprofil-Einträge, die widersprechen, werden unterdrückt.** |
| **Glossar (Vorrang, nie automatisch überschreibbar)** | **Unverändert. Glossar hat immer Vorrang vor Stilprofil.** |
| **Terminologie-Verzeichnis** | **Unverändert. Vorrang vor Stilprofil.** |
| **Religiöse Formeln-Verzeichnis** | **Unverändert. Vorrang vor Stilprofil.** |
| **Qurʾān-Stellenbehandlung gemäss §4.15 (arabischer Qurʾān-Referenzbestand für arabischen Referenztext und Vokalisierung; quranenc.com bzw. lokale Fallback-Kopie für Zielsprachen-Übersetzungen)** | **Unverändert. Externe Quelle hat Vorrang. Stilprofil gilt nicht für Koranvers-Texte.** |
| **Hadith-Behandlung (Verifikationsquellen-Hierarchie)** | **Unverändert. Verifikationslogik hat Vorrang.** |
| **Fachbegriff-Behandlung (erstes / Folgeauftreten)** | **Unverändert.** |
| **OCR-Export-Strang (Endfassung v1.3)** | **Unverändert. Stilprofil gilt nicht für OCR-Export-DOCX.** |
| **Harte Invarianten H-1 bis H-7** | **Unverändert.** |
| **Governable Project Rules G-1 bis G-4** | **Unverändert.** |
| **Delivery Backlog Baseline v1.0** | **Stilfeature-Backlog-Schicht (CR-3, §7) verankert; Implementierungs-Sprint-Tickets / Coding-Freigabe offen.** |

**2.2 Auch manuelle Stilregeln sind subordiniert \[KANON\]**

**Auch manuell durch den Nutzer eingegebene Stilregeln (Dokument B v1.2, Abschnitt 3.1) sind vollumfänglich der Vorranglogik unterworfen. Sie können keine Systemregel aufheben.**

3.  **NOTWENDIGE FOLGEARBEIT**

**Die Einfrierung von Dokument A und Dokument B v1.2 erzeugt eine Reihe von Folgearbeiten, die noch nicht erledigt sind. Diese Folgearbeiten sind hier strukturiert aufgelistet – sie sind noch keine Tickets und noch keine freigegebenen Implementierungs-CRs. Sie sind der Ausgangspunkt für die nächste Arbeitsphase.**

**3.1 Formale Integrationsanalyse**

**Folgende Fragen müssen vor der Implementierungsreife des Features formal beantwortet werden:**

| **Frage** | **Status** |
|----|----|
| **Welche bestehenden Baselines müssen angepasst werden, um das Feature aufzunehmen?** | **Offen – Analyse erforderlich** |
| **Welche bestehenden Tabellen / Datenmodell-Objekte müssen erweitert werden?** | **Offen – Analyse erforderlich** |
| **Wie verhält sich das Feature gegenüber dem bestehenden Übersetzungs-Job-Modell (Recovery, Provenance)?** | **Offen – Analyse erforderlich** |
| **Wie wird das Stilprofil im Provenance-Modell / EXPORT_EVENT abgebildet?** | **Offen – Analyse erforderlich** |
| **Wie verhält sich das Stilprofil gegenüber dem bestehenden Revisionsmodell?** | **Offen – Analyse erforderlich** |
| **Wie werden Stilprofil-Versionen in der werkweiten Konsistenzprüfung (K-01–K-07) berücksichtigt?** | **Offen – Analyse erforderlich** |
| **Wie verhält sich das Feature gegenüber dem Übersetzungs-Audit (A-01–D-03)?** | **Offen – Analyse erforderlich** |

**3.2 Notwendige CRs und Dokumentänderungen**

**Die folgenden Dokumente und Baselines werden durch das Feature berührt. Die Schema- und Schichtanker für CR-1 / CR-2 / CR-3 sind in den bereinigten Baselines verankert; die ausstehenden Implementierungs-CRs / Sprint-Tickets / Coding-Freigabe bleiben offen:**

| **Betroffenes Dokument / Baseline** | **Art der Berührung** | **CR-Status** |
|----|----|----|
| **Waraq Core Architecture Baseline v1.0** | **Erweiterung: Stilprofil-Objekte, Lernlogik, Versionierung** | **Schema-Anker verankert (CR-1, §B.6 / §B.7); Implementierungs-CRs offen** |
| **Waraq Engineering Execution Baseline v1.0** | **Erweiterung: Ausführungsregeln für Stilprofil-Anwendung, Job-Modell** | **Schicht-Anker verankert (CR-2, §11); Implementierungs-CRs offen** |
| **Waraq Delivery Backlog Baseline v1.0** | **Stilfeature-Backlog-Schicht** | **Schicht-Anker verankert (CR-3, §7); Implementierungs-Sprint-Tickets / Coding-Freigabe offen** |
| **Sprint-Planung** | **Das Feature braucht einen eigenen Sprint-Slot** | **Noch nicht geplant – kein Auftrag** |
| **Waraq Implementation Translation Baseline v1.0** | **Stilfeature-Verstösse in Audit-Struktur (A-01–D-03)** | **Schicht-Anker verankert (CR-2, §4.6a); Implementierungs-CRs offen** |

**3.3 Betroffene Kernobjekte, Tabellen und Regeln**

**Auf Basis von Dokument B v1.2 sind folgende neue Kernobjekte identifiziert, die in der Architecture Baseline noch nicht existieren:**

| **Neues Objekt** | **Herkunft** | **Zustand** |
|----|----|----|
| **stil_regel (mit allen Feldern aus Dok. B v1.2 Abschnitt 5.2)** | **Dokument B v1.2** | **Identifiziert, noch nicht in Baseline** |
| **stilbeleg (zweisprachiger strukturierter Beleg, Dok. B v1.2 Abschnitt 4.2)** | **Dokument B v1.2** | **Identifiziert, noch nicht in Baseline** |
| **stilprofil_version (Versionierungsmodell, Dok. B v1.2 Abschnitt 9.2)** | **Dokument B v1.2** | **Identifiziert, noch nicht in Baseline** |
| **referenz_paar (bestätigtes AR/DE-Paar als Trainingsquelle)** | **Dokument B v1.2** | **Identifiziert, noch nicht in Baseline** |
| **Phänomenfeld-Enum PF-01 bis PF-12** | **Dokument B v1.2 Abschnitt 4.3** | **Identifiziert, noch nicht in Baseline** |
| **Zustandsmodell-Enum für stil_regel.status** | **Dokument B v1.2 Abschnitt 8.2** | **Identifiziert, noch nicht in Baseline** |
| **Regeltyp-Enum (invariant / präferenz / tendenz / kandidat)** | **Dokument B v1.2 Abschnitt 6** | **Identifiziert, noch nicht in Baseline** |

**Bestehende Objekte, die voraussichtlich erweitert werden müssen:**

| **Bestehendes Objekt** | **Art der Erweiterung** | **Zustand** |
|----|----|----|
| **account** | **Verknüpfung mit aktivem Stilprofil** | **Analyse ausstehend** |
| **decision_event** | **Prüfung, ob Stilprofil-Entscheidungen als Decision-Events modelliert werden** | **Analyse ausstehend** |
| **Übersetzungs-Job / Recovery-Modell** | **Integration der Stilprofil-Version in den Job-Kontext** | **Analyse ausstehend** |
| **Provenance-Modell / EXPORT_EVENT** | **Ob und wie die angewendete Stilprofil-Version im Export-Provenance abgebildet wird** | **Analyse ausstehend** |

**3.4 Audit- und Qualitätslogik**

**Die folgende Audit- und Qualitätslogik ist durch Dokument B v1.2 definiert und muss bei der Implementierungsreife formal in die bestehende Audit-Struktur (A-01–D-03) integriert werden:**

| **Audit-Aspekt** | **Herkunft** | **Zustand** |
|----|----|----|
| **Protokollierung jeder Stilprofil-Anwendung (Version, Einträge, Zeitpunkt)** | **Dok. B v1.2 Abschnitt 11.4** | **Definiert, noch nicht in Audit-Baseline** |
| **Protokollierung jedes Konflikts mit Systemregeln (inkl. Zustandsübergang)** | **Dok. B v1.2 Abschnitt 8.4** | **Definiert, noch nicht in Audit-Baseline** |
| **Protokollierung jedes Stilprofil-Versions-Wechsels (delta)** | **Dok. B v1.2 Abschnitt 9.2** | **Definiert, noch nicht in Audit-Baseline** |
| **Keine verdeckte Stilanwendung – jede Anwendung ist kenntlich** | **Dok. B v1.2 Abschnitt 11.2** | **Definiert, noch nicht in Audit-Baseline** |
| **Phänomenfeld-Abdeckungsanzeige (für Nutzer)** | **Dok. B v1.2 Abschnitt 10.4** | **Definiert – Konfig, noch nicht spezifiziert** |

4.  **KANONISCH vs. KONFIGURIERBAR vs. KALIBRIERBAR – GESAMTÜBERSICHT**

**4.1 Was kanonisch ist (unveränderlich, kein Ermessen)**

- **Accountbindung absolut (keine Teilen-Funktion in diesem Feature)**

- **Nur bestätigtes zweisprachiges Material als Lernquelle**

- **Explizite Nutzeraktivierung und Nutzerbestätigung bei jedem Stilbeleg**

- **Lernquellen-Asymmetrie (akzeptierte KI-Vorschläge dürfen keine Invarianten oder starken Regeln erzeugen)**

- **Invariante entsteht nur durch explizite Nutzerhandlung – nie durch Statistik**

- **Keine verdeckte Stilanwendung**

- **Systemregel hat immer Vorrang – auch über manuelle Stilregeln**

- **Abgeschlossene Seiten werden durch spätere Stilprofil-Änderungen nie verändert**

- **Vollständige Protokollierung und Auditierbarkeit**

- **Stilprofil gilt nicht für OCR-Export-Strang**

- **Stilprofil-Rollback-Funktion ist standardmässig aktiv (vgl. Dokument B v1.2 §9.4)**

**4.2 Was produktkonfigurierbar ist**

- **Abo-Freischaltung des Features (Ja/Nein)**

- **Welche Accountklassen Zugang erhalten**

- **Phänomenfeld-Abdeckungsanzeige (Darstellungsform)**

- **UI-Ausgestaltung der Rollback-Bedienung (vgl. Dokument B v1.2 §9.4; Funktion selbst ist standardmässig aktiv)**

**4.3 Was kalibrierbar ist (noch nicht festgelegt)**

- **Mindestanzahl Referenzsätze für Aktivierung**

- **Konfidenz-Schwellen: Kandidat → Tendenz → Präferenz**

- **Konfidenz-Schwelle für automatische Anwendung (Präferenz)**

- **Mindestbelegdichte pro Phänomenfeld (PF-01 bis PF-12)**

**Alle Kalibrierungspunkte sind nach Gold-Corpus-Tests festzulegen. Sie sind keine offenen Architekturentscheidungen, sondern offene Messwerte.**

5.  **KONFLIKTE MIT BESTEHENDEN REGELN – AUSSCHLUSSLISTE**

**Die folgenden Konflikte sind durch die Vorranglogik und Dokument B v1.2 bereits strukturell ausgeschlossen. Sie dürfen bei der Implementierung weder entstehen noch still toleriert werden:**

| **Möglicher Konflikt** | **Ausschluss-Mechanismus** |
|----|----|
| **Stilprofil überschreibt Glossar-Eintrag** | **Systemregel-Vorrang; Status unterdrückt_durch_systemregel** |
| **Stilprofil überschreibt Transliterationsregel** | **Systemregel-Vorrang; Schreibweise wird angepasst** |
| **Stilprofil überschreibt Terminologie-Verzeichnis** | **Systemregel-Vorrang; Status unterdrückt_durch_systemregel** |
| **Stilprofil überschreibt religiöse Formel** | **Systemregel-Vorrang; Status unterdrückt_durch_systemregel** |
| **Stilprofil wendet sich auf Qurʾān-Stellen gemäss §4.15 an** | **Strukturell ausgeschlossen; Stilprofil gilt nicht für Koranvers-Kontext** |
| **Stilprofil wendet sich auf Hadith-Texte an** | **Strukturell ausgeschlossen; Verifikationslogik hat Vorrang** |
| **Stilprofil wirkt auf OCR-Export-DOCX** | **Strukturell ausgeschlossen; OCR-Export ist Quelltext** |
| **Akzeptierte KI-Vorschläge erzeugen Invariante** | **Strukturell ausgeschlossen durch Lernquellen-Asymmetrie** |
| **Statistik allein erzeugt Invariante** | **Strukturell ausgeschlossen; Invariante nur durch explizite Nutzerhandlung** |
| **Manuelle Stilregel hebt Systemregel auf** | **Strukturell ausgeschlossen; Systemregel hat immer Vorrang** |
| **Stilprofil eines Accounts wirkt auf anderen Account** | **Strukturell ausgeschlossen; Accountbindung absolut** |
| **Unbestätigtes Material fliesst in Stilprofil** | **Strukturell ausgeschlossen; nur bestätigtes Material** |
| **Abgeschlossene Seiten werden rückwirkend geändert** | **Strukturell ausgeschlossen; Unveränderlichkeit** |
| **Stille Stilanwendung ohne Kenntlichmachung** | **Strukturell ausgeschlossen; Transparenzpflicht** |

6.  **ACCOUNTBINDUNG UND NICHT-GLOBALITÄT**

**6.1 Grundsatz \[KANON\]**

**Das Stilprofil ist absolut accountgebunden. Es ist zu keinem Zeitpunkt ein globaler Standard und gilt nicht für andere Accounts.**

**6.2 Anforderungen an die Accountbindung**

| **Aspekt** | **Anforderung** |
|----|----|
| **Datenhaltung** | **Alle Stilprofil-Objekte (stil_regel, stilbeleg, stilprofil_version, referenz_paar) müssen an eine account_uuid gebunden sein** |
| **Abfragen** | **Jede Abfrage auf Stilprofil-Objekte muss die account_uuid als Pflichtfilter führen** |
| **Anwendung** | **Die Stilprofil-Anwendung auf einen Übersetzungsvorschlag verwendet ausschliesslich das Stilprofil des aktuell authentifizierten Accounts** |
| **Kein Cross-Account-Zugriff** | **Kein Mechanismus darf Stilprofil-Daten eines Accounts für einen anderen Account zugänglich machen** |
| **Keine globale Aggregation** | **Das System darf keine kontenübergreifenden Stilmuster ableiten oder anwenden** |
| **Teilen-Funktion** | **Ist nicht Teil dieses Features. Wenn später gewünscht: separater CR erforderlich** |

7.  **GEMEINSAME BEHANDLUNG VON DOKUMENT A UND DOKUMENT B v1.2 ALS GRUNDLAGE FÜR IMPLEMENTIERUNGSREIFE**

**7.1 Verhältnis der beiden Dokumente zueinander**

| **Dokument** | **Rolle** |
|----|----|
| **Dokument A** | **Inhaltliche Stilgrundlage: Referenzkorpus, harte Stil-Invarianten, Phänomenfelder, Fehler-Negativliste. Keine eigenständige Implementierungsanweisung.** |
| **Dokument B v1.2** | **Strukturierte Feature-Spezifikation: Datenmodell-Objekte, Lernlogik, Konfliktlogik, Zustandsmodell, Versionierung, Audit-Logik. Keine eigenständige Implementierungsanweisung.** |
| **Dokument A + B v1.2 gemeinsam** | **Zusammen bilden sie die inhaltliche und strukturelle Grundlage, auf der die Implementierungsreife aufgebaut werden muss. Weder allein ist vollständig.** |

**7.2 Was noch fehlt für vollständige Implementierungsreife**

| **Fehlender Schritt** | **Voraussetzung** |
|----|----|
| **Formale Integrationsanalyse (Abschnitt 3.1)** | **Muss vor dem ersten Implementierungs-CR abgeschlossen sein** |
| **Implementierungs-CRs für die im §3.2 genannten Baselines** | **Erst nach Integrationsanalyse und explizitem Auftrag** |
| **Ticket-Definition im Delivery Backlog** | **Erst nach Implementierungs-CR-Freigabe** |
| **Sprint-Planung** | **Erst nach Ticket-Definition und explizitem Auftrag** |
| **Kalibrierung der offenen Schwellenwerte (Abschnitt 4.3)** | **Nach Gold-Corpus-Tests – nicht vor erster Implementierung zwingend festzulegen** |
| **Coding-Freigabe** | **Erst nach abgeschlossener Integrationsanalyse, freigegebenen Implementierungs-CRs und Ticket-Definition** |

**7.3 Reihenfolge der Folgeschritte (orientierend, kein Sprint-Plan)**

**Die folgende Reihenfolge ergibt sich aus dem bestehenden CR- und Implementierungsprozess des Waraq-Kanons. Sie ist orientierend, kein verbindlicher Sprint-Plan und noch kein Auftrag:**

1.  **Formale Integrationsanalyse (Abschnitt 3.1 dieses Dokuments)\**

2.  **Implementierungs-CR-Eröffnung für die im §3.2 genannten Baselines\**

3.  **CR-Durchlauf: Analyse → Entscheidungen → CRs → Tickets → Sprint → Freigabe\**

4.  **Ticket-Definition und Aufnahme in Delivery Backlog\**

5.  **Sprint-Slot-Planung (nur auf expliziten Auftrag)\**

6.  **Coding-Freigabe (nur auf expliziten Auftrag)\**

7.  **AKTUELLER HANDLUNGSSTATUS\**

**Was jetzt eingefroren ist:**

| **Dokument** | **Status** |
|----|----|
| **Dokument A – Kanonischer Nutzerstil-Korpus v1.0** | **Eingefroren** |
| **Dokument B v1.2 – Feature-Spezifikation „Erkenne meinen Übersetzungsstil"** | **Eingefroren** |
| **OCR-Export-Endfassung v1.3** | **Eingefroren, vom Stilfeature getrennt** |
| **Dokument C v1.1 – Integrationsnachricht** | **Eingefroren als Integrationsrahmen (§3-Folgearbeiten offen)** |

**Was jetzt offen ist:**

- **Formale Integrationsanalyse (kein Auftrag erteilt)**

- **Implementierungs-CRs für die in §3.2 genannten Baselines (nicht eröffnet)**

- **Ticket-Definition (nicht erstellt)**

- **Sprint-Planung (kein Auftrag)**

- **Kalibrierungswerte (nach Gold-Corpus-Tests)**

- **Coding-Freigabe (nicht erteilt)**

**Was jetzt nicht passiert:**

- **Kein Code**

- **Keine Coding-Freigabe**

- **Keine Implementierung**

- **Kein stilles Re-Baselining**

- **Keine neue Feature-Ausweitung**

- **Keine neue Architektur ohne CR**

**Dokument C v1.1 – Integrationsnachricht „Erkenne meinen Übersetzungsstil" – Nachfolgefassung von Dokument C v1.0. Dokument A und Dokument B v1.2 sind eingefroren und gelten als kanonische Grundlage für alle weiteren Schritte. OCR-Export-Endfassung v1.3 bleibt separat eingefroren und vom Stilfeature getrennt. Nächster Schritt nur auf explizite Nutzeranweisung.**
