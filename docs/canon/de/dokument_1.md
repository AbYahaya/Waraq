<!-- Converted from "Dokument 1 _ Kanon (1).docx" via pandoc 3.9.0.2 on 2026-05-02 -->
<!-- The .docx in this directory remains source-of-truth per docs/canon/README.md authority rule -->
<!-- Conversion is content-faithful (text, tables, identifiers, Swiss German ss, Arabic RTL spans, §-refs); Word-specific visual styling is dropped -->

# **DOKUMENT 1 – LEBENDES MASTER-DOKUMENT (KANON)**

Einzige kanonische Hauptquelle – bereinigte Volltextfassung.

KRITISCH: Keine Umformulierung der Substanz. Keine Vereinfachung, die Sinn verändert. Kein stilles Re-Baselining. Diese bereinigte Fassung enthält ausschliesslich kosmetische, strukturelle und sprachlich-substanzielle Schärfungen. Inhaltliche Substanz ist unverändert.

## **1. PROJEKTIDENTITÄT**

- **Name**: Waraq (<span dir="rtl">ورق</span>) – arabisch für „Blatt/Seite".

- **Kurzbeschreibung**: Professionelle Publishing-Plattform für arabisch→deutsch/englisch Buchübersetzungen.

- **Ziel**: Druckfertige Bücher aus arabischen Scans/PDFs produzieren.

- **Problem**: Professionelle Übersetzer islamischer und historischer arabischer Texte haben kein spezialisiertes Werkzeug, das OCR, Übersetzung, Stilprofil, Verzeichnisse und Export in einem durchgängigen Workflow vereint.

- **Zielgruppe**: Verlage und Übersetzer islamischer und historischer arabischer Texte.

- **Zugang**: Internes Tool mit Bewerbungssystem – Administrator entscheidet über Zugang.

- **Kernversprechen**: Vom arabischen Scan zum druckfertigen deutschen oder englischen Buch in einem einzigen, auditierbaren Workflow.

**Unterstützte Sprachkombinationen:**

- Arabisch → Deutsch

- Arabisch → Englisch

- Englisch → Deutsch

- Deutsch → Englisch

**Übersetzungs-Transfer:** AR→DE bereits vorhanden → EN unter Berücksichtigung des deutschen Stils.

## **2. FESTSTEHENDES KONZEPT**

### **2.1 Verbindliche Module und Features**

**Phasen:**

- **Phase 1 – Upload:** alle Formate, Duplikat-Erkennung (SHA-256 Inhalts-Hash primär, Dateiname sekundär), 1 Buch gleichzeitig, max. 2 GB.

- **Phase 2 – OCR:** 5-Stufen-Rekonstruktions-Pipeline (Gemini 2.5 Pro Vision + kraken + Real-ESRGAN + CAMeL Tools + Farasa + Mishkal + LayoutParser + DocTR).

- **Phase 3 – OCR-Review:** Schwierigkeitsbericht, geführter Review, DPI-Vergleichsansicht.

- **Phase 4 – IVZ-Bestätigung:** Vergleichsansicht arabisch/deutsch, Kapitelüberschriften anpassen. Kein IVZ erkannt → seitenweise Aufteilung. Manuelles IVZ-Definieren ist nicht Teil dieser Version. Separater CR, wenn später gewünscht.

- **Phase 5 – Übersetzung:** GPT-4o + Gemini 2.5 Pro parallel, RAG, Chunk-Strategie.

- **Phase 6 – Benachrichtigung + IVZ-Bestätigung:** Nutzer informiert, finales IVZ-Review.

**Sichtbare Archive und Verzeichnisse (5 Stück):**

1.  Glossar (Vorrang vor Lernstil, nie automatisch überschreibbar)

2.  Terminologie-Verzeichnis

3.  Religiöse Formeln-Verzeichnis

4.  Referenz- und Entitäten-System

5.  Stilprofil Option B (accountgebunden)

**Stilfeature „Erkenne meinen Übersetzungsstil":** Vollständig spezifiziert in Dokument A v1.0, Dokument B v1.2 und Dokument C v1.1.

**Export:** DOCX (Word-Template Option B), PDF digital und Druck, OCR-Export-DOCX (getrennt vom Publikationsexport).

**Dateiformate Upload:**

- Bilder: JPG, JPEG, PNG, TIFF, TIF, HEIC, WEBP

- Dokumente: PDF, DOCX, ODT, TXT, XML, HTML

- E-Books: EPUB, MOBI, AZW, AZW3, DjVu

- Archive: ZIP, RAR, CBZ, CBR

- Maximalgrösse: 2 GB

**Format-Logik:**

- ZIP/RAR/CBZ/CBR → automatische Seitensortierung nach Dateiname

- TXT/XML/HTML → OCR übersprungen

- EPUB/MOBI/AZW → direkte Textextraktion

- DjVu → spezieller OCR-Pfad

### **2.2 Verbindliche Produktlogik**

- Glossar hat immer Vorrang vor Lernstil. Keine Einzel-Übersteuerung eines Glossar-Eintrags im Kontext möglich. Wer abweichen will, muss den Eintrag ändern oder löschen.

- Keine leeren Seiten in arabischen Werken.

- Westliche Ziffern überall – nie arabische Ziffern. Verstösse gegen den Ziffernstandard werden Guard-nah behandelt und sind blockierend. Kein Audit-Fall, kein Nutzerurteil – direkter Systemmechanismus.

- Religiöse Formeln als Kalligraphie/Unicode: <span dir="rtl">ﷺ, ﷻ</span>.

- Kopfzeile zeigt Überschrift 2 (Kapitel), nicht Überschrift 1.

- Beim Export wird gefragt, welche Überschriftenebene Kapitel markiert – nie annehmen.

- Transliterationsstandard: EI2 mit Q (statt Ḳ) und J (statt Dj).

- Kein Timeout bei aktivem Hintergrundprozess, sonst 2 Stunden.

- Papierkorb: 10 Tage.

- Duplikat- und 1-Buch-Warnung: Modal-Popup.

- Gastnutzer beforeunload-Warnung: aktiv, solange OCR läuft.

- Benachrichtigungen erfolgen standardmässig via E-Mail und In-App. E-Mail ist durch den Nutzer deaktivierbar.

- Morphologie-Panel: Seitenpanel.

- Wortformen-Häufigkeitsanalyse: Modal-Dialog.

### **2.3 Nutzerzugangssystem**

| **Stufe** | **Name**                    | **Funktion**           |
|-----------|-----------------------------|------------------------|
| 0         | Bewerber                    | Nur Bewerbungsformular |
| 1         | Vollversion Gratis          | Alles komplett         |
| 2         | Vollversion Kostenpflichtig | Alles komplett         |

**Ablaufzeiten:** 1 Woche / 1 Monat / 6 Monate / 1 Jahr.

**Inaktivitätslöschung:** 6 Monate (ausser bei aktivem Abo).

**Warnungen:**

- 1 Monat vor Inaktivitätslöschung per E-Mail.

- 7 Tage vor Abo-Ablauf per E-Mail.

**Abo-Ablauf:** Nach Ablauf eines kostenpflichtigen Abos (Stufe 2) erfolgt automatischer Wechsel zu Stufe 1 (Vollversion Gratis), ohne funktionale Einschränkung. Laufende Projekte bleiben vollständig zugänglich.

**Benutzerdefiniertes Abo (Ja/Nein):** Erkenne meinen Stil, Glossar, Terminologie-Verzeichnis, Religiöse Formeln-Verzeichnis, Referenz-Ordner, max. Seiten pro Werk, max. Werke gesamt.

**Gast-Nutzer:** Upload ohne Account, keine Bearbeitung (Buttons inaktiv), kann Ansichten wechseln. Browser schliessen vor OCR-Fertig → Daten verloren. Solange OCR läuft, ist eine beforeunload-Warnung aktiv. OCR fertig → Account erstellen und Projekt übernehmen möglich.

## **3. FESTSTEHENDE ARCHITEKTUR**

### **3.1 Absolut verbindliche Arbeitsregeln**

- Keine stillen Architekturänderungen – jede Änderung nur als expliziter CR.

- Kein Code ohne explizite Coding-Freigabe des Nutzers.

- Keine neuen Features ohne vollständigen CR-Durchlauf (Analyse → Entscheidungen → CRs → Tickets → Sprint → Freigabe).

- Kein stilles Re-Baselining.

- Keine neue Sprint-Planung ohne expliziten Auftrag.

- Kurz vor Erschöpfung des Kontextfensters (~70 %): Nutzer sofort informieren, dann Übergabedokumente erstellen.

### **3.2 Freigegebene Baselines**

| **Dokument**                                   | **Version** |
|------------------------------------------------|-------------|
| Waraq Core Architecture Baseline               | v1.0        |
| Waraq Implementation Translation Baseline      | v1.0        |
| Waraq Engineering Execution Baseline           | v1.0        |
| Waraq Delivery Backlog Baseline                | v1.0        |
| Sprint-0 bis Sprint-6 Pläne                    | v1.0        |
| OCR Export Konsolidierte Endfassung            | v1.3        |
| Dokument A – Kanonischer Nutzerstil-Korpus     | v1.0        |
| Dokument B – Feature-Spezifikation Stilfeature | v1.2        |
| Dokument C – Integrationsnachricht Stilfeature | v1.1        |
| Kanonische Formatvorlagen-Baseline             | v1.1        |

**3.3 OCR-Engine-Kombination**

Die OCR-Engine-Kombination basiert auf einem mehrstufigen, engine-übergreifenden System. Die konkrete Rollenverteilung der OCR-Engines ist vorläufig kanonisch und revidierbar.

Aktuelle OCR-Leselinien:

Hauptleselinie / Vision-OCR: Gemini 2.5 Pro Vision.

Zusätzliche OCR-Leselinie: Google Cloud Vision (DOCUMENT_TEXT_DETECTION), insbesondere für moderne gedruckte arabische Scans.

Manuskripte und Kalligraphie: kraken + eScriptorium.

Bildvorverarbeitung: Real-ESRGAN + OpenCV (adaptiv).

Validierung: CAMeL Tools + Farasa + Mishkal.

Dokumentstruktur: LayoutParser + DocTR.

Die konkrete Auswahl, Gewichtung und Rollenverteilung der OCR-Leselinien kann je nach Dokumenttyp, Seitenstruktur, Blockklasse und empirischen Testergebnissen angepasst werden. Für moderne gedruckte arabische Scans kann Google Cloud Vision als Basis- oder Primärleser eingesetzt werden, sofern strukturierte Gold-Corpus-Tests dies bestätigen.

Änderungen an der OCR-Engine-Zuweisung erfolgen ausschliesslich auf Basis strukturierter empirischer Tests (Gold-Corpus-Evaluation) und werden in einem separaten Entscheidungsprozess kanonisch festgelegt. Das zugrunde liegende Konsensprinzip aus §3.4 bleibt davon unberührt.

**3.4 OCR – 5-Stufen-Rekonstruktions-Pipeline**

Stufe 1 – Visuelle Struktur-Analyse: Leserichtungs-Karte, Textdichte-Analyse, Baseline-Erkennung, Schriftgrössen-Kartierung, Isolierung dekorativer Elemente, Seitenorientierung pro Block, tabellarische Strukturen, Textspalten, Überschriften-Blöcke, Fussnoten-Bereich, Trennlinien, Seitenzahlen, Koranvers-Blöcke, Randnotizen.

Für Spalten- und Blockreihenfolge gilt: geometrische Reihenfolge-Analyse (x, y, Breite, Höhe), topologische Sortierung als Graph, exakte Lokalisierung der Spalten-Trennlinie, Cross-Validation mit OCR-Text, Anker-Elemente als Referenzpunkte, schräge Zeilen via Hough-Transformation.

Stufe 2 – OCR pro Textblock (separat, nicht gesamte Seite). Ein Textblock kann durch eine oder mehrere OCR-Leselinien gelesen werden. Die Auswahl der Leselinie richtet sich nach Dokumenttyp, Layoutkomplexität, Bildqualität und Blockklasse. Als OCR-Leselinien kommen insbesondere Gemini 2.5 Pro Vision, Google Cloud Vision (DOCUMENT_TEXT_DETECTION) sowie kraken/eScriptorium für Manuskript- und Kalligraphie-Fälle in Betracht. Die konkrete Zuweisung bleibt vorläufig und wird durch Gold-Corpus-Tests validiert.

Stufe 3 – Semantische Rekonstruktion (dreifach validiert):

Regelbasiert: arabische Grammatik.

KI-basiert: GPT-4o und Gemini 2.5 Pro parallel als Konsens-Signalgeber innerhalb der KI-Validierungslinie. Beide Modelle sind gleichrangig; es gibt innerhalb der KI-Linie keine Primär/Prüf-Rollen. Bei Uneinigkeit der beiden Modelle wird kein künstlicher Sieger gebildet; stattdessen sinkt die Konfidenz und die Stelle wird ins OCR-Review priorisiert (siehe Qualitätsprinzip am Ende von §3.4).

Statistisch: Shamela-Datenbank.

Die §3.6-Modellzuweisung (Primär GPT-4o / Prüf Gemini 2.5 Pro) gilt ausschliesslich für die Übersetzungs-Pipeline und bleibt von dieser KI-Validierungslinie unberührt.

Revidierbarkeit der KI-Modellwahl in Stufe 3: vorläufig kanonisch. Eine Revision der konkreten Modellwahl erfolgt ausschliesslich in einem strukturierten Entscheid bei neueren oder klar besseren Modellen, auch innerhalb derselben Modellfamilie. Keine stille Modellwechsel-Änderung. Die Revision betrifft ausschliesslich die Modellwahl, nicht die Konsens-Architektur innerhalb der KI-Validierungslinie.

Das Konsensprinzip der semantischen Rekonstruktion ist unabhängig von der konkreten Auswahl der OCR-Leselinien. Zusätzliche OCR-Leselinien wie Google Cloud Vision verändern nicht das Prinzip der Konsensbildung, sondern liefern weitere Lesesignale für die Bewertung eines Blocks.

Stufe 4 – Zeilenrekonstruktion: Wort-Wahrscheinlichkeits-Modell, Zeilen-Kontinuitäts-Score, Silben-Trennungs-Erkennung, Homoglyphen-Korrektur (<span dir="rtl">ر/ز, د/ذ</span> etc.).

Stufe 5 – Qualitätsprüfung: seitenweise Vollständigkeits-Check, Zeichenanzahl-Plausibilität, strukturelle Symmetrie bei Mehrspaltensatz, Matching bekannter Passagen (Koran, Hadith).

Übergreifendes OCR-Qualitätsprinzip: Wenn nach Durchlauf der vorgesehenen Rekonstruktionsstufen mehrere starke konkurrierende Lesungen bestehen bleiben, wird kein künstlicher Sieger gebildet. Die Konfidenz sinkt, die Stelle wird im OCR-Review priorisiert.

### **3.5 Externe Quellen und Datenbanken**

**Offline lokal (serverseitig):**

- **<span dir="rtl">مكتبة الشاملة</span> (Shamela)** – vollständige Datenbank inkl. Lisān al-ʿArab und Tāj al-ʿArūs. Lisān al-ʿArab (20+ Bände) und Tāj al-ʿArūs (40 Bände) werden innerhalb Shamela als eigenständig abfragbare Einheiten behandelt; Suche innerhalb einzelner Werke ist möglich, nicht nur über den Gesamtbestand.

- Shamela wird in zwei funktional getrennten Modi genutzt:

  - **Modus A – OCR-intern:** systemausgelöst in OCR-Stufe 3 (semantische Rekonstruktion) als Plausibilitätsprüfung erkannter Textfragmente.

  - **Modus B – nutzergesteuert:** lexikalische Recherche und Fussnoten-Erstellung in der Übersetzungsphase.

- Die Datenquelle ist in beiden Modi dieselbe; Auslöser, Zweck und Ergebnisverarbeitung unterscheiden sich.

**APIs:**

- quranenc.com – Koranverse (german_rwwad für Deutsch, english_rwwad für Englisch)

- sunnah.com – Hadith-Verifikation

- dorar.net – Hadith

**Web-Scraping (Playwright):** islamweb.net, <span dir="rtl">جامع السنة النبوية, المكتبة الوقفية</span>.

**Scraping-Zweitpfad-Regel:** Scraping ist strikter Zweitpfad gegenüber einer vorhandenen API derselben Quelle. Für dorar.net gilt: API-Pfad primär, Scraping nur als Rückfall bei nicht abgedecktem Funktionsumfang der API. Ein DOM-Bruch wird als §4.18-Klasse-B-Ausfall ohne Retry behandelt; keine stille Selbstheilung zur Laufzeit.

**Anfrageprofil externer Quellen (Modell U):** Externe HTTP-basierte Quellen (APIs und Scraping-Pfade) folgen einem einheitlichen konservativen Anfrageprofil. Lokale Quellen sind ausgenommen; Shamela als lokaler Bestand ist ausdrückliche Ausnahme. Konkrete Raten, Pausen, Obergrenzen und Wiederaufnahme-Zeiten bleiben offen und werden nach realer Messung festgelegt.

**Konfidenz-Ranking der Hadith-Quellen:** quranenc \> sunnah \> Shamela \> dorar \> islamweb \> weitere.

Für die Hadith-Verifikation (§4.16) wird das lineare Konfidenz-Ranking durch eine domänenspezifische mehrdimensionale Vergleichs- und Konsenslogik präzisiert; das lineare Ranking greift in diesem Fall als Tie-Breaker, wenn die Konsenslogik keinen klaren Sieger ergibt.

**Arabischer Qurʾān-Referenzbestand (AR-Referenzbestand):** Eigener lokaler Bestand mit vokalisiertem arabischem Qurʾān-Text. Kanonischer Träger für arabischen Referenztext und Vokalisierung gemäss §4.15. Konkrete Quellenbenennung und Update-Mechanismus noch offen.

**Lokal-Fallback Qurʾān-Übersetzungen:** Vollständige lokale Kopien der german_rwwad- und english_rwwad-Übersetzungen. Primär ist immer quranenc.com API. Fallback nur bei API-Ausfall. Wöchentlicher automatischer Abgleich auf Updates.

**Spezifikationsstatus externer Quellen:**

- Alle externen Quellen: API-Endpunkte, Authentifizierung, Rate-Limits, Fehlerverhalten und Scraping-Strukturen sind vollständig unspezifiziert – aktive Arbeitsfront.

- Schnittstellen-Arbeitsentwürfe (1 OCR-Hauptengine, 2 OCR-semantische Zusatzvalidierung, 3 Übersetzungs-KI, 4 Qurʾān, 5 Hadith, 6 Shamela/Lexikon) liegen vor, sind aber noch kein Kanon.

- Modellzuweisung Primär/Prüf für Übersetzungs-KI ist in §3.6 kanonisch festgelegt; OCR-Stufe 3 hat eigene Logik (siehe §3.4).

### **3.6 Übersetzungs-Pipeline**

**Modellzuweisung:**

- **Primär** (führender Übersetzungsentwurf): GPT-4o.

- **Prüf** (parallele Gegenübersetzung und Qualitätsprüfung): Gemini 2.5 Pro.

- Die Zuweisung gilt systemweit für die §3.6 Übersetzungs-Pipeline. Die Modellzuweisung in der OCR-semantischen Rekonstruktion (§3.4 Stufe 3) ist davon nicht berührt und bleibt eigenständig.

**Revidierbarkeit der Modellzuweisung:** Die konkrete Modellzuweisung (Primär GPT-4o / Prüf Gemini 2.5 Pro) ist vorläufig kanonisch und bildet den aktuell besten verfügbaren Stand ab. Sie bleibt verbindlich, bis sie in einem strukturierten Entscheid neu bewertet und ausdrücklich revidiert wird. Eine Neubewertung ist insbesondere dann angezeigt, wenn neuere oder klar bessere Modelle verfügbar werden – auch innerhalb derselben Modellfamilie. Die Revision betrifft ausschliesslich die konkrete Modellwahl; die Rollenlogik dieses Abschnitts und die Trennung zur OCR-Stufe-3-Zuweisung bleiben unberührt. Keine stille Modellwechsel-Änderung.

**Prüf-Modell-Korrekturrecht:** Das Prüf-Modell hat kein allgemeines stilles Korrekturrecht. Es gelten vier Situationstypen:

1.  **Einigkeit:** Primär-Output wird übernommen.

2.  **Objektiv-deterministischer Befund:** Auto-Korrektur wird durchgesetzt; immer protokolliert und für den Nutzer einsehbar.

3.  **Substanziell-interpretative Abweichung:** keine stille Korrektur; Konfidenz sinkt; die Stelle wird für Review markiert.

4.  **Echte Ambiguität trotz Gegenprüfung:** Nutzerhinweis; keine stille Entscheidung.

**Kein stiller Rollentausch zwischen Primär- und Prüfpfad bei Ausfall:**

- Fällt der Primärpfad aus, übernimmt der Prüfpfad nicht still die Primärrolle; der Chunk wartet oder geht in einen Wartezustand mit Auto-Retry.

- Fällt der Prüfpfad aus, läuft der Primär-Output weiter; die betroffenen Stellen gelten als nicht gegengeprüft und werden entsprechend protokolliert.

**Audit-Befunde:** Inhaltliche Audit-Befunde (A-01 bis D-03) stoppen den Übersetzungsflow nicht. Sie werden als Befunde persistiert und in der Preflight-Logik (§4.6 / §4.7) weitergeführt.

**API-Ausfall-Verhalten:** Bei API-Ausfall: stille Hintergrundmarkierung der betroffenen Stelle, Dashboard-Statusindikator, automatisches Retry, manueller Retry-Button für den Nutzer verfügbar. Nach 30 Minuten ohne Wiederherstellung erfolgt aktive Nutzerinformation via In-App und E-Mail. Der Dashboard-Statusindikator bleibt unverändert bestehen.

**Chunk- und Kontextregeln:**

- Chunks enden nie mitten im Satz.

- Jeder Chunk enthält: Stil-Kern, Glossar-Einträge, Entitäten-Datenbank, semantische Zusammenfassung.

- Letzter Absatz des vorherigen Chunks dient als Kontext.

- RAG für Skalierbarkeit.

**Sonstiges:**

- Fortschrittsanzeige seitenweise.

- Benachrichtigungen erfolgen standardmässig via E-Mail und In-App. E-Mail ist durch den Nutzer deaktivierbar.

### **3.7 Benutzeroberfläche**

**Dashboard:** Meine Projekte, Bücher hochladen, Account-Einstellungen, Nutzungsstatistiken, API-Nutzungs-Statistik.

**Haupt-Editor:** Login → Dashboard → Projekt öffnen → Ansicht wählen \[Arabisch / Übersetzung / Vergleich\] → automatisch im Bearbeitungsmodus.

**Toolbar:** Ansicht-Tabs / Vorschau / Speichern / Export.

**Vergleichsansichten (5 Modi):**

1.  Originalbuch / OCR

2.  Originalbuch / Übersetzung

3.  OCR / Übersetzung (Standard)

4.  Dreier-Ansicht

5.  Einzelansicht Vollbild

**Dreier-Ansicht:** ziehbare Trennlinien 15–70 %, Doppelklick = 33/33/33 %.

**Synchronisierung:**

- Seitenweise zwischen Originalbuch und OCR.

- Satzweise zwischen OCR und Übersetzung (immer aktiv).

- Satz-ID im Format \[AR-047-003\].

- Klick auf Satz → alle Fenster springen auf diese Stelle.

**Vorschau-Modus (Option A):** Einstellungspanel und Live-Buchvorschau (Doppelseite, blätterbar). Einstellungen: Seitenformat, Typografie Deutsch und Arabisch, Zitat-Elemente, Kopf- und Fusszeile, IVZ, Fussnoten, Kapitelanfang.

**Layout-Profile:** unbegrenzt speicherbar, projektübergreifend.

## **4. FESTSTEHENDE LOGIK UND REGELN**

### **4.1 Harte Invarianten H-1 bis H-7**

Vollständige Definitionen in Core Architecture Baseline v1.0.

### **4.2 Governable Project Rules G-1 bis G-4**

Vollständige Definitionen in Core Architecture Baseline v1.0.

### **4.3 Kernobjekte und Identitäten**

Vollständige Definitionen in Core Architecture Baseline v1.0: Page-UUID, Block-UUID, Satz-UUID, Revisions-UUID, Decision-Event-UUID, Konzept-ID, Quellenattribute. Schutzmodell mit Sperrebene 1/2/3, Revisionsmodell, Promotion-Pipeline.

### **4.4 OCR-Fehlerklassen F-01 bis F-09**

Vollständige Definitionen mit Schweregradmatrix und Aggregationslogik in Core Architecture Baseline v1.0.

**OCR-Qualitäts-Klassifizierung:**

- ✅ **Akzeptiert:** Konfidenz ≥ 85 % und alle Validierungen bestätigt.

- 🟡 **Mangelhaft:** Konfidenz 60–84 % oder eine Bedingung nicht erfüllt.

- 🔴 **Kritisch:** Konfidenz \< 60 % oder Lesereihenfolge widersprechend oder \> 15 % Wörter unmöglich.

**OCR-Darstellung (maximal simpel):** Noto Sans Arabic, 14 pt. Überschriften nur fett und mit grösserem Abstand. Koranverse und Hadithe nur eingerückt mit Randstrich. Fussnoten 11 pt mit Trennlinie.

### **4.5 Freigabeschranken-Logik (Go/No-Go)**

Vollständige Definitionen in Core Architecture Baseline v1.0.

### **4.6 Übersetzungs-Audit A-01 bis D-03**

Die Audit-Kategorien A-01 bis D-03 sind in drei Klassen eingeteilt. Massgebliche Quelle für die vollständigen Kategorien-Definitionen und ihre Klassifikation ist die Implementation Translation Baseline v1.0. Der Abgleich ist erfolgt.

**Abgrenzung:**

- Koranvers- und Hadith-Behandlung sind eigenständige Stränge (§4.15 / §4.16) und nicht Teil dieses Audit-Strangs.

- Stilfeature-Logik ist strikt getrennt.

- Verstösse gegen Formatvorlagen, RTL-Encoding/RTL-Anwendung und Ziffernstandard sind kein Teil dieses Audit-Strangs – sie werden Guard-nah behandelt (§4.7).

**Bestätigte Prinzipien:**

- Kein Gesamtscore. Das Audit prüft pro Segment, ob konkrete definierte Regeln eingehalten oder verletzt wurden.

- Ein Verstoss hat eine Klasse, einen Schweregrad und eine Konsequenz.

- Das Audit läuft parallel zur Übersetzungsausgabe.

- Ignorieren eines Audit-Befunds wird immer protokolliert (audit_resolution decision_event, Entscheid = ignoriert).

**Drei Klassen:**

**Kritisch – blockierend** (Stelle blockiert bis aufgelöst, P-03):

- C-01: Terminologieeintrag verletzt – Terminologie-Verzeichnis oder Glossar (Verletzung G-2).

- D-03: Religiöse Formel nicht nach Verzeichnis (Verletzung G-3).

**Hoch – Pflichthinweis** (muss vor Export pro Stelle aktiv entschieden werden, P-04):

- A-01: <span dir="rtl">إِنَّ / أَن</span>َّ nicht übertragen.

- A-04: <span dir="rtl">أَمَّا...ف</span>َ-Konstruktion nicht vollständig übertragen.

- B-01: Idāfa zu frei aufgelöst.

- B-02: Dual nicht sichtbar.

- C-02: Islamischer Fachbegriff ohne Erstauftreten-Behandlung.

- C-03: Translatorische Ergänzung nicht markiert.

**Mittel – Hinweis** (Export mit Warnung möglich, W-01):

- A-02: <span dir="rtl">ل</span>َ (Betonung) nicht als Emphase übertragen.

- A-03: <span dir="rtl">ف</span>َ nicht kontextsensitiv übertragen.

- B-03: Genusunterschied nicht übertragen.

- B-04: Konditionalsatz nicht textnah.

- D-01: Metapher oder Redewendung nicht wörtlich mit Fussnote.

- D-02: Sajʿ ohne Hinweis in Fussnote.

**Konsequenzlogik:**

- **Kritisch:** Ignorieren nicht möglich – Blockade.

- **Hoch:** Ignorieren erfordert aktive Entscheidung pro Stelle – wird protokolliert.

- **Mittel:** Ignorieren löst go_with_warning beim Export aus – wird protokolliert.

### **4.7 Export-Preflight P-01 bis P-06 / W-01 bis W-08**

Vollständige Definitionen in Engineering Execution Baseline v1.0.

#### **4.7.1 Preflight-Schichtenmodell (kanonisch bestätigt)**

Der Preflight-Dialog enthält zwei konzeptionell eigenständige Schichten:

**Schicht 1 – Konfigurationspflichten:** Die 4 Pflichtfragen bilden eine eigenständige Konfigurationsschicht im Preflight-Dialog. Sie fordern notwendige Exportparameter und prüfen keinen Befund im Dokument. Sie belegen nicht automatisch P-01 bis P-06.

**Schicht 2 – Gate-Prüfungen:** Blockierende P-Gates (P-01 bis P-06) und warnungsbasierte W-Gates (W-01 bis W-08) prüfen Sachverhalte im Dokument oder Exportzustand gegen definierte Bedingungen.

#### **4.7.2 Pflichtfragen beim Export (Konfigurationsschicht)**

1.  Welche Überschriftenebene soll in der Kopfzeile angezeigt werden?

2.  Welche Überschriftenebene markiert Kapitelumbrüche?

3.  Position des IVZ (vorne / hinten)?

4.  Arabische Kapitelüberschriften im Text anzeigen (ja/nein)?

**PDF-Export:** Digital (RGB) oder Druck (PDF/X-1a, CMYK, 3 mm Beschnitt).

#### **4.7.3 Guard-nahe Behandlung vor Preflight (kanonisch bestätigt)**

- **Ziffernstandard-Verstösse:** Guard-nah; blockierend; kein Audit-Fall, kein Nutzerurteil – direkter Systemmechanismus. Prüfung vor Preflight-Dialog.

- **Kritische RTL-Encoding-/RTL-Anwendungsfehler:** Guard-nah; Integritätsverstoss; blockierend. Prüfung vor Preflight-Dialog.

- **Formatvorlagen-Integritätsverstösse:** Guard-nah; blockierend. Prüfung unmittelbar vor Öffnung des Preflight-Dialogs; liegt ein Verstoss vor, wird der Preflight-Dialog nicht geöffnet. Auflösung setzt technische Beseitigung des Verstosses voraus.

- **Kritische Schriftart-Verfügbarkeit:** Guard-nah; blockierend; Prüfung vor Preflight-Dialog. Fehlt eine der vier kritischen Schriftarten (KFGQPC Uthmanic Script HAFS, Traditional Naskh, Noto Sans Arabic, Calibri), wird der Preflight-Dialog nicht geöffnet. Auflösung setzt technische Wiederherstellung der Schriftart voraus; blosse Nutzerbestätigung genügt nicht. Kein P-Slot wird belegt.

- **Graduelle Formatvorlagen-Abweichungen:** warnungsbasiert; nicht blockierend. Erreichen den Preflight-Dialog. Belegen W-03.

#### **4.7.4 Belegte Gates (bestätigt)**

- **P-03:** eigenständiges blockierendes Gate in der Preflight-Gate-Prüfungsschicht, strukturell gleichrangig neben P-04.

- **P-04:** Hoch-Audit-Befunde – stärkste strukturelle Passung als blockierendes Preflight-Gate.

- **W-01:** Mittel-Audit-Befunde (A-02, A-03, B-03, B-04, D-01, D-02), belegt via §4.6.

- **W-02:** K-01 bis K-07 Konsistenzwarnungen – eigenständige Gruppe.

- **W-03:** Graduelle Formatvorlagen-Abweichungen – eigenständiger Slot.

#### **4.7.5 Eigene benannte Gruppe – Hadith-Verifikationsstatus**

Eigene benannte Gruppe innerhalb der Gate-Prüfungsschicht: **Hadith-Verifikationsstatus.** Die Gruppe ist keine neue Schicht und belegt keinen der offenen P- oder W-Slots. Sie trägt zwei Zustandsklassen gemäss §4.16:

- **H-2 blockierend:** Stelle nicht exportierbar, solange H-2 bleibt; Auflösung ausschliesslich über die in §4.16 kanonisierten Handlungstypen.

- **H-1 warnungsbasiert:** Stelle exportierbar mit go_with_warning-Bestätigung, konsistent mit §4.9 E-1 angewendet; decision_source preflight_confirmation gemäss §4.10.

Keine neuen decision_source-Werte. Keine Änderung der 7 kanonisierten Handlungstypen. H-0-Stellen erzeugen keinen Gruppen-Eintrag. Die Gate-Wirkung der Gruppe ist slot-unabhängig geführt; eine spätere formale Belegung offener P-/W-Slots bleibt möglich, ohne dass dieser Kanon still geändert wird.

#### **4.7.6 Noch offen**

- **P-01, P-02, P-05, P-06:** Im bestehenden Kanon des Publikationsexports derzeit keine sauberen Kandidaten identifizierbar. Slots bleiben vorerst offen.

- **W-04 bis W-08:** Im bestehenden Kanon des Publikationsexports derzeit keine weiteren sauberen Kandidaten identifizierbar. Slots bleiben offen. Keine Richtungsbindung vorweggenommen. Keine neuen warnungsbasierten Zustände eingeführt.

### **4.8 Werkweite Konsistenzprüfung K-01 bis K-07**

Vollständige Definitionen in Engineering Execution Baseline v1.0.

K-01 bis K-07 sind nicht export-blockierend. Sie erzeugen Warnungen. Ausnahme: Wenn ein K-Verstoss gleichzeitig eine Kritisch-Klasse im Sinne von §4.6 verletzt, gilt das Audit-Gate. Graduelle Formatvorlagen-Abweichungen fallen unter W-03 – warnungsbasiert, nicht blockierend.

### **4.9 OCR-Export-Endfassung v1.3 – Verbindliche Entscheidungen E-1 bis E-10**

| **Nr.** | **Entscheidung** |
|----|----|
| E-1 | go_with_warning erlaubt mit doppelter Warnung |
| E-2 | Zwei Modi: Arbeitsstand / freigegebener Stand |
| E-3 | Harte Konflikte blockieren; editorische Restunsicherheiten = Warnung |
| E-4 | Text exakt wie vorliegend – keine Harakat-Ergänzung |
| E-5 | Standard: MT + UE; optional: FN, QR, HD, RN |
| E-6 | Editorische Markierungen: Nutzerentscheidung |
| E-7 | DOCX ist Teil des Features |
| E-8 | Eigener PO-Typ: OCR_EXPORT_EVENT |
| E-9 | Eigene Funktion get_ocr_exports_for_segment() |
| E-10 | Strenge Versionierung: ocr_revision_snapshot\[\], active_decision_event_uuids\[\] |

**OCR-Export-DOCX – formal verbindliche Anforderungen:**

- Per-paragraph RTL.

- Echte DOCX-Fussnoten.

- Blocktypen-Struktur (MT/UE; optional FN/QR/HD/RN).

- Harakat exakt wie vorliegend.

- Editorische Markierungen als DOCX-Kommentare, wenn aktiviert.

- DOCX öffnet reparaturfrei in Word.

- Kein Option-B-Template, kein Buchlayout – einfaches Arbeitsdokument.

- Getrennt vom Stilfeature.

**Harte Konflikte (immer blockierend):**

- F-06-QR ohne Auflösung.

- F-07 kritisch.

- F-08 unentschieden.

- conflict_instance mit unklarem Textzustand.

- Inaktive Segmente ohne Lineage-Auflösung.

- Kritische RTL-Encoding-Probleme.

### **4.10 decision_source-Enum (10 Werte, überschneidungsfrei)**

| **Wert** | **Domäne** |
|----|----|
| ocr_review | OCR-Fehlerklassen-Auflösung |
| lock_management | Sperrflag-Setzen/Aufheben |
| conflict_resolution | Konflikt-Auflösung |
| glossary_management | Eintragsänderung in den Pflege-Verzeichnissen Glossar, Terminologie-Verzeichnis und Religiöse-Formeln-Verzeichnis. Abgrenzung: keine Anwendung auf Stilregel-Änderungen (style_management), keine Anwendung auf Konflikt-Auflösungen ohne Verzeichnisänderung (conflict_resolution), keine Anwendung auf Audit-Befund-Auflösungen (audit_resolution). |
| export_confirmation | Nur OCR-Export-Pflichtfragen |
| preflight_confirmation | Nur finaler Publikationsexport |
| translation_pipeline | Übersetzungsphase |
| audit_resolution | Audit-Befund-Auflösung |
| consistency_resolution | Konsistenz-Gruppen-Auflösung |
| style_management | Stilprofil-Entscheidungen |

### **4.11 Abfrageregel active_decision_event_uuids\[\] (deterministisch, v1.3)**

exported_segment_uuids =

SELECT satz_uuid FROM segments

WHERE current_rev_uuid IN ocr_revision_snapshot\[\]

AND active = true

exported_page_uuids =

SELECT page_uuid FROM pages

WHERE page_number IN export_config.page_range

AND project_uuid = current_project_uuid

AND active = true

current_export_confirmation_uuids =

SELECT decision_event_uuid FROM decision_events

WHERE decision_source = 'export_confirmation'

AND related_export_attempt_id = current_export_attempt_id

AND is_superseded = false

active_decision_event_uuids\[\] =

SELECT decision_event_uuid FROM decision_events

WHERE is_superseded = false

AND decision_source IN ('ocr_review', 'lock_management', 'conflict_resolution')

AND ((scope_type = 'segment' AND scope_uuid IN exported_segment_uuids)

OR (scope_type = 'page' AND scope_uuid IN exported_page_uuids))

UNION

current_export_confirmation_uuids

Diese OCR-Export-Abfrageregel ist snapshot-spezifisch und beschränkt sich bewusst auf segment- und page-scoped Decision Events sowie die Pflichtfragen-Bestätigungen des aktuellen OCR-Exportversuchs. Sie schränkt den allgemeinen scope_type-Enum nicht ein. Der allgemeine scope_type-Enum umfasst gemäss Core Architecture Baseline §B.1: segment, page, block, account, project.

### **4.12 Stilfeature – Vorranglogik, Konfliktfall-Matrix, Lernregel**

#### **4.12.1 Vorranglogik (unveränderlich)**

- **Rang 1 – Allgemeine Systemregeln (immer Vorrang):** Transliteration (EI2 Q/J), Glossar, Terminologie-Verzeichnis, Religiöse Formeln-Verzeichnis, Koranvers-Behandlung (quranenc.com), Hadith-Behandlung, Fachbegriff-Behandlung, alle sonstigen kanonischen Standards.

- **Rang 2 – Kanonischer Nutzerstil:** Dokument A (Nutzerstil-Korpus v1.0) und Dokument B v1.2 (Feature-Spezifikation).

- **Rang 3 – Einzelne Referenzsätze:** Nur als strukturierte zweisprachige Stilbelege – nie als stiller Ersatz für Systemregeln.

Ein Stilprofil-Vorschlag, der mit Rang 1 kollidiert, wird nicht ausgeführt. Stille Übersteuerung einer Rang-1-Systemregel durch das Stilfeature ist ausgeschlossen. Die einzige zulässige dauerhafte Abweichung von einem Verzeichniseintrag ist die Änderung oder Löschung des Verzeichniseintrags selbst.

Pro Konfliktstelle stehen dem Nutzer ausschliesslich die in der Konfliktfall-Matrix definierten Handlungstypen zur Verfügung. Die jeweilige Handlung wird über den passenden kanonischen decision_source-Wert gemäss §4.10 protokolliert. Keine Handlung führt einen neuen decision_source-Wert ein.

#### **4.12.2 Stilprofil-Sprachpaarbindung**

Das Stilfeature „Erkenne meinen Übersetzungsstil" ist accountgebunden und sprachpaarbezogen. Geltungsbereich eines Stilprofils ist genau ein (account_uuid, sprachpaar)-Paar.

- **Sprachpaar-Enum:** AR_DE, AR_EN, EN_DE, DE_EN.

- Stilprofile werden zwischen Accounts und zwischen Sprachpaaren desselben Accounts nicht übertragen.

- Kein Cross-Account-Transfer.

- Kein Cross-Sprachpaar-Transfer.

#### **4.12.3 Vorprägungslage**

- Für den Hauptnutzer/Admin ist im Sprachpaar AR_DE der kanonische Nutzerstil-Korpus (Dokument A v1.0) als Vorprägung gesetzt.

- In allen anderen (account_uuid, sprachpaar)-Paaren – einschliesslich AR_EN, EN_DE und DE_EN beim Hauptnutzer/Admin – beginnt das Stilprofil leer.

#### **4.12.4 Aktivierung pro Sprachpaar**

Das Stilfeature ist in einem (account_uuid, sprachpaar)-Paar erst aktivierbar, wenn der Account in diesem Sprachpaar genügend eigene bestätigte Übersetzungstexte erzeugt hat. „Bestätigt" bezeichnet vom Nutzer selbst erstellte oder ausdrücklich bestätigte Übersetzungstexte sowie bestätigte Referenzsätze; korrigierte KI-Vorschläge wirken gemäss §4.13 als Gegensignal und zählen nicht automatisch als positive Stilbelege.

Der konkrete Aktivierungsschwellenwert wird nach Gold-Corpus-Tests festgelegt (Kalibrierungswert gemäss §4.14). Vor Festlegung des Schwellenwerts bleibt M3 ausserhalb der vorgeprägten Hauptnutzer/Admin-AR_DE-Konstellation nicht aktivierbar.

#### **4.12.5 Übersetzungsmodi pro Stelle**

In der Übersetzungsansicht je Stelle wählbar:

- **M1:** leer / manuell selbst übersetzen.

- **M2:** KI-Übersetzung nach vordefinierter wortgetreuer Übersetzungslogik unter Beachtung der Rang-1-Systemregeln.

- **M3:** KI-Übersetzung nach persönlichem Stilprofil (Rang 2). M3 ist nur verfügbar, wenn für das aktive (account_uuid, sprachpaar)-Paar ein Stilprofil aktiv ist.

#### **4.12.6 Konfliktfall-Matrix Stilfeature**

| **ID** | **Situation** | **Systemreaktion** | **Nutzeroptionen** | **decision_source** |
|----|----|----|----|----|
| K-S1 | Stilprofil-Vorschlag ≠ Glossareintrag | Stilprofil-Vorschlag unterdrückt; Glossarwert gesetzt; Konfliktindikator an der Stelle | a\) Glossareintrag ändern · b) Einzelstelle manuell überschreiben · c) Stilregel auf nur_kontextuell_zulässig oder deaktiviert setzen | a\) glossary_management · b) translation_pipeline · c) style_management |
| K-S2 | Stilprofil-Vorschlag ≠ Terminologie-Verzeichnis-Eintrag | Stilprofil-Vorschlag unterdrückt; Terminologiewert gesetzt; Konfliktindikator an der Stelle | a\) Terminologie-Verzeichnis-Eintrag ändern · b) Einzelstelle manuell überschreiben · c) Stilregel auf nur_kontextuell_zulässig oder deaktiviert setzen | a\) glossary_management · b) translation_pipeline · c) style_management |
| K-S3 | Stilprofil-Vorschlag ≠ Religiöse-Formeln-Verzeichnis-Eintrag | Stilprofil-Vorschlag unterdrückt; Verzeichniswert gesetzt; Konfliktindikator an der Stelle | a\) Religiöse-Formeln-Verzeichnis-Eintrag ändern · b) Einzelstelle manuell überschreiben · c) Stilregel auf nur_kontextuell_zulässig oder deaktiviert setzen | a\) glossary_management · b) translation_pipeline · c) style_management |
| K-S4 | Stelle ist akzeptierte Qurʾān-/Hadith-Stelle gemäss §4.15 / §4.16 | Stelle geschützt; Stilregel wirkt nicht; kein Konfliktdialog; keine Lernwirkung; keine Protokollierung als Stilregel-Verletzung | keine | kein decision_event auf Stilfeature-Seite |
| K-S5 | Stilprofil-Vorschlag berührt Fachbegriff-Erstauftreten gemäss §4.17 | Erstauftreten-Regel erzwungen; Stilprofil-Vorschlag im Erstauftreten unterdrückt; ab Zweitauftreten desselben Fachbegriffs wirkt das Stilprofil normal | a\) Erstauftreten korrekt bilden · b) Stilregel kontextuell auf „nicht beim Erstauftreten" einschränken · c) Einzelstelle manuell | a\) audit_resolution (C-02) · b) style_management · c) translation_pipeline |
| K-S6 | Referenzsatz steht im Widerspruch zu späterer manueller Nutzerregel | Manuelle Regel hat Vorrang vor Referenzsatz gemäss §4.13; Referenzsatz wirkt nicht als stiller Ersatz | a\) manuelle Regel beibehalten oder hochstufen · b) Referenzsatz aus Korpus entfernen · c) Referenzsatz nur_kontextuell_zulässig markieren | style_management |
| K-S7 | Akzeptierter KI-Vorschlag wird später vom Nutzer korrigiert | Korrektur überschreibt die Stelle; Korrektur wirkt auf Lernebene ausschliesslich als Gegensignal gemäss §4.13; Korrektur wird nie selbst zur Regel | a\) Korrektur stehen lassen (Gegensignal automatisch) · b) zusätzlich manuelle Stilregel anlegen | a\) translation_pipeline · b) style_management |
| K-S8 | Einzelstellen-Abweichung ohne Regeländerungswunsch | Stelle manuell überschrieben; Glossar, Verzeichnisse und Stilregeln unverändert; kein Lernsignal über das normale §4.13-Mass hinaus; kein automatischer Aufstieg zur Regel | a\) manuelle Übersetzung an dieser Stelle | translation_pipeline |
| K-S9 | Aus einer Einzelabweichung soll eine dauerhafte Regel werden | Expliziter Nutzerschritt; zwei Pfade | a\) Verzeichniseintrag erzeugen (Glossar / Terminologie / Religiöse Formeln) · b) Stilregel anlegen oder hochstufen | a\) glossary_management · b) style_management |

#### **4.12.7 Schutzklauseln zur Konfliktfall-Matrix**

- K-S4 (geschützte Stellen) erzeugt keinen Konfliktdialog, keine Lernwirkung und keine Protokollierung als Stilregel-Verletzung.

- K-S6 und K-S7 verändern das Stilprofil ausschliesslich über die Hochstufungsregeln gemäss §5.6 und die Lernquellen-Asymmetrie gemäss §4.13.

- K-S8 ist niemals automatisch eine neue Stilregel; aus K-S8 wird nur dann eine Regel, wenn der Nutzer ausdrücklich K-S9 wählt.

- Verzeichnisse (Glossar, Terminologie, Religiöse Formeln) werden niemals durch das Stilfeature verändert. Verzeichnisänderungen erfolgen ausschliesslich über den Verzeichnis-Pflegepfad und werden in allen drei Verzeichnissen über decision_source = glossary_management protokolliert. Stilfeature-Logik führt keine Verzeichnisänderung durch.

#### **4.12.8 Stilfeature-Lernregel**

**Es wird gelernt:**

- bei expliziter Nutzerhandlung (manuelle Stilregel anlegen, Hochstufung, bestätigter Referenzsatz, Verzeichnisänderung);

- als schwache Verstärkung bestehender Regeln durch akzeptierte KI-Vorschläge ohne Aufstieg zur Invariante;

- als Gegensignal durch Korrekturen akzeptierter KI-Vorschläge, ohne dass die Korrektur selbst zur Regel wird.

**Es wird nicht gelernt:**

- aus geschützten Stellen gemäss K-S4;

- aus Einzelstellen-Abweichungen gemäss K-S8 ohne ausdrückliche K-S9-Handlung;

- aus ignorierten KI-Vorschlägen (Null-Signal);

- aus Konflikten gegen Rang-1-Systemregeln, weder in Richtung des unterdrückten Stilvorschlags noch als Stilsignal in Richtung des Verzeichniswerts.

Ohne explizite Nutzerhandlung gibt es keinen Pfad zu invariant.

### **4.13 Lernquellen-Asymmetrie Stilfeature (KANON)**

| **Quelle** | **Starke Regeln** | **Invarianten** | **Verstärken** | **Kandidaten** | **Nichtnützung** |
|----|----|----|----|----|----|
| Bestätigte Referenzsätze | Ja | Nein (nur via Bestätigung) | Ja | Ja | – |
| Manuelle Nutzerregeln | Ja | Ja – direkt | Ja | Ja | – |
| Akzeptierte KI-Vorschläge | Nein | Nein | Ja (bestehend) | Ja (schwach) | – |
| Korrigierte KI-Vorschläge | Nein | Nein | Nein | Nein | Gegensignal |
| Ignorierte KI-Vorschläge | Nein | Nein | Nein | Nein | Null-Signal |

**Schutzklausel:** Die Matrix definiert die qualitativen Wirkrichtungen pro Lernquelle. Konkrete Lerngewichte, Belegdichte-Schwellen und Hochstufungs-Schwellen sind ausdrücklich nicht Teil dieser Matrix und werden ausschliesslich nach Gold-Corpus-Tests als Kalibrierungswerte gemäss §4.14 festgelegt.

**Signalklassen:**

- **stark:** manuelle Nutzerregel oder bestätigter Referenzsatz – können selbst Regel sein.

- **schwach:** akzeptierter KI-Vorschlag – verstärkt bestehende Regeln, Kandidat.

- **Gegensignal:** korrigierter KI-Vorschlag – wirkt ausschliesslich gegen die ursprüngliche Vorschlagsrichtung, wird nie selbst Regel.

- **Null:** ignorierter KI-Vorschlag.

Akzeptierte KI-Vorschläge erzeugen niemals automatisch eine Invariante oder eine starke Regel. Korrigierte KI-Vorschläge wirken ausschliesslich als Gegensignal. Ignorierte KI-Vorschläge sind Null-Signal. Eine Hochstufung über präferenz hinaus zu invariant und eine Rückstufung von invariant erfordern eine ausdrückliche Nutzerhandlung gemäss §5.6. Es gibt keinen automatischen Pfad zu Invarianten aus Lernquellen.

### **4.14 Zustandsmodell Stilregeln**

| **Status**                    | **Bedeutung**              |
|-------------------------------|----------------------------|
| aktiv                         | Regel aktiv und angewendet |
| in_prüfung                    | Kandidat – keine Anwendung |
| unterdrückt_durch_systemregel | Systemregel hat Vorrang    |
| nur_kontextuell_zulässig      | Nicht in allen Kontexten   |
| deaktiviert                   | Temporär deaktiviert       |
| vom_nutzer_gesperrt           | Dauerhaft gesperrt         |

**Stilprofil-Marker:** Stilbeeinflusste Stellen im Editor werden durch dezente Unterstreichung (Blauton) und Hover-Tooltip mit Regelbezeichnung (PF-XX) kenntlich gemacht. Deaktivierbar in den Anzeigeeinstellungen.

**Anzeigeeinstellung Stilmarker:** account-level gespeichert.

**Stilprofil-Rollback:** Standardmässig aktiv für alle Nutzer mit freigeschaltetem Stilfeature. Rückkehr zu früherer stilprofil_version möglich; bereits abgeschlossene Seiten werden dabei nicht verändert.

**Kalibrierungswerte Stilfeature:** werden nach Gold-Corpus-Tests festgelegt.

### **4.15 Koranvers-Behandlung (kanonisch)**

#### **4.15.1 Trägerstruktur**

Nach akzeptierter Qurʾān-Erkennung gilt eine getrennte Trägerstruktur:

- **Arabischer Referenztext und Vokalisierung:** Arabischer Qurʾān-Referenzbestand (AR-Referenzbestand). Eigenständiger lokaler Bestand. Zielsprachenunabhängig. Zu keinem Zeitpunkt API-gestützt; kein API-Primärpfad und kein Fallback-Status. Konkrete Quellenbenennung und Update-Mechanismus noch offen.

- **Deutsche Übersetzung:** primärer Träger ist quranenc.com API (german_rwwad). Fallback bei API-Ausfall ist die lokale Kopie der german_rwwad-Übersetzung. Wöchentlicher automatischer Abgleich auf Updates.

- **Englische Übersetzung:** primärer Träger ist quranenc.com API (english_rwwad). Fallback bei API-Ausfall ist die lokale Kopie der gewählten englischen Übersetzung. Wöchentlicher automatischer Abgleich, analog zur deutschen Übersetzung.

Die kanonisch genannten APIs (quranenc.com DE und EN) sowie deren lokale Fallback-Kopien betreffen ausschliesslich die Übersetzungsträger, nicht den AR-Referenzbestand.

Eine Abweichung zwischen OCR-Vokalisierung und dem AR-Referenzbestand erzeugt keinen freien Wahlfall. Prüfbedürftig ist ausschliesslich die vorgelagerte Erkennungsfrage: Ist die Stelle mit ausreichender Sicherheit als Qurʾān-Stelle erkannt?

#### **4.15.2 Erkennung, Konfidenz und API-Zeitpunkt**

- Der erste externe API-Ruf (quranenc.com) erfolgt erst in der Übersetzungsphase. Während des OCR-Laufs wird nur lokal gematcht; kein externer Ruf in der OCR-Phase.

- Bei Konfidenz der Qurʾān-Erkennung unter dem definierten Schwellenwert: manuelle Bestätigung durch den Nutzer ist vorgelagert; kein automatischer API-Ruf. Schwellenwert noch offen.

- Erkannter Fehler bei Koranversen: Warn-Icon inline, persistiert bis zur Korrektur durch den Nutzer.

#### **4.15.3 Schutz bestehender Projektstellen**

Bereits in Projekten gespeicherte Qurʾān-Stellen bleiben bei Änderung des arabischen Qurʾān-Referenzbestands oder der lokalen Fallback-Kopie der Übersetzung unverändert. Kein automatischer Re-Abruf, kein stilles Überschreiben bestehender Projektstellen.

#### **4.15.4 Quellenangabe**

- Reihenfolge im Text: Arabisch → Deutsche Übersetzung → Quellenangabe.

- Koranvers-Quellenangabe wird über das Kontextmenü am Block aufgerufen.

- Fallback auf lokale Quran-Kopie: Log-Eintrag im Projekt-Protokoll.

**Quellenangabe-Logik:**

1.  System erkennt Qurʾān-Vers.

2.  Hat Autor Quellenangabe gemacht?

    - **Ja:** System verifiziert. Korrekt → übernehmen. Falsch → Nutzer informieren.

    - **Nein:** Stelle bleibt leer.

3.  In beiden Fällen: Nutzer bekommt Option, kanonische Quellenangabe einzufügen.

#### **4.15.5 Qurʾān-Stellenbehandlung – decision_source-Zuordnung**

| **Handlung** | **decision_source** |
|----|----|
| Manuelle Bestätigung bei Konfidenz unter Schwellenwert | translation_pipeline |
| Korrektur der Sure/Āya-Zuordnung | conflict_resolution |
| Ablehnung als Qurʾān-Stelle („nicht als Qurʾān behandeln") | conflict_resolution |
| Ausdrückliche Nutzeraktion zur Aktualisierung einer bereits gespeicherten Qurʾān-Stelle nach Update des AR-Referenzbestands oder der lokalen Fallback-Kopie der Übersetzung | translation_pipeline |

Automatische Akzeptanz bei Konfidenz über Schwellenwert erzeugt kein decision_event. Keine neuen decision_source-Werte. Die Matrix ist strukturell analog zur Hadith-Handlungstypen-Matrix in §4.16.

### **4.16 Hadith-Behandlung**

#### **4.16.1 Verifikationsquellen (zweistufig)**

**Pflichtmenge** (wird bei jedem Hadith-Verifikationslauf vollständig durchsucht):

- P-1: sunnah.com (API)

- P-2: Shamela (lokal)

- P-3: dorar.net (= <span dir="rtl">الدُّرَرُ السَّنِيَّة</span>)

**Erweiterte Menge** (wird automatisch zugeschaltet, wenn die Pflichtmenge keinen belastbaren Treffer liefert; vom Nutzer jederzeit auch manuell auslösbar):

- E-1: islamweb.net – dokumentiert, faktisch suspendiert.

- E-2: <span dir="rtl">جَامِعُ السُّنَّةِ النَّبَوِيَّة</span> – hoch belastbar identifiziert als Alifta-/Harf-Variante; dokumentiert, faktisch suspendiert.

- E-3: <span dir="rtl">المكتبة الوقفية</span> – dokumentiert, faktisch suspendiert; nur noch als mögliche manuelle Referenzquelle geführt.

- E-4: <span dir="rtl">جَامِعُ الكُتُبِ التِّسْعَة</span> – dokumentiert, faktisch suspendiert.

- E-5: <span dir="rtl">مَوْسُوعَةُ الأَحَادِيثِ النَّبَوِيَّة</span> – nicht suspendiert, in Sonderrolle geführt (siehe §4.16.2).

**Ausdrücklicher Ausschluss:** hadithportal.com ist als Quelle für die Hadith-Verifikation ausgeschlossen.

**Hinweis:** Die zweistufige Quellenstruktur (Pflicht/erweitert) ist eine bewusste Schärfung aus der Hadith-Integration. <span dir="rtl">المكتبة الوقفية</span> erscheint in der erweiterten Menge als Eskalationsquelle, nicht in der Pflichtmenge.

#### **4.16.2 Sonderrolle E-5**

E-5 wird als „deutsche Übersetzungsquelle / mehrsprachige Referenzquelle" geführt und nicht als breite Korpus-Ersatzquelle.

- Kein API-Volltextsuchpfad.

- Technischer Anschluss über die offizielle API und die offiziellen Bulk-Downloads.

- **Offizielle Live-API:** primärer Laufzeitpfad.

- **Offizielle Bulk-Downloads:** sekundärer Hilfs- und Analysepfad, nicht Laufzeitquelle für die Hadith-Verifikation.

- Kein Offline-Index als Normalpfad.

- Kein Frontend-Scraping als Normalmodell.

**Auswirkung auf die Eskalationslogik:** Solange E-1, E-2, E-3 und E-4 faktisch suspendiert sind, wird bei automatischer Zuschaltung der erweiterten Menge faktisch ausschliesslich E-5 in der beschriebenen Sonderrolle wirksam. Die zweistufige Struktur Pflicht/erweitert bleibt strukturell erhalten. Die Bewertung der Treffer aus der erweiterten Menge folgt derselben Konsens- und Vergleichslogik wie bei der Pflichtmenge.

#### **4.16.3 Konsenslogik**

Die Hadith-Verifikation arbeitet mit einer mehrdimensionalen Vergleichs- und Konsenslogik über alle aktiven Quellen. Verglichen wird nach:

- Wortlautnähe

- Trägerschaft durch mehrere Quellen

- Nähe zur vom Autor genannten Quelle

- Isnād-/Sammlungsbezug

- Vokalisierungskonsistenz

- Authentizitätssignalen

Das lineare Konfidenz-Ranking (§3.5) greift als Tie-Breaker, wenn die Konsenslogik keinen klaren Sieger ergibt.

**Kutub as-Sitta:** starker Gewichtungsfaktor bei Konflikten, kein absoluter Vorrang. Bei gleichwertigen Treffern werden Kutub-as-Sitta-Quellen bevorzugt. Ein wortlautnäherer, belastbarer Treffer ausserhalb der Kutub as-Sitta kann den Vorrang brechen; die Abweichung wird im Review sichtbar gemacht.

**Authentizitätsgrad:** optional anzeigbar.

**Quellenangabe-Format:**

- **Deutsch:** (Sahih al-Bukhari, Nr. 1; Sahih Muslim, Nr. 1907)

- **Englisch:** (Sahih al-Bukhari 1; Sahih Muslim 1907)

#### **4.16.4 Hadith-Verifikationsstatus**

Jede Hadith-Stelle erhält nach Abschluss der Mehrquellen-Verifikation und nach jeder nachfolgenden Nutzerinteraktion einen Zustandstyp und eine daraus abgeleitete Verifikationsklasse.

**Stellentypen:**

- **N-1:** vollständig verifiziert und automatisch akzeptiert.

- **N-2:** verifiziert mit protokollpflichtigem Restbefund (V-1-Vokalisierungsrest, einzelner Pflichtquellen-Ausfall bei belastbarem Konsens, fehlendes Kutub-as-Sitta-Signal bei belastbarem Konsens ausserhalb).

- **N-3:** verifiziert mit aktiver Nutzerentscheidung.

- **N-4:** unaufgelöst, vom Nutzer aktiv „für spätere Klärung markiert".

- **N-5:** Gesamt-Verifikationsausfall ohne Nutzerentscheidung.

- **N-6:** Autor-Quellenkonflikt unaufgelöst.

- **N-7:** kein Treffer, kein Entscheid.

- **N-8:** V-2-Vokalisierungskonflikt unaufgelöst.

- **N-9:** „nicht als Hadith" behandelt.

- **N-10:** „ohne Verifikation fortfahren" explizit gewählt.

**Verifikationsklassen:**

- **H-0** (review-intern tolerierbar, nicht export-blockierend): N-1, N-3, N-9.

- **H-1** (protokollpflichtig, nicht export-blockierend, warnungsfähig): N-2, N-10.

- **H-2** (export-blockierend bis Auflösung): N-4, N-5, N-6, N-7, N-8.

Auflösung von H-2 ausschliesslich über die in §4.16.5 kanonisierten 7 Handlungstypen. Keine neuen decision_source-Werte. Markierung „für spätere Klärung" ist kein decision_event und hebt H-2 nicht auf.

**Verortung im Export-Preflight:** eigene benannte Gruppe „Hadith-Verifikationsstatus" innerhalb der Gate-Prüfungsschicht gemäss §4.7. Der Hadith-Verifikationsstatus ist kein Audit-Fall im Sinne von §4.6.

#### **4.16.5 Hadith-spezifische decision_event-Zuordnung**

| **Handlungstyp**                                    | **decision_source**  |
|-----------------------------------------------------|----------------------|
| Verifizierte Fassung statt Autorwortlaut übernehmen | translation_pipeline |
| Volltext statt Kurzfassung wählen                   | translation_pipeline |
| Autorwortlaut trotz Konflikt beibehalten            | conflict_resolution  |
| Quellenangabe ändern oder bewusst nicht ändern      | conflict_resolution  |
| Ohne belastbare externe Verifikation fortfahren     | conflict_resolution  |
| Stelle nicht als Hadith behandeln                   | conflict_resolution  |
| Vokalisierungskonflikt manuell entscheiden          | conflict_resolution  |

#### **4.16.6 Datenmodell Mehrquellen-Ergebnisobjekte**

Hadith-Ergebnisse werden in vier logischen Ebenen geführt:

- **Ebene 1 – Stellenanker:** über Block-UUID, Satz-UUID und OCR-Revisions-UUID.

- **Ebene 2 – Einzelquellen-Lesung:** pro Quelle und Verifikationslauf; mehrere Einzelquellen-Objekte derselben Quelle im selben Lauf sind zulässig (Treffer-Varianten).

- **Ebene 3 – Aggregiertes Gesamtergebnis:** pro Verifikationslauf, referenziert die Einzelquellen-Objekte und bestimmt Referenz-Matn sowie Referenz-Vokalisierung.

- **Ebene 4 – Nutzerentscheidungs-Overlay:** ausschliesslich über decision_event_uuid gemäss §4.10 und §4.11; keine eigene Superseding-Logik im Ergebnisobjekt.

**Quellenrolle (Pflicht-Snapshot-Feld):** Werte pflicht, erweitert_aktiv, erweitert_sonderrolle, erweitert_suspendiert. Der Wert wird zum Zeitpunkt des Verifikationslaufs festgeschrieben; keine dynamische Rückableitung gegen den jeweils aktuellen Kanon. hadithportal.com darf im Quellen-Enum nicht geführt werden (Ausschluss kanonisch). E-5 trägt den Rollenwert erweitert_sonderrolle.

**Abgeleitete Zustände** (nicht eigenständig persistiert, deterministisch aus Ebene 2/3/4 ableitbar):

- entscheidungsstatus

- vokalisierungsklasse (V-0 / V-1 / V-2)

- hadith_stellen_typ (N-1 bis N-10)

- hadith_verifikationsklasse (H-0 / H-1 / H-2)

**Rückfallregel:** bei Unklarheit wird die höhere Klasse oder der risikoreichere Zustand angewendet.

**Unveränderlichkeit analog §4.9 E-10:** Einzelquellen-Objekte und das Gesamtergebnis sind nach Anlage unveränderlich in Bezug auf Provenienz und Einzelquellen-Referenzen. decision_event_uuids wachsen ausschliesslich durch neue decision_events (Superseding gemäss §4.11). Eine neue Verifikationsrunde erzeugt ein neues Gesamtergebnis mit eigener UUID; das alte bleibt als Provenienz erhalten (is_aktiv = false). Keine neuen Kernobjekte. Keine neuen decision_source-Werte.

#### **4.16.7 Hadith-Vokalisierung**

**Trägerprinzip:** Referenz-Matn und Referenz-Vokalisierung werden als getrennt bestimmbare Felder geführt. Im Normalfall stammen beide aus derselben Quelle. Wenn eine andere Quelle die Vokalisierung besser liefert, kann die Vokalisierungsquelle separat bestimmt und protokolliert werden. Anders als bei Qurʾān (§4.15) gibt es bei Hadith bewusst keinen alleinigen Textträger. Bei relevanten Vokalisierungskonflikten wird der Nutzer einbezogen; die Entscheidung wird als decision_event unter conflict_resolution protokolliert.

**Vokalisierungs-Eskalationskriterium:** Abweichungen zwischen Vokalisierungsfassungen werden einer von drei Relevanzklassen zugeordnet.

- **V-0 (automatisch tolerierbar):** orthographisch-technische Varianten ohne Laut- oder Bedeutungsänderung (Tatweel, Unicode-Normalisierung, reine Rendering-Varianten, überlappungsfreie Teilvokalisierung in Sonderlage). Automatische Übernahme. Keine Protokollpflicht auf Stellenebene.

- **V-1 (protokollpflichtig, keine Eskalation):** Abweichungen ohne Bedeutungsänderung, die für die Nachvollziehbarkeit sichtbar bleiben müssen (Vokalisierungsdichte-Unterschiede, Shadda ohne Wortidentitätsänderung, Hamzat al-Waṣl/Qaṭʿ ohne Bedeutungsänderung, Namensvokalisierungsvarianten mit klassisch zulässiger Doppelform). Automatische Wahl der Referenz-Vokalisierung aus der besten Quelle. Dokumentation im Stellen-Logging. Kein aktiver Nutzereingriff. Kein decision_event bei Inaktion.

- **V-2 (eskalationspflichtig):** Abweichungen mit Bedeutungs-, iʿrāb-, sarf-, Isnād-Identifikations- oder Matn-Lexem-Veränderung (Kasus-/Modus-Abweichung, Aktiv/Passiv- oder Stammwechsel, Shadda mit Wortidentitätsänderung, Hamza mit Bedeutungsänderung, Namens-/Nisba-Vokalisierung mit Identifikationsfolge, Matn-Lexem-Abweichung über Vokalisierung). Keine automatische Übernahme. Aktive Nutzerauflösung gemäss den kanonisierten Handlungstypen. decision_source conflict_resolution.

**Aggregationsregel:** Bei mehreren Abweichungen in einer Stelle gilt die höchste auftretende Klasse für die Stelle (V-0 \< V-1 \< V-2). **Rückfallregel:** bei Unklarheit der Typ-Zuordnung wird die höhere Klasse angewendet; keine stille Abstufung.

Das Feld vokalisierungs_konflikt bleibt strikt binär (nein / ja). Die Klassen-Differenzierung läuft ausschliesslich über die abgeleitete vokalisierungsklasse. Ist die Typ-Zuordnung im Einzelfall unklar, bleibt vokalisierungs_konflikt auf ja; die Unklarheit wird nur im Logging bzw. in der Konfliktbegründung dokumentiert.

#### **4.16.8 Sprachneutrales Referenz- und Vergleichsfeld**

Website-Übersetzungen aus Hadith-Verifikationsquellen werden im Einzelquellen-Ergebnisobjekt als Teil des Feldes website_uebersetzung geführt (siehe §5.1.1). Wenn eine Quelle eine englischsprachige Übersetzung zum getroffenen Hadith liefert, wird diese mit lang = "en" in website_uebersetzung eingetragen.

- Diese Einträge entstehen unabhängig von der Zielsprache des Projekts und unabhängig davon, ob Englisch eine Ausgabesprache im betreffenden Projekt ist.

- Die Einträge wirken ausschliesslich als Provenienz- und Vergleichsmaterial.

- Sie haben keinen Einfluss auf Matn-Konsens, Referenz-Matn, Referenz-Vokalisierung oder auf die primäre Übersetzungsausgabe.

- Sie dürfen im Hadith-Review-Panel als Vergleichssprache sichtbar gemacht werden, auch in Projekten mit anderer Zielsprache; die Anzeige ist nicht verpflichtend und erzeugt keinen eigenen decision_event.

**Englische Hadith-Ausgabe:** ist ein eigener Primärproduktionspfad aus dem arabischen Matn, parallel und strukturell gleichwertig zur deutschen Hadith-Ausgabe. Sie wird nicht aus der deutschen Primärübersetzung abgeleitet. Eine Kaskade AR→DE→EN für die Hadith-Matn-Übersetzung ist ausgeschlossen (Keine-Kaskade-Regel).

Die englische Hadith-Ausgabe folgt für Fussnoten derselben strukturellen Fussnotenlogik und demselben Vorlagen- und Kategoriensatz wie die deutsche Ausgabe; konkrete englische Marker-Abkürzungen werden hier nicht festgezogen. Quellenangabe-Format und Transliteration bleiben sprachspezifisch geregelt (§4.16.3 für Quellenangabe-Format DE/EN; §2.2 für Transliteration). Verhältnis zum Stilfeature und zu Schnittstelle 3 bleibt ausdrücklich offen.

### **4.17 Besondere Behandlungen**

**Haraktisierung:** Originalgetreu übernehmen. Intern immer vokalisiert. Optionale Anzeige: KI-vokalisiert in Farbe A, manuell korrigiert in Farbe B. Drei Unsicherheitsstufen:

- Hoch (\> 85 %): still.

- Mittel (50–85 %): Tooltip.

- Niedrig (\< 50 %): vollständiges Panel.

**Fachbegriffe:**

- Erstes Auftreten: deutsche Fachübersetzung + (arabisch vokalisiert) + Fussnote.

- Ab zweitem Auftreten: nur Transliteration.

- Wenn kein Treffer: KI-generierte Fussnote mit \[Quelle: KI\]-Marker.

**Arabische Metaphern:** vollständige Erkennung. Behandlung: wörtlich + Fussnote \[Ü.\].

**Sajʿ:** Fussnote „Im arabischen Original als Sajʿ formuliert". Kashida standardmässig aktiviert.

**Religiöse Formeln:** als Kalligraphie/Unicode: <span dir="rtl">ﷺ, ﷻ</span>. Optionalität: Kalligraphie / deutsche Übersetzung / arabisch ausgeschrieben.

**Morphologie-Panel:** Bei Klick auf arabisches Wort werden angezeigt: Wortart, Wurzel, Wazn, Konjugationstabelle, Nominalisierungen, Iʿrāb, Übersetzungsvorschläge. Anzeigeort: Seitenpanel.

**Wortformen-Häufigkeitsanalyse:** Bei Wortkorrektur werden alle Formen mit Häufigkeit angezeigt. Pro Form: eigenes Übersetzungsfeld und Entscheidung. Anzeigeort: Modal-Dialog.

### **4.18 Fehlerklassifikations-System**

#### **4.18.1 Spur 1 – Fehlerbehebung**

- **Klasse A (Nutzerfehler/Datenfehler):** Nutzer informieren, dokumentieren.

- **Klasse B (Externer Fehler):** Retry, Fallback. (Generallogik siehe §4.18.2.)

- **Klasse C (Systembehebbar):** voller Prozess bis Code-Update.

#### **4.18.2 Generallogik Klasse-B-Benachrichtigung (L-24)**

- Klasse-B-Fehler werden immer protokolliert.

- Aktive Nutzerinformation erfolgt nicht pro Einzelfall, sondern aggregiert über den Dashboard-Statusindikator bei Erreichen einer Häufungsschwelle gemäss Spur 2.

- Bereits kanonisierte Spezialfälle mit eigener Regel bleiben unberührt: §3.6 Übersetzungs-KI 30-Min-Regel mit In-App und E-Mail; §4.15 Qurʾān-Fallback mit Log-Eintrag ohne Nutzer-Interrupt; Guard-nahe Blockaden gemäss §4.7.

- Konkrete Häufungsschwellenwerte sind live-messungsabhängig und bleiben bis zur realen Messung Werkbank; der strukturelle Mechanismus ist kanonisch.

#### **4.18.3 Spur 2 – Prozessoptimierung**

**Auslöser:** Häufungsmuster → periodische Auswertung → Optimierungsvorschlag → Bestätigung → Implementierung.

**Admin-Optimierungs-Eingabekanal:**

- Zusätzlich zur automatischen Häufungsmuster-Erkennung steht dem Hauptnutzer/Admin ein internes Optimierungs-Eingabefenster zur Verfügung. Über diesen Kanal kann der Hauptnutzer/Admin manuell Beobachtungen, Prozessprobleme, Fehlerhinweise, UI-/Ablaufbemerkungen, Optimierungsvorschläge oder gewünschte Verbesserungen einspeisen. Beispiele sind etwa: Position eines Morphologie-Fensters, Anordnung eines Buttons, gewünschte Formatvorlage im Export, wiederkehrende Bedienprobleme, erkannte Prozessfehler oder technische Auffälligkeiten.

- **Sichtbarkeit und Berechtigung:** Der Eingabekanal ist ausschliesslich für den Hauptnutzer/Admin sichtbar. Normale Nutzer (Stufen 1 und 2 gemäss §2.3) haben keinen Zugriff.

- **Verarbeitung:** Admin-Eingaben werden in denselben Spur-2-Fluss eingespeist wie automatisch erkannte Häufungsmuster. Beide Eingangsquellen (\`system\` und \`admin\`) durchlaufen identisch die Schritte Erfassen → Klassifizieren → Verknüpfen mit Fehler-/Prozessdaten → Aufbereiten als Optimierungsvorschlag → Vorschlagsstand. Es gibt keinen Admin-Sonderweg und keine Admin-Bypass-Möglichkeit.

- **Wirkungsschranke:** Eine Admin-Eingabe ist Input in den Optimierungsprozess, keine Entscheidung. Sie löst keine automatische Architektur-, Kanon- oder Code-Änderung aus. Der weitere Pfad zu Analyse, CR, Ticket, Sprint und Umsetzung erfolgt ausschliesslich über das statusbasierte Admin-Optimierungs-Panel gemäss §4.18.

**Admin-Optimierungs-Panel:**

Das Admin-Optimierungs-Panel führt alle Optimierungseinträge aus den Quellen \`system\` und \`admin\` in einer statusbasierten Oberfläche. Die Darstellung erfolgt in Registern. Ein Eintrag befindet sich immer in genau einem Hauptregister.

Register:

1\. Eingang / Vorschläge: neue automatisch erzeugte oder manuell eingegebene Optimierungseinträge, die noch nicht eingeordnet wurden.

2\. Weiter beobachten: Einträge, die noch nicht entscheidungsreif sind und weiter gesammelt, verdichtet oder mit künftigen Fehler-/Prozessdaten abgeglichen werden.

3\. Zur Analyse freigegeben: Einträge, die zur fachlichen oder technischen Analyse freigegeben wurden. Nach Abschluss der Analyse erhalten sie einen Analysebefund.

4\. Als CR vorbereiten: Einträge, deren Analyse ergeben hat, dass eine kanonische, architektonische oder prozessuale Änderung wahrscheinlich erforderlich ist und als Change Request vorbereitet werden soll.

5\. Tickets: Einträge, die fachlich entschieden sind und als Entwickleraufgabe vorgemerkt oder in eine spätere Umsetzungsplanung überführt werden können.

6\. Archiviert / verworfen: Einträge, die ignoriert, erledigt, verworfen oder bewusst nicht weiterverfolgt werden.

Jeder Eintrag enthält mindestens: Titel, Quelle (\`system\` / \`admin\`), Kategorie, betroffener Bereich, Beschreibung, verknüpfte Fehler-/Prozessdaten, Status, Priorität, letzter Bearbeitungszeitpunkt und nächste zulässige Aktion.

**Statusabhängige Aktionen im Admin-Optimierungs-Panel:**

Die verfügbaren Aktionen hängen vom Status des Eintrags ab. Es werden nicht in jedem Status alle Aktionen angeboten.

Status \`vorschlag\` / Register „Eingang / Vorschläge":

Zulässige Aktionen: ignorieren, weiter beobachten, zur Analyse freigeben.

Nicht zulässig: direkt als CR vorbereiten, direkt als Ticket vormerken.

Status \`weiter_beobachten\` / Register „Weiter beobachten":

Zulässige Aktionen: zur Analyse freigeben, weiter beobachten fortsetzen, ignorieren.

Nicht zulässig: direkt als CR vorbereiten, direkt als Ticket vormerken.

Status \`analyse_freigegeben\` / Register „Zur Analyse freigegeben":

Zulässige Aktionen: Analysebefund eintragen, zurück zu weiter beobachten, ignorieren.

Nicht zulässig: erneute Freigabe zur Analyse, direktes Ticket ohne Analysebefund.

Status \`analyse_abgeschlossen\`:

Zulässige Aktionen: als CR vorbereiten, weiter beobachten, ignorieren.

Nicht zulässig: direktes Ticket, solange keine CR-Entscheidung oder gleichwertige fachliche Entscheidungsgrundlage vorliegt.

Status \`cr_vorbereitung\` / Register „Als CR vorbereiten":

Zulässige Aktionen: CR-Entwurf erstellen, CR verwerfen, zurück zu Analyse, als Ticket vormerken nach bestätigter CR-Grundlage.

Nicht zulässig: direkte Umsetzung.

Status \`ticket_vorgemerkt\` / Register „Tickets":

Zulässige Aktionen: Ticket priorisieren, Ticket einer späteren Planung zuordnen, Ticket zurückstellen, Ticket schliessen.

Nicht zulässig: automatische Sprint-Aufnahme oder automatische Umsetzung ohne gesonderte Freigabe.

Grundregel: Analyse = Verstehen des Problems. CR = offizielle Beschreibung einer gewünschten Änderung. Ticket = vorbereitete Entwickleraufgabe. Umsetzung erfolgt erst nach gesonderter Sprint-/Umsetzungsfreigabe.

**Kategorien für Optimierungseinträge:**

Optimierungseinträge werden mindestens einer Kategorie zugeordnet:

1\. Fehlerquelle: wiederkehrender Fehler oder technischer Defekt.

2\. Prozessproblem: Ablauf ist unklar, unnötig langsam, fehleranfällig oder erzeugt unnötige Nutzerarbeit.

3\. UI-/UX-Bemerkung: Anordnung, Sichtbarkeit, Bedienbarkeit oder Darstellung eines Elements.

4\. Export-/Formatierungsproblem: Formatvorlagen, Layout, DOCX/PDF-Ausgabe, Fussnoten, Überschriften oder Register.

5\. OCR-/Erkennungsproblem: OCR-Qualität, Layout-Erkennung, Blockzuordnung, Spalten, Fussnoten, Harakāt, Qurʾān-/Hadith-Erkennung.

6\. Übersetzungs-/Stilproblem: Übersetzungslogik, Stilprofil, Glossar, Terminologie, religiöse Formeln oder Fachbegriffe.

7\. Schnittstellen-/Quellenproblem: externe API, Scraping-Pfad, lokale Datenquelle, Shamela, Qurʾān- oder Hadith-Schnittstelle.

8\. Allgemeiner Verbesserungsvorschlag: sonstige Optimierung ohne bereits festgelegte technische Ursache.

Eine Kategorie ist eine Arbeitsklassifikation und keine Entscheidung. Die Kategorie kann im Analyseverlauf angepasst werden.

**Schutzsatz Admin-Optimierungsprozess:**

Kein Optimierungseintrag – weder aus automatischer Mustererkennung noch aus Admin-Eingabe – führt unmittelbar zu einer Architekturänderung, Kanonänderung, Codeänderung, Sprint-Aufnahme oder Umsetzung. Jeder Eintrag bleibt solange ein Vorschlag oder Arbeitsgegenstand, bis der Hauptnutzer/Admin den nächsten zulässigen Prozessschritt ausdrücklich bestätigt. Die Bestätigung eines Prozessschritts ersetzt keine Coding-Freigabe.

### **4.19 Referenz- und Entitäten-System**

**Kategorien:** Gelehrte und Personen / Historische Orte / Masseinheiten / Arabische Bücher / Dynastien und Epochen.

**Quellen Kurz-Bios:** <span dir="rtl">سير أعلام النبلاء, تهذيب التهذيب, وفيات الأعيان, الأعلام للزركلي</span>.

**Quellen Arabische Bücher:** <span dir="rtl">كشف الظنون, الأعلام, معجم المؤلفين, فهرست ابن النديم</span>.

## **5. FESTSTEHENDES DATENMODELL**

### **5.1 Kernobjekte**

Page-UUID, Block-UUID, Satz-UUID, Revisions-UUID, Decision-Event-UUID, Konzept-ID, Quellenattribute.

#### **5.1.1 Hadith-Einzelquellen-Ergebnisobjekt (gemäss §4.16 Datenmodell)**

**Pflichtfelder:**

- einzelquelle_uuid

- gesamtergebnis_uuid

- quelle_id

- quellen_rolle (Pflicht-Snapshot-Feld)

- treffer_status

- technischer_status

- zugriffszeitpunkt

**Pflicht bei treffer_status = treffer:**

- matn_arabisch

**Optional:**

- matn_arabisch_raw

- matn_vokalisiert

- isnad

- sammlung

- werk_nummer

- direktlink

- hukm

- hukm_quelle

- website_uebersetzung (Liste von {lang, text}, mehrsprachig; Einträge werden pro gelieferter Sprache der jeweiligen Quelle geführt, unabhängig von der Zielsprache des Projekts)

**Abgeleitet:**

- textnaehe

- autorquelle_match

- fehlerklasse_418 (gemäss §4.18)

**Eigenschaft:** unveränderlich nach Anlage.

**HTML-Stripping (Modell R):** Für Quellen, deren Matn-Antwort Markup enthält, wird der gelieferte Roh-Body in matn_arabisch_raw persistiert; matn_arabisch enthält die daraus deterministisch abgeleitete Textfassung. Textnähe-, Vergleichs- und Konsenslogik arbeiten auf matn_arabisch. Bei Quellen ohne Markup entfällt matn_arabisch_raw.

**Quellenrolle (quellen_rolle):** Pflicht-Snapshot-Feld. Werte pflicht, erweitert_aktiv, erweitert_sonderrolle, erweitert_suspendiert. Der Wert wird zum Zeitpunkt des Verifikationslaufs festgeschrieben. Keine dynamische Rückableitung gegen den jeweils aktuellen Kanon. hadithportal.com darf im Quellen-Enum nicht geführt werden (Ausschluss kanonisch).

**Enums:**

- treffer_status: treffer / kein_treffer / technischer_fehler / quelle_suspendiert / quelle_nicht_durchsucht.

- technischer_status: ok / timeout / retry_erfolgreich / dom_bruch / parse_fehler / quelle_suspendiert / quelle_nicht_durchsucht / http_4xx / http_5xx.

#### **5.1.2 Hadith-Gesamtergebnisobjekt (gemäss §4.16 Datenmodell)**

**Pflichtfelder:**

- gesamtergebnis_uuid

- block_uuid

- ocr_revision_uuid

- lauf_zeitpunkt

- is_aktiv

- autorwortlaut

- einzelquellen_uuids

- eskalation_ausgefuehrt

- eskalation_quellen_aktiv

- ausgefallene_quellen

- konsens_status

- kutub_as_sitta_signal

- kutub_as_sitta_abweichung_aktiv

- vokalisierungs_konflikt

- decision_event_uuids

**Pflicht, sobald Satzsegmentierung für die Stelle vorhanden ist:**

- satz_uuid

**Pflicht bei belastbarem Konsens:**

- referenz_matn

- referenz_matn_quelle_uuids

**Optional:**

- autor_genannte_quelle

- ocr_konfidenz

- referenz_vokalisierung

- referenz_vokalisierung_quelle_uuid

**Abgeleitet, nicht persistiert** (deterministisch aus Pflicht- und Optionalfeldern, referenzierten Einzelquellen-Lesungen und aktiven decision_events):

- entscheidungsstatus (Werte ohne_aktive_entscheidung / translation_pipeline / conflict_resolution / gemischt; abgeleitet aus nicht-superseded decision_events gemäss §4.11)

- vokalisierungsklasse

- hadith_stellen_typ

- hadith_verifikationsklasse

**Enums:**

- konsens_status: konsens / mehrheit / tie_breaker / kein_konsens / kein_treffer.

- vokalisierungs_konflikt: nein / ja (strikt binär).

**Klassen-Differenzierung** (V-0/V-1/V-2): läuft ausschliesslich über die abgeleitete vokalisierungsklasse. Ist die Typ-Zuordnung im Einzelfall unklar, bleibt vokalisierungs_konflikt auf ja; die Unklarheit wird nur im Logging bzw. in der Konfliktbegründung dokumentiert.

**Eigenschaft:** Pro Stelle und OCR-Revision genau ein aktives Gesamtergebnis (is_aktiv = true). Unveränderlich nach Anlage in Bezug auf einzelquellen_uuids, autorwortlaut, ocr_revision_uuid, lauf_zeitpunkt.

### **5.2 Stilprofil-Objekte (aus Dokument B v1.2)**

**stil_regel:** stil_regel_uuid, account_uuid, sprachpaar, dimension, phänomenfeld (PF-01–PF-12), arabisches_muster, bevorzugte_wiedergabe, konfidenz (Float 0.0–1.0), belege_uuids\[\], status (Enum), regeltyp (Enum), invariant_quelle (Enum), erstellt_aus (Enum), erstellt_at, zuletzt_aktualisiert_at.

**stilbeleg:** beleg_uuid, account_uuid, sprachpaar, arabisches_muster, arabischer_kontext, deutsche_wiedergabe, phänomenfeld, belegtyp, regeltyp, konfidenz, referenz_paar_uuid, nutzer_bestätigt, erstellt_at.

**stilprofil_version:** stilprofil_version_uuid, account_uuid, sprachpaar, version_nummer, erstellt_at, auslöser (Enum), delta (JSON), is_aktiv.

**referenz_paar:** referenz_paar_uuid, account_uuid, sprachpaar, arabischer_text, deutscher_text, bestätigt_at.

**sprachpaar-Enum:** AR_DE, AR_EN, EN_DE, DE_EN. Pflichtfeld in allen vier Stilprofil-Objekten.

**Accountbindung:** Alle Stilprofil-Objekte sind an account_uuid und sprachpaar gebunden. Geltungsbereich genau ein (account_uuid, sprachpaar)-Paar. Kein Cross-Account-Zugriff. Kein Cross-Sprachpaar-Zugriff.

### **5.3 Phänomenfeld-Enum PF-01 bis PF-12**

| **Nr.** | **Phänomenfeld**                                         |
|---------|----------------------------------------------------------|
| PF-01   | Partikelbehandlung                                       |
| PF-02   | Satzverknüpfung und Wiederholung                         |
| PF-03   | Idāfa-Behandlung                                         |
| PF-04   | Masdar-/Verb-Beziehung                                   |
| PF-05   | Fachgleichsetzungen                                      |
| PF-06   | Umgang mit Qurʾān- und Ḥadīṯ-Zitaten                     |
| PF-07   | Isnād-/ḥadīṯ-kritische Fachsprache                       |
| PF-08   | Klammergebrauch                                          |
| PF-09   | Religiös-polemische Begriffe                             |
| PF-10   | Juristisch-vertragliche Metaphorik                       |
| PF-11   | Registerhöhe                                             |
| PF-12   | Fehler, die nicht wieder passieren dürfen (Negativliste) |

### **5.4 EXPORT_EVENT-Schema**

ocr_export_uuid, project_uuid, export_mode, gate_mode, export_config, ocr_revision_snapshot\[\], active_decision_event_uuids\[\], export_warnings\[\], artefact_ref, created_at, active_stilprofil_version_uuid (nullable). Unveränderlich nach Anlage.

### **5.5 Regeltyp-Enum**

invariant / präferenz / tendenz / kandidat.

### **5.6 Hochstufungsregeln**

| **Von** | **Nach** | **Bedingung** |
|----|----|----|
| kandidat | tendenz | Mindestbelegdichte oder Nutzerbestätigung |
| tendenz | präferenz | Höhere Belegdichte oder Nutzerbestätigung |
| präferenz | invariant | Nur durch explizite Nutzerhandlung \[KANON\] |
| invariant | präferenz | Nur durch explizite Nutzerhandlung \[KANON\] |
| jeder Typ | vom_nutzer_gesperrt | Explizite Nutzeraktion oder wiederholtes Korrektursignal |

## **6. FESTSTEHENDE ENTSCHEIDUNGEN**

Alle kanonisch bestätigten Einzelentscheidungen sind in den jeweiligen Abschnitten dieses Dokuments eingearbeitet.

## **7. FESTSTEHENDE QUALITÄTSANFORDERUNGEN**

### **7.1 DOCX-Qualitätsanforderungen**

- DOCX öffnet reparaturfrei in Word.

- Per-paragraph RTL (OCR-Export-DOCX) / Per-Run RTL (Übersetzungs-DOCX).

- Schriftarten serverseitig bereitgestellt.

**Kritische Schriftarten** (Export blockiert bei fehlender Schriftart, kein stiller Fallback):

| **Schriftart** | **Verwendet in** | **Kritikalität** |
|----|----|----|
| KFGQPC Uthmanic Script HAFS | Quran_AR | Kritisch – keine Alternative |
| Traditional Naskh | Hadith_AR, Zitat_AR, Titel_AR, Titel_AR_Untertitel | Kritisch |
| Noto Sans Arabic | UeberschriftAR_1–6, Begriff_AR, FussN_AR | Kritisch |
| Calibri | Body_DE, Titel_DE, Heading 1–6, FN_Uebersetzer, FN_Herausgeber, FN_Verlag | Kritisch |

**Einordnung im Exportprozess:** kanonisch bestätigt als Guard-nah vor dem Preflight-Dialog. Fehlt eine der vier kritischen Schriftarten, wird der Preflight-Dialog nicht geöffnet. Auflösung nur durch technische Wiederherstellung der Schriftart. Kein P-Slot wird belegt.

### **7.2 Formatvorlagen-Baseline v1.1**

Vollständig kanonisch. Alle Werte unverändert übernommen; Kerntabelle siehe Formatvorlagen-Baseline v1.1.

### **7.3 OCR-Qualitätsstandards**

OCR-Darstellung maximal simpel: Noto Sans Arabic, 14 pt. Überschriften nur fett mit grösserem Abstand. Koranverse und Hadithe nur eingerückt mit Randstrich. Fussnoten 11 pt mit Trennlinie.

### **7.4 Sicherheit und Datenschutz**

- SSL und at-rest encryption.

- Passwort-Hashing (bcrypt/Argon2), 2FA optional.

- Kein Timeout bei aktivem Hintergrundprozess, sonst 2 Stunden.

- Papierkorb: 10 Tage.

## **VERSIONSSTAND**

**Status:** Lebendes Master-Dokument – bereinigte Volltextfassung. Einzige kanonische Hauptquelle.

**Kanonisierte Inhalte (Hadith-Verifikationssemantik, Preflight-Verortung, Datenmodell und englischer Strang):**

- Vokalisierungs-Eskalationskriterium V-0/V-1/V-2 mit Aggregations- und Rückfallregel; Feld vokalisierungs_konflikt strikt binär (§4.16.7).

- Hadith-Verifikationsstatus N-1 bis N-10 mit Klassen H-0/H-1/H-2 (§4.16.4).

- Gate-Verortung Hadith-Verifikationsstatus als eigene benannte Gruppe innerhalb der Gate-Prüfungsschicht ohne neue Schicht und ohne P-/W-Slot-Belegung (§4.7.5).

- Datenmodell Mehrquellen-Ergebnisobjekte in vier logischen Ebenen mit quellen_rolle als Pflicht-Snapshot und abgeleiteten Zuständen (§4.16.6 / §5.1.1 / §5.1.2).

- Teilkanonisierung englischer Hadith-Strang K-4 R-1/R-2: englischsprachige Website-Übersetzungen aus Hadith-Verifikationsquellen als sprachneutrales Referenz- und Vergleichsfeld (§4.16.8 / §5.1.1).

**Kanonisierte Inhalte (Konsolidierung Schnittstelle 5):**

- Pflichtmenge P-1/P-2/P-3 unverändert.

- E-1/E-2/E-3/E-4 nach Option B dokumentiert, faktisch suspendiert; E-2 hoch belastbar identifiziert als Alifta-/Harf-Variante; E-3 nur noch als mögliche manuelle Referenzquelle.

- E-5 nach Option B nicht suspendiert, in Sonderrolle „deutsche Übersetzungsquelle / mehrsprachige Referenzquelle".

- hadithportal.com ausdrücklich ausgeschlossen.

- Eskalationslogik faktisch nur E-5 bei automatischer Zuschaltung wirksam (§4.16).

**Kanonisierte Inhalte (Hadith-Integration):**

- Zweistufige Quellenstruktur Pflicht/erweitert (§4.16.1).

- Konsenslogik mit linearem Ranking als Tie-Breaker (§3.5 / §4.16.3).

- Kutub as-Sitta als starker Gewichtungsfaktor (§4.16.3).

- decision_event-Zuordnung 7 Handlungstypen (§4.16.5).

- Vokalisierungsprinzip getrennte Felder ohne alleinigen Textträger (§4.16.7).

**Kanonisierte Inhalte (Übersetzungs-Pipeline-Verhalten, Qurʾān-Erkennungsregeln, Shamela-Modi, OCR-Qualitätsprinzip):**

- Prüf-Modell-Korrekturrecht (§3.6).

- Kein stiller Rollentausch (§3.6).

- Audit-Befunde stoppen Übersetzungsflow nicht (§3.6).

- Qurʾān-Vokalisierungs-Regel (§4.15).

- Qurʾān-API-Ruf-Zeitpunkt (§4.15).

- Qurʾān-Konfidenz-Schutz (§4.15).

- Qurʾān-Projektstellen-Schutz (§4.15).

- Shamela Nutzungsmodi und Lisān/Tāj als Abfrageeinheiten (§3.5).

- OCR-Qualitätsprinzip kein künstlicher Sieger (§3.4).

**Offene Arbeitsfront:**

- Schnittstellen-Arbeitsentwürfe 1–6 laufen, noch kein Kanon.

- Maximum-Modus nicht kanonisiert.

- Wortpanel-Arbeitsstrang läuft separat, noch kein Kanon.

- Offene Punkte explizit offen gehalten. Kein stilles Re-Baselining.
