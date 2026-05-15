<!-- Converted from "BLOCK 3 – SEPARATE VOLLTEXT-ARBEITSSTÄNDE (1).docx" via pandoc 3.9.0.2 on 2026-05-02 -->
<!-- The .docx in this directory remains source-of-truth per docs/canon/README.md authority rule -->
<!-- Conversion is content-faithful (text, tables, identifiers, Swiss German ss, Arabic RTL spans, §-refs); Word-specific visual styling is dropped -->

# **BLOCK 3 – SEPARATE VOLLTEXT-ARBEITSSTÄNDE**

Bereinigte Volltextfassung.

**WICHTIG:** Diese Arbeitsstände sind keine Referenzhinweise. Sie sind echte mitgetragene Volltexte und müssen als solche behandelt werden.

## **ENDFASSUNG 1 – OCR-MAXIMUM-QUALITÄTSLOGIK**

inklusive verschärfte Zusatz-Endfassungen für Schnittstelle 1 und Schnittstelle 2

**Status:** Arbeitsentwurf. Noch kein Kanon. Keine Einarbeitung in Dokument 1 oder Dokument 2. Kein Code. Keine CRs. Keine stillen Architekturänderungen.

### **Punkt 1 – Ziel und Stellung im Gesamtsystem**

Die OCR-Maximum-Qualitätslogik ist kein Ersatz der bestehenden OCR-Pipeline, sondern deren kompromisslose Qualitätsverschärfung.

Sie baut auf dem bestehenden Waraq-Kanon auf:

- OCR ist als 5-Stufen-Rekonstruktionspipeline festgelegt.

- Die bestehende Engine-Kombination ist bereits angelegt:

- Gemini 2.5 Pro Vision

- Google Cloud Vision (DOCUMENT_TEXT_DETECTION) als zusätzliche OCR-Leselinie

- kraken / eScriptorium

- Real-ESRGAN + OpenCV

- CAMeL Tools / Farasa / Mishkal

- LayoutParser / DocTR

- OCR wird blockweise verarbeitet; die Seite ist Checkpoint-Einheit.

- OCR-Review, Schwierigkeitsbericht und DPI-Vergleichsansicht sind bereits vorgesehen.

**Neue Leitregel dieses Arbeitsentwurfs:** Waraq behandelt OCR nicht als „einmal lesen und ausgeben", sondern als mehrstufiges Prüf- und Konsenssystem, das alle verfügbaren Mittel ausschöpft, um den bestmöglichen OCR-Text zu erzeugen.

**Primärziel:**

- maximal richtige Zeichen

- maximal richtige Wortgrenzen

- maximal richtige Leserichtung

- maximal richtige Harakāt und Spezialzeichen, soweit vorhanden

- maximale Sicherheit bei Qurʾān-, Hadith-, Namen-, Isnād- und Fachstellen

**Sekundärziel:**

- Unsicherheit nie verschleiern

- Schwachstellen intelligent priorisieren

- Review nur dort erzwingen, wo die Maschine trotz maximaler Prüfung keinen belastbaren Sieger erzeugen kann

### **Punkt 2 – Mehrfachvorverarbeitung statt Einmal-Render**

Jede OCR-relevante Seite wird nicht nur in einer Bildfassung, sondern in mehreren technischen Fassungen verarbeitet.

**2.1 Standard-Varianten pro Seite**

- Original-Render

- höheres DPI-Render

- kontrastverstärkte Variante

- entrauschte Variante

- deskewte Variante

- dewarpte / entzerrte Variante

- binarisierte Variante

- farberhaltende Variante

**2.2 Ziel der Mehrfachvorverarbeitung** Unterschiedliche OCR-Engines reagieren unterschiedlich auf niedrige Druckqualität, Schieflage, Randverzerrung, feine Harakāt, eng gesetzte Fussnoten, mehrspaltige Layouts, historische Druckbilder und Manuskript-/Kalligraphie-Anteile. Darum wird derselbe Block in mehreren technisch unterschiedlichen Vorlagen gelesen.

**2.3 Arbeitsregel** Keine Vorverarbeitungsvariante gilt automatisch als „die beste". Die Vorverarbeitung ist ein Erzeugungsraum für mehrere OCR-Pfade, nicht ein stiller einmaliger Fix.

### **Punkt 3 – Harte Layout- und Blocklogik vor jeder OCR**

**3.1 Pflichtsegmente:** Haupttext, Überschrift, Unterüberschrift, Fussnote, Randnotiz, Tabellen-/Listenbereich, Qurʾān-Block, Hadith-Block, Seitenzahl/Kolumnentitel, Schmuck/Zierelement/Trennlinie.

**3.2 Leserichtung und Blockordnung:** Harte Vorabprüfung für: Spaltenstruktur, Reihenfolge der Blöcke, Zeilenrichtung, Leserichtungs-Karte, Baseline-Lage, Randzonen, Einrückungs- und Fussnotenbezug.

**3.3 Ziel:** OCR darf nicht direkt auf die ganze Seite losgelassen werden, sondern nur auf strukturierte Blöcke mit bekannter Funktion.

### **Punkt 4 – Multi-Engine-Committee statt Einzelengine**

**4.1 Grundsatz:** Kein Block soll im Maximum-Modus nur von einer OCR-Engine abhängen. Stattdessen wird pro Block ein Engine-Committee eingesetzt.

**4.2 Kernrollen der Engines:**

- **A – Standard-/Druckscan-Leselinien:** Gemini 2.5 Pro Vision und Google Cloud Vision (DOCUMENT_TEXT_DETECTION). Für moderne gedruckte arabische Scans kann Google Cloud Vision als Basis- oder Primärleser eingesetzt werden, sofern Gold-Corpus-Tests dies bestätigen.

- **B – Sonderfall-/Manuskriptleser:** kraken / eScriptorium für Manuskript, Kalligraphie, schwierige historische Blöcke

- **C – Layout-/Detection-Stütze:** LayoutParser / DocTR für Blocklokalisierung und Struktur

- **D – Sprach-/Plausibilitätsstütze:** CAMeL Tools / Farasa / Mishkal in der semantischen Rekonstruktion

**4.3 Maximum-Erweiterung:** Im Maximum-Modus wird ein Block von mehreren Lesern unabhängig gelesen. Mindestens denkbare Rollen: visueller Hauptleser, Zweitleser, Sonderfallleser, Schlichtungsleser, Sprachprüfer, Corpusprüfer.

**4.4 Keine blinde Mehrzahlregel:** Nicht „2 gegen 1" allein entscheidet. Die Engine-Mehrheit ist nur ein Signal, nicht automatisch der Sieger. Innerhalb der KI-Validierungslinie gemäss §3.4 Stufe 3 sind GPT-4o und Gemini 2.5 Pro gleichrangige Konsens-Signalgeber gemäss kanonischer Modellzuweisung §3.4; keine Primär/Prüf-Rollen innerhalb der KI-Linie. Revidierbarkeit der konkreten Modellwahl analog §3.6. Das OCR-Qualitätsprinzip (kein künstlicher Sieger, Konfidenz sinkt, Review priorisiert) greift wie kanonisch §3.4, wenn nach Durchlauf der vorgesehenen Rekonstruktionsstufen mehrere starke konkurrierende Lesungen bestehen bleiben. Die konkrete Gewichtungs- und Auslösematrix zwischen den drei §3.4-Stufe-3-Validierungslinien (regelbasiert, KI-basiert, statistisch) bleibt offen.

### **Punkt 5 – Konsens-, Prüf- und Eskalationslogik**

**5.1 Grundprinzip:** Nicht die erste Lesung gewinnt, sondern die belastbarste Lesung nach mehreren Prüfebenen.

**5.2 Vier Konsensebenen:**

- **Ebene A – Oberflächenkonsens:** Vergleich nach Zeichenfolge, Wortgrenzen, Zeilenstruktur, Übereinstimmung mehrerer Render/Engines.

- **Ebene B – Layoutkonsens:** Passt die Lesung zur Blockklasse, Zeilenlänge, Spalten-/Fussnotenstruktur, Kontext der Nachbarzeilen?

- **Ebene C – Sprachkonsens:** Arabisch morphologisch plausibel? Offensichtliche Unwörter? Unmögliche Flexion? Verdächtige Homoglyphenfehler?

- **Ebene D – Wissenskonsens:** Prüfung gegen Qurʾān, Hadith, Shamela, später Lexika/Terminologie, bekannte religiöse Formeln.

**5.3 Spezialregel für semantisch heikle Blöcke:** Qurʾān-, Hadith-, Isnād-, Namen- und lexikalisch sensible Blöcke werden strenger geprüft als normaler Fliesstext.

**5.4 Kein stiller Scheinsieg:** Wenn mehrere starke konkurrierende Lesungen bestehen bleiben: Konfidenz runter, Review-Relevanz rauf, Stelle priorisieren.

### **Punkt 6 – Eskalationsschleifen für Hochrisikoblöcke**

**6.1 Wann eskaliert wird:** Mehrere Engines widersprechen sich, Konfidenz zu niedrig, Blockklasse = Qurʾān/Hadith/Isnād/Manuskript/Fussnoten-Kleindruck, Layout instabil, Sprachprüfung meldet Unwahrscheinlichkeiten, Corpusabgleich widerspricht Hauptlesung, OCR-Fehlerklasse deutet auf Hochrisiko.

**6.2 Eskalationsmassnahmen:** Erneutes Cropping, erneutes Lesen in mehreren Zoomstufen, alternative Vorverarbeitungsvarianten, Umgebungszeilen mitlesen, Blockklasse neu prüfen, Spezialengine zuschalten, LLM-Schlichtung zuschalten, zusätzliche Corpusabgleiche, Variantenmatrix erzeugen.

**6.3 Leitregel:** Im Maximum-Modus ist Aufwand kein Gegenargument, solange er die OCR-Qualität erhöht.

**6.4 Praktischer Schutz:** Block eskaliert, Seite bleibt Checkpoint, Gesamtjob stoppt nicht automatisch.

### **Punkt 7 – Qualitätsmetriken, Review und Nutzererlebnis**

**7.1 Keine einzige Confidence-Zahl:** Qualität getrennt nach Zeichenstabilität, Wortstabilität, Zeilenstabilität, Blockstabilität, Layoutkonsistenz, Sprachplausibilität, Corpusnähe, Spezialblock-Sicherheit (Qurʾān/Hadith/Isnād), Grad der technischen Degradation.

**7.2 Nutzeroberfläche:** Live sieht der Nutzer weiterhin nur verständliche Seitenzustände, nicht rohe OCR-Innenlogik.

**7.3 OCR-Review:** Zuerst nach oben: ungelöste Qurʾān-Konflikte, ungelöste Hadith-Konflikte, Blocks mit hoher Engine-Divergenz, Blocks mit niedriger Corpusplausibilität, Fussnoten-/Kleindruck-Hochrisiko, Leserichtungs-/Spaltenkonflikte.

**7.4 Was der Nutzer bei schwierigen Stellen sieht:** Originalblock/Crop, stärkste Lesung, alternative Lesung(en), verständlicher Unsicherheitsgrund, ggf. Qurʾān-/Hadith-/Shamela-Hinweis, warum die Stelle priorisiert wurde.

### **Punkt 8 – Persistenz, Nachvollziehbarkeit und offene Punkte**

**8.1 Was intern persistiert werden soll:** Genutzte Vorverarbeitungsvariante(n), gewählte Blockklasse, aktive OCR-Pfade/Engines, technische Ausfälle/Degradationen, Kandidatenlesungen, entscheidtragender Pfad, Gründe für Eskalation, Gründe für Review-Markierung, corpusgestützte Konflikte/Bestätigungen, Seiten-/Blockpriorisierung.

**8.2 Strukturell entschieden (Arbeitsstand, kein Kanon):**

*Aktivierungsebene:* projektweise Aktivierung ine-Committee auf Blocke durch den Nutzer; innerhalb eines aktivierten Projekts steuert die Blockklasse die konkrete Prüftiefe gemäss Schnittstelle 1 Punkt 3. Global- und rein blockweise Aktivierung verworfen. Werkkategorien-Automatik bewusst offen gehalten, nicht still eingeführt.

*Datenmodell-/Persistenz-Verankerung:* Projekt-Flag für den Maximum-Modus auf Projektebene; Provenienzfeld für den aktiven OCR-Modus (Standard / Maximum) pro OCR-Lauf auf Blockebene. Kein neues Kernobjekt. Die finale Feldbenennung bleibt offen.

*Aktivierungsprotokollierung:* Log-Eintrag auf Projektebene im Projekt-Protokoll. Kein decision_event gemäss §4.10. Keine neuen decision_source-Werte.

**8.3 Noch offen** Genaue maximale Anzahl Eskalationsdurchläufe, harte Schwellenwerte Standard/Maximum-Modus, weitere zusätzliche Engines/Provider über Google Cloud Vision hinaus, Kosten-/Latenzgrenzen, genaue Persistenzform der Kandidatenmatrix, automatische Aktivierung nach Werkkategorie, genaue UI-Darstellung alternativer Lesungen, finale Feldbenennung im Datenmodell. Die konkrete Primärrolle und Gewichtung von Google Cloud Vision bleibt Gold-Corpus-abhängig.

### **Schnittstelle 1 – OCR-Hauptengine (Verschärfte Zusatz-Endfassung Maximum-Modus)**

**Status:** Diese Zusatz-Endfassung ersetzt die bestehende Endfassung von Schnittstelle 1 nicht, sondern verschärft sie für den OCR-Maximum-Modus.

**Punkt 1 – Auslöser:** OCR-Hauptengine bleibt nach Upload für alle OCR-pflichtigen Dateitypen zuständig. Im Maximum-Modus wird Mehrfach-Vorverarbeitungsraum pro Seite erzeugt (Original-Render, höheres DPI, kontrastverstärkt, entrauscht, deskewt, dewarpt, binarisiert, farberhaltend).

**Punkt 2 – Zugriffstyp:** Im Maximum-Modus erweitert zu Engine-Committee auf Blockebene: Vorverarbeitung lokal, Layout-/Detection lokal, externe OCR-Leselinien (Gemini 2.5 Pro Vision und Google Cloud Vision DOCUMENT_TEXT_DETECTION), Sonderfall-Leser lokal, zusätzliche Gegenleser/Prüfer je nach Blockklasse, semantische Zusatzvalidierung in Schnittstelle 2. Für moderne gedruckte arabische Scans kann Google Cloud Vision als Basis- oder Primärleser eingesetzt werden, sofern Gold-Corpus-Tests dies bestätigen. Die KI-Validierungslinie innerhalb Stufe 3 folgt der kanonischen Modellzuweisung §3.4 (GPT-4o + Gemini 2.5 Pro parallel als gleichrangige Konsens-Signalgeber innerhalb der KI-Linie, keine Primär/Prüf-Rollen, Revidierbarkeit analog §3.6).

**Punkt 3 – Reihenfolge / Priorität:** Blockklasse steuert Mehrfachlesungspflicht:

- **Standard**-Buchtext / moderne gedruckte arabische Scans → Google Cloud Vision und/oder Gemini 2.5 Pro Vision als Basis-/Hauptleselinie plus Gegenleser nach Konfidenzlage,

- Fussnoten → zusätzliche Zoom-/Render-Varianten,

- Qurʾān/Hadith/Isnād → strenge Mehrfachprüfung,

- Manuskript → kraken/eScriptorium als Spezialleser,

- layoutinstabil → zusätzliche Reihenfolgenprüfung.

**Punkt 4 – Timeout / Retry:** Technischer Retry (API-Fehler, Modul-Ausfall) vs. qualitative Eskalation (Engine-Widerspruch, Instabilität, Hochrisiko-Block). Beide klar getrennt.

**Punkt 5 – Fallback:** Kein stiller fachlicher Engine-Wechsel, kein stiller Rollentausch, keine Scheinsicherheit. Drei Gruppen:

- A: Einzelpfad fällt aus.

- B: Hauptleser da, aber Widerspruch hoch.

- C: keine belastbare Einigung → Review priorisiert, kein künstlicher Sieger.

**Punkt 6 – UI-Sichtbarkeit:** Live: verarbeitet / ausstehend / problematisch. Im OCR-Review: intelligent priorisiert nach Qurʾān-Konflikten, Hadith-Konflikten, Engine-Divergenz, Sprach-/Corpusplausibilität, Layoutinstabilität, Fussnoten-Risiko.

**Punkt 7 – Protokollierung:** Erweitert um: Vorverarbeitungsvarianten, Blockklasse, aktive OCR-Leselinien (einschliesslich Gemini 2.5 Pro Vision und/oder Google Cloud Vision, sofern genutzt), aktive Leser/Gegenleser, Eskalationsgründe, Degradationsmarker, alternative Kandidatenlesungen, entscheidtragender Pfad, Priorisierungsgrund.

**Punkt 8 – Flow-Regel:** Block darf viele interne Prüfungen durchlaufen. Seite bleibt Checkpoint. Gesamtjob stoppt nicht. Problematische Blöcke eskaliert und priorisiert. Technische Degradation und qualitative Restunsicherheit werden mitgetragen, nicht versteckt.

**Kernregel:** Der Maximum-Modus erhöht die Tiefe der Prüfung, nicht die Monolithik des Jobs.

### **Schnittstelle 2 – OCR-semantische Zusatzvalidierung (Verschärfte Zusatz-Endfassung Maximum-Modus)**

**Status:** Diese Zusatz-Endfassung ersetzt die bestehende Endfassung von Schnittstelle 2 nicht, sondern verschärft sie für den OCR-Maximum-Modus.

**Punkt 1 – Auslöser:** Semantische Zusatzvalidierung prüft im Maximum-Modus die Kandidatenmatrix eines Blocks (mehrere Lesungen aus verschiedenen OCR-Leselinien wie Gemini 2.5 Pro Vision und Google Cloud Vision, Vorverarbeitungsvarianten, Zoom-/Crop-Stufen). Die KI-basierte Validierung ist eine der drei §3.4-Stufe-3-Validierungslinien (regelbasiert, KI-basiert, statistisch). Innerhalb der KI-Validierungslinie gelten die kanonisierten Regeln gemäss §3.4: GPT-4o und Gemini 2.5 Pro als gleichrangige Konsens-Signalgeber, keine Primär/Prüf-Rollen, kein künstlicher Sieger bei Uneinigkeit innerhalb der KI-Linie, Revidierbarkeit analog §3.6. Ausgelöst wird die KI-Validierungslinie bei starker Kandidatendivergenz, Layoutinstabilität, Qurʾān-/Hadith-/Isnād-Hochrisiko, Sprach-/Corpusunklarheit. Die konkrete Gewichtungs- und Auslösematrix zwischen den drei §3.4-Stufe-3-Validierungslinien bleibt offen.

**Punkt 2 – Zugriffstyp:** Drei Stränge (regelbasiert, statistisch, KI-basiert) plus vier Prüfebenen: Oberflächenkonsens, Layoutkonsens, Sprachkonsens, Wissenskonsens. Schnittstelle 2 wird im Maximum-Modus zur Schlichtungs- und Konsensschicht.

**Punkt 3 – Reihenfolge / Priorität:** Innerhalb der KI-Validierungslinie sind GPT-4o und Gemini 2.5 Pro gleichrangige Konsens-Signalgeber gemäss kanonischer Modellzuweisung §3.4; kein künstlicher Sieger bei Uneinigkeit innerhalb der KI-Linie. Wenn nach Durchlauf der vorgesehenen Rekonstruktionsstufen mehrere starke konkurrierende Lesungen bestehen bleiben, greift das kanonische OCR-Qualitätsprinzip §3.4 (kein künstlicher Sieger, Konfidenz sinkt, Stelle ins OCR-Review priorisiert). Entscheidend ist die belastbarste Gesamtkonstellation. Spezialregel: Bei Qurʾān/Hadith/Isnād/Hochrisiko kein automatischer Endsieg bei konkurrierenden Lesungen → Review-Priorisierung. Die konkrete Gewichtungs- und Auslösematrix zwischen den drei §3.4-Stufe-3-Validierungslinien bleibt offen.

**Punkt 4 – Timeout / Retry:** Technische Fälle (KI-Timeout, Shamela nicht verfügbar) vs. qualitative Fälle (mehrere plausible Lesungen, keine klare Schlichtung). Kein belastbarer Sieger → Konfidenz runter, Review hoch, kein künstlicher Abschlusssieg.

**Punkt 5 – Fallback:** Drei Gruppen:

- A: technischer Ausfall.

- B: schwaches/neutrales Signal.

- C: unaufgelöste Mehrdeutigkeit trotz Maximum-Prüfung → Review, kein stiller Endsieg.

Innerhalb der KI-Validierungslinie führt Uneinigkeit zwischen GPT-4o und Gemini 2.5 Pro zu sinkender Konfidenz und Review-Priorisierung gemäss kanonischer Modellzuweisung §3.4; kein künstlicher Sieger innerhalb der KI-Linie. Das OCR-Qualitätsprinzip §3.4 greift, wenn nach Durchlauf der vorgesehenen Rekonstruktionsstufen mehrere starke konkurrierende Lesungen bestehen bleiben.

**Schutzsatz:** Unaufgelöste Mehrdeutigkeit ist selbst ein eigener Qualitätsbefund.

**Punkt 6 – UI-Sichtbarkeit:** Live: Seitenstatus. Im Review ableitbar: semantisch unsicher, Quellen widersprüchlich, mehrere starke Lesungen, ohne KI-Schlichtung entschieden, Qurʾān-/Hadith-Hochrisiko, Layout-/Leserichtungskonflikt, stark unsicher.

**Punkt 7 – Protokollierung:** Erweitert um: Kandidatenmatrix, Anzahl konkurrierender Lesungen, Art des Konsens/Nicht-Konsens, Corpusbestätigung/-widerspruch, Spezialblock-Kennzeichnung, Grund der Review-Priorisierung, Grund warum kein Sieger gebildet wurde.

**Punkt 8 – Flow-Regel:** Zusätzliche Konsens-/Schlichtungsschleifen erhöhen Prüfintensität, machen aber keinen Monolith. Ungelöster Block wird markiert und priorisiert. Ungelöste Mehrdeutigkeit ist ein legitimer Output-Zustand.

**Kernregel:** Maximum-Prüfung darf zu mehr Tiefe führen, aber nicht zu stiller Scheinsicherheit und nicht zu monolithischem Abbruchverhalten.

## **ENDFASSUNG 2 – SCHNITTSTELLE 3 – ÜBERSETZUNGS-KI**

**Status:** Arbeitsentwurf. Noch kein Kanon. Keine Einarbeitung in Dokument 1 oder Dokument 2.

### **Punkt 1 – Auslöser**

Die Übersetzungs-KI wird nach abgeschlossenem OCR-Review und IVZ-Bestätigung aufgerufen. Sie läuft chunkweise und RAG-basiert; Chunks enden nie mitten im Satz. Pro Chunk laufen zwei Modelle parallel: Primär (führender Übersetzungsentwurf) GPT-4o, Prüf (parallele Gegenübersetzung und Qualitätsprüfung) Gemini 2.5 Pro, gemäss kanonischer Modellzuweisung in §3.6. Die Zuweisung ist vorläufig kanonisch und revidierbar in einem strukturierten Entscheid bei neueren oder klar besseren Modellen (auch innerhalb derselben Familie); keine stille Modellwechsel-Änderung. Die Rollenlogik bleibt unverändert.

**Ausklammerung akzeptierter Qurʾān-Stellen:** Akzeptierte Qurʾān-Stellen gemäss §4.15 werden im Chunking als geschützte Stellen geführt. Ausgeklammert wird die akzeptierte Qurʾān-Stelle selbst, nicht der umgebende Chunk. Für die geschützte Stelle werden der kanonische arabische Referenztext und die kanonische Zielsprachen-Übersetzung gemäss §4.15 aus den jeweiligen Trägersträngen eingesetzt:

- Arabischer Qurʾān-Referenzbestand als Textträger für arabischen Referenztext und Vokalisierung.

- quranenc.com bzw. lokale Fallback-Kopie der Qurʾān-Übersetzung in der jeweiligen Zielsprache.

Glossar, Stilprofil und RAG wirken nicht auf die geschützte Qurʾān-Stelle. Der übrige Übersetzungsfluss innerhalb des Chunks bleibt unberührt und folgt dem Normalfluss der Übersetzungs-KI. Abgelehnte Qurʾān-Stellen gemäss §4.15 folgen dem Normalfluss. Die Behandlung verifizierter Hadith-Stellen im Verhältnis zur Übersetzungs-KI ist nicht Gegenstand dieser Regelung und bleibt der Hadith-Strang-Ausarbeitung vorbehalten.

### **Punkt 2 – Zugriffstyp**

- **Primärpfad:** GPT-4o – führender Übersetzungsentwurf (Modell-API extern).

- **Prüfpfad:** Gemini 2.5 Pro – parallele Gegenübersetzung und Qualitätsprüfung (Modell-API extern).

- **RAG-Basis und Glossar/Terminologie/Stilprofil:** lokal.

Zwei externe Abhängigkeiten gleichzeitig. Zuweisung kanonisch gemäss §3.6, vorläufig kanonisch und revidierbar gemäss §3.6-Revidierbarkeits-Klausel.

### **Punkt 3 – Reihenfolge / Priorität**

Prüf-Modell hat kein allgemeines stilles Korrekturrecht.

- Bei objektiven deterministischen Befunden: Auto-Korrektur, immer protokolliert und einsehbar.

- Bei substanziellen/interpretativen Abweichungen: Konfidenz sinkt, Stelle für Review markiert.

- Bei echter Ambiguität: Nutzerhinweis, keine stille Entscheidung.

### **Punkt 4 – Timeout / Retry**

Eigene Timeouts pro Modellpfad. Automatisches Retry vorhanden. Chunk markiert, Rest läuft weiter. Zusätzlich steht dem Nutzer ein manueller Retry-Button zur Verfügung (kanonisch §3.6).

Primärpfad-Ausfall: kein stiller Rollentausch, Chunk in Wartezustand mit Auto-Retry. Nach 30 Min ohne Wiederherstellung: aktive Nutzerinformation via In-App + E-Mail (kanonischer Spezialfall §3.6). Konkrete Timeout- und Retry-Werte bleiben offen und live-messungsabhängig.

### **Punkt 5 – Fallback**

| **Situation**          | **Verhalten**                                 |
|------------------------|-----------------------------------------------|
| Ein Modellpfad Timeout | automatisches Retry, dann Chunk markiert      |
| Primär ausgefallen     | kein stiller Rollentausch, Wartezustand       |
| Prüfpfad ausgefallen   | Primär weiter, Chunk als „ungeprüft" markiert |
| Beide ausgefallen      | Wartezustand und Auto-Retry                   |

Über alle Ausfallkonstellationen hinweg steht dem Nutzer ein manueller Retry-Button zur Verfügung (kanonisch §3.6). Aktive Nutzerinformation nach 30 Min ohne Wiederherstellung via In-App + E-Mail (kanonischer Spezialfall §3.6).

Sonstige Klasse-B-Fehler der Übersetzungs-KI, die nicht unter diesen 30-Min-Spezialfall fallen, werden protokolliert und über den Dashboard-Statusindikator aggregiert gemeldet, sobald die Häufungsschwelle gemäss §4.18 Spur 2 erreicht ist (kanonische Klasse-B-Generallogik). Konkrete Häufungsschwellenwerte live-messungsabhängig.

Systemweit tot: Job pausiert, Resume möglich.

**Schutzsatz:** Es gibt keinen stillen Rollentausch.

### **Punkt 6 – UI-Sichtbarkeit**

Seitenweise Fortschrittsanzeige. Chunk-Zustände: verarbeitet / ausstehend / ungeprüft / problematisch. Auto-Korrekturen dezent markiert, auf Anfrage einsehbar. Review-Markierungen sichtbar mit Grundtyp. Dashboard-Statusindikator bei API-Ausfall bestehen bis Wiederherstellung.

### **Punkt 7 – Protokollierung**

**Intern:** führendes Modell pro Chunk, Prüf-Modell-Befund, Art des Befunds (objektiv/interpretativ), Auto-Korrekturen mit Diff, Konfidenz, Ausfälle, Retry, Wartezustand/Auto-Retry, Review-Markierungen mit Grund.

**Für Nutzer:** abgeleitete Statussicht.

### **Punkt 8 – Flow-Regel**

Chunkweise, nicht monolithisch. Einzelne Chunk-Fehlschläge stoppen Gesamtjob nicht. Kein stiller Rollentausch. Gesamtjob nur bei systemweitem Totalausfall in Wartezustand. Inhaltliche Audit-Befunde (A-01 bis D-03) stoppen Flow nicht; sie werden persistiert und in Preflight weitergeführt. Auto-Korrekturen immer protokolliert und nie still.

## **ENDFASSUNG 3 – SCHNITTSTELLE 4 – QURʾĀN-SCHNITTSTELLE**

**Status:** Arbeitsentwurf. Noch kein Kanon. Keine Einarbeitung in Dokument 1 oder Dokument 2.

### **Punkt 1 – Auslöser**

Drei Auslöser:

- **A (OCR-Stufe 1):** Block vorgemerkt, kein API-Ruf.

- **B (OCR-Stufe 5):** lokales Matching → Vers-Metadaten, kein API-Ruf.

- **C (Übersetzungsphase):** API-Ruf quranenc.com, erst hier extern.

Erkannte und akzeptierte Verse werden nicht durch KI übersetzt, sondern durch kanonische Quelle bedient.

### **Punkt 2 – Eingabe**

Sure-Nummer, Aya-Start/Ende (aus B), Sprache/Übersetzungsversion (german_rwwad), Match-Konfidenz (intern, steuert automatisch vs. manuell).

**Vokalisierungs-Regel:** Nach akzeptierter Erkennung ist quranenc.com alleiniger Textträger. Kein freier Wahlfall. Prüfbedürftig nur die Erkennungsfrage.

### **Punkt 3 – Ausgabe**

Kanonischer arabischer Text (vokalisiert, überschreibt OCR), deutsche Übersetzung (german_rwwad), Sure/Aya verifiziert, Quellen-Kennung, Fallback-Indikator.

Speist Quellenangabe-Logik:

- Hat Autor Quellenangabe → System verifiziert.

- Keine → Stelle bleibt leer, Nutzer bekommt Option.

### **Punkt 4 – Fehlerverhalten**

- API-Ausfall: stiller Fallback auf lokale Kopie (nur Protokoll).

- Vers nicht gefunden: Warn-Icon und Protokoll.

- Lokale Kopie auch nicht verfügbar: Warn-Icon und Protokoll.

- Konfidenz unter Schwelle: manuelle Bestätigung vorgelagert.

### **Punkt 5 – Authentifizierung und Verbindungsparameter**

API-Endpunkt, Auth, Rate-Limit, Timeout, Retry: alles unspezifiziert (aktive Arbeitsfront). Lokale Fallback-Kopie: kanonisch vorhanden, vollständig.

### **Punkt 6 – Verknüpfung mit internen Objekten**

- **Block-UUID:** Träger der Vers-Metadaten.

- **Satz-UUID:** Träger der kanonischen Ausgabe.

- **Quellenattribute:** Sure, Aya-Range, Quellen-Kennung, Fallback-Indikator.

- **Decision-Event-UUID:** bei manueller Bestätigung/Verwerfung.

### **Punkt 7 – Versionierung**

Nachvollziehbar: aktive Qurʾān-Kopie, Primär-API oder Fallback, Sure/Aya-Kombination, Übersetzungsversion, manuelle Bestätigung, Änderung lokale Kopie.

**Kernregel:** Bereits gespeicherte Projektstellen bleiben bei Änderung der lokalen Kopie unverändert. Kein stilles Überschreiben.

### **Punkt 8 – Offene Punkte**

Konfidenz-Schwellenwert, API-Endpunkt/Auth/Rate-Limit/Timeout/Retry, Versionierung german_rwwad, Modellierung Vers-Metadaten B, englische Qurʾān-Übersetzung.

## **ENDFASSUNG 4 – SCHNITTSTELLE 5 – HADITH-SCHNITTSTELLE**

**Status:** Arbeitsentwurf. Noch kein Kanon. Keine Einarbeitung in Dokument 1 oder Dokument 2.

**Kanonisierungsstand:**

- Hadith-Integration: fünf Teilbereiche kanonisiert (Quellenstruktur, Konsenslogik, Kutub-as-Sitta, decision_event-Zuordnung, Vokalisierungsprinzip). Integrationsblöcke A-1–A-5 und B-1–B-4 eingearbeitet.

- Konsolidierungsstand der erweiterten Hadith-Quellenmenge: E-1/E-2/E-3/E-4 Option B suspendiert, E-5 in Sonderrolle; hadithportal.com ausgeschlossen.

- Hadith-Verifikationssemantik und Datenmodell: Vokalisierungs-Eskalationskriterium V-0/V-1/V-2, Hadith-Verifikationsstatus N-1 bis N-10 / H-0/H-1/H-2, Gate-Verortung, Datenmodell Mehrquellen-Ergebnisobjekte, K-4 R-1/R-2 sprachneutrales Referenzfeld englisch.

### **Aktive Arbeitsbasis (historischer Werkbank-Stand, hier preserviert als Entwicklungsspur; überholt durch Kanon §4.16)**

6 aktive Quellen: <span dir="rtl">الدُّرَرُ السَّنِيَّة, جَامِعُ الكُتُبِ التِّسْعَة</span>, Sunnah.com, <span dir="rtl">مَوْسُوعَةُ الأَحَادِيثِ النَّبَوِيَّة</span>, Islamweb, Shamela. <span dir="rtl">المكتبة الوقفية</span> nicht Teil der aktiven Suchbasis.

**Hinweis:** Diese ursprüngliche Listung ist durch die Hadith-Integration (zweistufige Quellenstruktur Pflicht/erweitert in §4.16) und den Konsolidierungsstand der erweiterten Hadith-Quellenmenge (E-1/E-2/E-3/E-4 faktisch suspendiert, E-5 in Sonderrolle, hadithportal.com ausgeschlossen) überholt. Massgeblich ist der Kanonstand in Dokument 1 §4.16.

### **Punkt 1 – Auslöser**

- OCR-Stufe 1: Hadith-Block vorgemerkt.

- OCR-Stufe 5: lokales Matching.

- Vor Übersetzung: Konfidenz prüfen.

- Übersetzungsphase: externer Mehrquellen-Abruf.

Erster externer Ruf erst in Übersetzungsphase.

### **Punkt 2 – Eingabe**

Erkannter arabischer Referenztext, Match-Konfidenz, vom Autor genannte Quelle, Einordnung exakt/Kurzfassung/Zusammenfassung, Isnād-/Matn-Hinweise.

**Normalisierung:** Suche ohne/mit Harakāt, OCR-Verzerrungen, Teilwortlaut, Matn/Isnād-Trennung, Kurzfassung vs. Vollhadith.

### **Punkt 3 – Ausgabe**

Mehrquellen-Ergebnis pro Quelle: Trefferstatus, Matn, Vokalisierung, Isnād, Sammlung/Werk/Nummer, Direktlink, Website-Übersetzung, Authentizität/Hukm, Abweichung, Textnähe, technischer Status.

Drei Zielausgaben:

- **A:** Referenz-Matn.

- **B:** Referenz-Vokalisierung.

- **C:** Provenienz-/Vergleichspaket.

Deutsche Übersetzung durch Waraq-KI; Website-Übersetzungen extrahiert und vergleichbar.

### **Punkt 4 – Fehlerverhalten**

- **Gruppe A:** technischer Quellenfehler – andere laufen weiter.

- **Gruppe B:** inhaltlicher Nichttreffer – schwaches Signal.

- **Gruppe C:** Gesamt-Verifikationsausfall – Warn-Icon, Protokoll, Review-Panel, kein automatisches Einfügen.

### **Punkt 5 – Fallback- und Vergleichslogik**

Pflichtsuche über alle aktiven Quellen.

**Suchmodi:** exakter Wortlaut, Teilwortlaut, Quelle+Wortlaut, Kurzfassung, Isnād-Anfang, normalisierte OCR-Variante, ohne/mit Harakāt.

**Vergleich nach:** Wortlautnähe, Mehrquellen-Trägerschaft, Autorquellen-Nähe, Isnād-Bezug, Vokalisierungskonsistenz, Authentizitätssignalen, Website-Übersetzungslage, Kutub-as-Sitta-Signal.

### **Punkt 6 – Nutzerlogik und Konfliktfälle**

- **Fall A:** Konsens.

- **Fall B:** Autor nennt Quelle, passt.

- **Fall C:** Autor nennt Quelle, Wortlautkonflikt.

- **Fall D:** keine Quelle genannt.

- **Fall E:** keine Quelle liefert Treffer → 5 Nutzeroptionen.

7 decision_event-relevante Handlungen.

### **Punkt 7 – Isnād-Logik und vorläufige Nachvollziehbarkeit**

Mindestens nachvollziehbar: Autorwortlaut, durchsuchte Quellen, Referenz-Matn-Quellen, Vokalisierungsquelle, Verifikationsquellen, Quellenkonflikte, Website-Übersetzungen, manuelle Entscheidungen, Nulltreffer.

### **Punkt 8 – Noch offene Punkte (Werkbank-Stand bei Erstellung; viele zwischenzeitlich kanonisiert)**

Technische Zugriffsspezifikation pro Quelle, Konfidenz-Schwellenwert, endgültige Variantenanzeige, UI Kurzfassung vs. Vollhadith, Datenmodell Mehrquellen-Ergebnisobjekte, decision_source-Zuordnung, Vokalisierungsregel, englischer Hadith-Strang, Anschlussfähigkeit <span dir="rtl">جامع الكتب التسعة</span>, Verhältnis zu §4.16, Nachvollziehbarkeitslogik.

## **ENDFASSUNG 5 – SCHNITTSTELLE 6 – SHAMELA-/LEXIKON-SCHNITTSTELLE**

**Status:** Arbeitsentwurf. Noch kein Kanon. Keine Einarbeitung in Dokument 1 oder Dokument 2.

Massgeblich ist die detaillierte Fassung. Zusammen mit den Schnittstelle-6-Arbeitsblöcken (Technische Zugriffsschicht, Verifikationsrahmen, Prüfprotokoll, Rückspiel-/Auswertungslogik, operative Durchführungsvorlage) bildet diese Endfassung den vollständigen aktuellen Arbeitsstand von Schnittstelle 6.

Der fachliche Stand ist aus Dokument 2 §2F, §2G und §2H vollständig ableitbar.

### **Stabilisierte Kernentscheidungen**

- Shamela-Gesamtbestand = Eskalationssuchraum, nicht dritte gleichartige Lexikonquelle.

- Dreistufiger Suchlauf:

  - Stufe 1 exakt

  - Stufe 2 erweitert

  - Stufe 3a gröbere Lexikonsuche

  - Stufe 3b Eskalation Shamela-Gesamtbestand

- Stufe 3b wird nur auf explizite Nutzeranforderung ausgelöst (Variante B). Spätere Hybrid-Logik (Variante C) bleibt als mögliche Verfeinerung offen.

- Qualitative Prüflogik für „belastbar" als strukturierte Leitkriterien-Reihenfolge verankert (5 Dimensionen).

- Optionaler morphologisch-kontextueller Fussnoten-Entwurf als Fallback bei fehlendem Lexikontreffer.

- Abgrenzung Fallback vs. §4.17: getrennte Stränge, Zusammenführung bewusst offen.

- Shamela zwei Nutzungsmodi: Modus A (OCR-nahe, systemausgelöst), Modus B (nutzergesteuert, Lexikon-Workflow).

### **Drei Ebenen vor dem lexikalischen Fussnoten-Eintrag**

1.  Ebene 1 – Morphologische Kurzanalyse.

2.  Ebene 2 – Lexikonlage (mit Drei-Stufen-Klassifikation).

3.  Quellenbasis-Auswahl (Zwischenschritt).

4.  Ebene 3 – Fussnoten-Generator.

**Nächster operativer Schritt:** Reale Shamela-Ist-Aufnahme (derzeit geparkt; wird erst wieder bearbeitet, wenn der Nutzer sie ausdrücklich wieder aufgreift).

## **ARBEITSBLOCK – SCHNITTSTELLE 6 – TECHNISCHE ZUGRIFFSSCHICHT SHAMELA / LISĀN / TĀJ**

**Status:** Arbeitsentwurf. Noch kein Kanon. Keine Einarbeitung in Dokument 1 oder Dokument 2. Kein Code. Keine CRs. Keine stillen Architekturänderungen. Hadith-Suche in Shamela bleibt Teil von Schnittstelle 5, nicht von Schnittstelle 6. Wortpanel-Strang bleibt getrennt.

### **T6-1 – Zulässige Annahmen über den lokalen Shamela-Bestand**

- **Annahme A-1 – Datenbankformat:** Shamela speichert Werke in einem strukturierten Format (historisch SQLite-basiert, bok-Dateien). Das tatsächliche Format der eingesetzten Shamela-Version muss vor Implementierung verifiziert werden. Es wird kein bestimmtes Format als gegeben vorausgesetzt.

- **Annahme A-2 – Werkidentifikation:** Jedes Werk innerhalb Shamela besitzt eine eindeutige Werk-ID (BkId oder vergleichbar). Die konkrete Bezeichnung und Struktur der Werk-IDs muss verifiziert werden.

- **Annahme A-3 – Textgranularität:** Shamela-Werke sind intern in adressierbare Texteinheiten unterteilt (Seiten, Abschnitte oder vergleichbar). Ob diese Einheiten seitenbasiert, kapitelbasiert oder anders organisiert sind, muss pro Werk bzw. pro Shamela-Version verifiziert werden.

- **Annahme A-4 – Volltextsuche:** Der Shamela-Bestand ist volltextsuchbar (nicht nur über Metadaten). Ob diese Suche über eine eigene interne Indexierung oder über externe Volltextindizierung läuft, muss verifiziert werden.

- **Annahme A-5 – Lisān und Tāj als Werke:** Lisān al-ʿArab und Tāj al-ʿArūs liegen als einzelne identifizierbare Werke im Shamela-Bestand vor und können über ihre Werk-IDs gezielt angesteuert werden. Die konkreten Werk-IDs müssen verifiziert werden.

- **Annahme A-6 – Vokalisierung im Bestand:** Der Grad der Vokalisierung variiert innerhalb des Shamela-Bestands von Werk zu Werk und ggf. innerhalb eines Werks. Suchanfragen müssen sowohl mit als auch ohne Harakāt funktionieren.

**Regel:** Keine dieser Annahmen darf still als verifiziert behandelt werden.

### **T6-2 – Logische Zugriffseinheiten**

- **Einheit L – Lisān al-ʿArab:** Primäre Lexikonquelle. Suche auf dieses Werk eingrenzbar.

- **Einheit T – Tāj al-ʿArūs:** Gleichrangig neben Lisān.

- **Einheit G – Shamela-Gesamtbestand:** Nur in Stufe 3b und Modus A. Kein gleichartiger Lexikon-Status.

### **T6-3 – Minimale technische Suchfähigkeiten pro Stufe**

- **Stufe 1 – Exakte Suche (L und/oder T):** Exakte Zeichenkettensuche, mit und ohne Harakāt, Trefferstelle mit Kontext.

- **Stufe 2 – Erweiterte Suche (L und/oder T):** Wurzelbasiert, Teilwortsuche. Wurzelquelle (intern oder extern) offen.

- **Stufe 3a – Gröbere Lexikonsuche (L und/oder T):** Semantisch gelockert, Nachbareinträge, phonetisch ähnlich, Homoglyphen. Transparenzmarker „indirekte Evidenz".

- **Stufe 3b – Eskalation (G):** Nur auf explizite Nutzeranforderung. Gesamtbestand. Qualitative Prüflogik (5 Dimensionen).

### **T6-4 – Zugriffspfade Modus A vs. Modus B**

- **Modus A – OCR-intern:** Systemausgelöst, OCR-Stufe 3, Suchraum G, Stufe 1+2, kein Nutzer-Feedback, Performance-kritisch.

- **Modus B – Nutzergesteuert:** Explizite Aktion, Übersetzungsphase, Suchraum L/T (Stufe 1–3a) und optional G (3b), vollständiger Nutzer-Feedback-Pfad, interaktive Latenz.

**Trennregel:** Selbe Datenquelle, selbe Zugriffsschicht, aber Auslöser, Suchraum, Suchtiefe, Ergebnis-Verwendung und Nutzerinteraktion unterschiedlich.

### **T6-5 – Zwingende technische Vorbedingungen vor Implementierung**

V-1 bis V-10: alle offen. Siehe Verifikationsrahmen.

### **T6-6 – Bewusst offen gehaltene Punkte**

Konkretes Datenbankformat, externe Indizierung, Hybrid-Logik 3b (Variante C), Abgrenzung §4.17, Wortpanel-Strang, Hadith-Suche (→ Schnittstelle 5), UI-Trigger Modus B.

## **ARBEITSBLOCK – SCHNITTSTELLE 6 – VERIFIKATIONSRAHMEN SHAMELA / LISĀN / TĀJ**

**Status:** Arbeitsentwurf. Noch kein Kanon. Keine Ergebnisse enthalten.

### **Teil 1 – Annahmen A-1 bis A-6**

- **A-1 (Datenbankformat):** Direkte Inspektion Dateisystem + DB-Viewer. Verifiziert bei eindeutiger Identifikation an ≥ 3 Werken. Folgefrage: native vs. externe Indizierung.

- **A-2 (Werkidentifikation):** Metadaten-DB-Inspektion, Stichprobe ≥ 10. Verifiziert bei eindeutigem stabilem Schema. Folgefrage: Suchraum-Steuerung L/T/G.

- **A-3 (Textgranularität):** Tabellenstruktur ≥ 3 Werke. Verifiziert bei konsistenter adressierbarer Unterteilung. Folgefrage: Trefferstellen-Format V-7.

- **A-4 (Volltextsuche):** Testabfrage und Zeitmessung. Verifiziert bei funktionierender werkeingrenzbarer Suche in akzeptabler Zeit. Folgefrage: Indizierungstechnologie.

- **A-5 (Lisān/Tāj vorhanden):** Werk-IDs und Stichprobe (<span dir="rtl">ك-ت-ب</span>). Verifiziert bei Fund beider Werke mit plausibel vollständigem Bestand. Folgefrage: bei Fehlen → Ebene-2-Logik neu bewerten.

- **A-6 (Vokalisierung):** 30 Textausschnitte (10 Lisān, 10 Tāj, 10 andere). Verifiziert bei dokumentiertem Grad. Folgefrage: Suchnormalisierung V-5.

### **Teil 2 – Vorbedingungen V-1 bis V-10**

- **V-1 (Datenbankformat):** = A-1. Blockiert fast alles.

- **V-2 (Werk-ID-Schema):** = A-2. Blockiert Suchraum-Steuerung.

- **V-3 (Textgranularität):** = A-3. Blockiert V-7.

- **V-4 (Volltextsuche):** = A-4 + Entscheidung native/extern. Hängt von V-1 ab.

- **V-5 (Normalisierung):** Harakāt-Stripping, Unicode-Normalisierung, Hamza/Alif-Varianten. Hängt von A-6 + V-1 ab.

- **V-6 (Wurzelzuordnung):** Shamela-intern oder extern (CAMeL/Farasa). Hängt von V-1 ab.

- **V-7 (Rückgabeformat):** Felder pro Treffer, Kontextumfang, Positionsangabe. Hängt von V-2 + V-3 ab.

- **V-8 (Latenz):** Zielwerte Modus A (Batch) + Modus B (interaktiv). Hängt von V-4 ab.

- **V-9 (Trefferzahl):** Maximum, Paginierung, Modi-Unterschiede.

- **V-10 (Fehlerverhalten):** Pro Fehlerkategorie: Meldung/Warnung/Skip/Blockade. Konsistenz mit §4.18.

### **Teil 3 – Prüfreihenfolge**

1.  **Schritt 1 (Basis):** V-1 / A-1 → zuerst.

2.  **Schritt 2 (Kernstruktur):** V-2 / A-2 + V-3 / A-3 + A-5 + A-6 → parallel nach Schritt 1.

3.  **Schritt 3 (Sucharchitektur):** V-4 + V-5 + V-6 → nach Schritt 1+2.

4.  **Schritt 4 (Spezifikation):** V-7 + V-8 + V-9 + V-10 → nach Schritt 2+3.

## **ARBEITSBLOCK – SCHNITTSTELLE 6 – PRÜFPROTOKOLL REALE SHAMELA-IST-AUFNAHME**

**Status:** Arbeitsentwurf. Ausfüllbares Prüfprotokoll. Noch kein Kanon. Keine Ergebnisse enthalten. Felder mit \_\_\_\_\_ sind durch den Prüfer auszufüllen. Prüfreihenfolge: Schritt 1 → 2 → 3 → 4.

(Derzeit geparkt, wird erst wieder bearbeitet, wenn der Nutzer ausdrücklich wieder aufgreift.)

### **Schritt 1 – Basis**

**A-1 / V-1 – Datenbankformat:**

- Installationspfad: \_\_\_\_\_

- Verzeichnisstruktur (oberste 2 Ebenen): \_\_\_\_\_

- Dateitypen im Bestand: \_\_\_\_\_

- Tabellenstruktur Beispielwerk: \_\_\_\_\_

- Zentrale Metadaten-DB vorhanden (ja/nein): \_\_\_\_\_

- Falls ja – Tabellenstruktur: \_\_\_\_\_

- Shamela-Version: \_\_\_\_\_

- Sonstiges / Auffälligkeiten: \_\_\_\_\_

- Status: ☐ verifiziert ☐ nicht verifiziert ☐ unklar

### **Schritt 2 – Kernstruktur**

**A-2 / V-2 – Werkidentifikation:**

- Feldname Werk-ID: \_\_\_\_\_

- ID-Typ: \_\_\_\_\_

- Stichprobe 10 Werke (ID \| Titel \| Autor): 1. \_\_\_\_\_ 2. \_\_\_\_\_ 3. \_\_\_\_\_ 4. \_\_\_\_\_ 5. \_\_\_\_\_ 6. \_\_\_\_\_ 7. \_\_\_\_\_ 8. \_\_\_\_\_ 9. \_\_\_\_\_ 10. \_\_\_\_\_

- Eindeutigkeit bestätigt (ja/nein): \_\_\_\_\_

- Status: ☐ verifiziert ☐ nicht verifiziert ☐ unklar

**A-5 – Lisān und Tāj als Werke:**

- Lisān al-ʿArab – Werk-ID: \_\_\_\_\_

- Lisān – Stichprobe <span dir="rtl">ك-ت-ب</span> gefunden (ja/nein): \_\_\_\_\_

- Lisān – Anzahl Texteinheiten/Seiten: \_\_\_\_\_

- Tāj al-ʿArūs – Werk-ID: \_\_\_\_\_

- Tāj – Stichprobe <span dir="rtl">ك-ت-ب</span> gefunden (ja/nein): \_\_\_\_\_

- Tāj – Anzahl Texteinheiten/Seiten: \_\_\_\_\_

- Status: ☐ verifiziert ☐ nicht verifiziert ☐ unklar

**A-3 / V-3 – Textgranularität:**

- Werk 1 (Lisān/Tāj) – Felder: \_\_\_\_\_

- Werk 1 – Beispielwerte (3 Einträge): \_\_\_\_\_

- Werk 1 – Durchgehend nummeriert (ja/nein): \_\_\_\_\_

- Werk 2 (anderes) – Felder: \_\_\_\_\_

- Werk 3 (Nicht-Lexikon) – Felder: \_\_\_\_\_

- Konsistenz zwischen Werken (ja/nein/teilweise): \_\_\_\_\_

- Status: ☐ verifiziert ☐ nicht verifiziert ☐ unklar

**A-6 – Vokalisierung:**

- Lisān – vorherrschender Vokalisierungsgrad: \_\_\_\_\_

- Lisān – konsistent (ja/nein): \_\_\_\_\_

- Tāj – vorherrschender Vokalisierungsgrad: \_\_\_\_\_

- Tāj – konsistent (ja/nein): \_\_\_\_\_

- Allgemeiner Bestand – vorherrschend: \_\_\_\_\_

- Allgemeiner Bestand – konsistent (ja/nein): \_\_\_\_\_

- Status: ☐ verifiziert ☐ nicht verifiziert ☐ unklar

### **Schritt 3 – Sucharchitektur**

**V-4 – Volltextsuchfähigkeit:**

- Einzelwerk-Suche funktioniert (ja/nein): \_\_\_\_\_

- Einzelwerk – Antwortzeit: \_\_\_\_\_

- Gesamtbestand-Suche funktioniert (ja/nein): \_\_\_\_\_

- Gesamtbestand – Antwortzeit: \_\_\_\_\_

- FTS-Index vorhanden (ja/nein): \_\_\_\_\_

- Externe Indizierung nötig (ja/nein/unklar): \_\_\_\_\_

- Status: ☐ verifiziert ☐ nicht verifiziert ☐ unklar

**V-5 – Vokalisierungs-Normalisierung:**

- Suche mit Harakāt – Treffer (ja/nein): \_\_\_\_\_

- Suche ohne Harakāt – Treffer (ja/nein): \_\_\_\_\_

- Tatweel-Behandlung: \_\_\_\_\_

- Hamza-Varianten: \_\_\_\_\_

- Alif-Maqsura/Ya: \_\_\_\_\_

- Normalisierung nötig auf (Abfrage/Index/beide): \_\_\_\_\_

- Status: ☐ verifiziert ☐ nicht verifiziert ☐ unklar

**V-6 – Wurzelzuordnungs-Quelle:**

- Wurzelfeld vorhanden in Lisān (ja/nein): \_\_\_\_\_

- Wurzelfeld vorhanden in Tāj (ja/nein): \_\_\_\_\_

- Falls ja – Feldname: \_\_\_\_\_

- Stichprobe korrekt (ja/nein): \_\_\_\_\_

- Externer Pfad nötig (ja/nein): \_\_\_\_\_

- Status: ☐ verifiziert ☐ nicht verifiziert ☐ unklar

### **Schritt 4 – Spezifikation**

**V-7 – Ergebnis-Rückgabeformat:**

- Verfügbare Felder pro Treffer: \_\_\_\_\_

- Kontextumfang: \_\_\_\_\_

- Seitenreferenz vorhanden (ja/nein): \_\_\_\_\_

- Für Modus A ausreichend (ja/nein): \_\_\_\_\_

- Für Modus B ausreichend (ja/nein): \_\_\_\_\_

- Status: ☐ verifiziert ☐ nicht verifiziert ☐ unklar

**V-8 – Latenz:**

- Einzelwerk – Mittelwert: \_\_\_\_\_ ms / Maximum: \_\_\_\_\_ ms

- Gesamtbestand – Mittelwert: \_\_\_\_\_ ms / Maximum: \_\_\_\_\_ ms

- Für Modus A akzeptabel (ja/nein/unklar): \_\_\_\_\_

- Für Modus B akzeptabel (ja/nein/unklar): \_\_\_\_\_

- Status: ☐ verifiziert ☐ nicht verifiziert ☐ unklar

**V-9 – Trefferzahl / Paginierung:**

- Treffer häufiges Wort Einzelwerk: \_\_\_\_\_

- Treffer häufiges Wort Gesamtbestand: \_\_\_\_\_

- Paginierung nötig (ja/nein): \_\_\_\_\_

- Status: ☐ verifiziert ☐ nicht verifiziert ☐ unklar

**V-10 – Fehlerverhalten:**

- Verhalten bei fehlender Werk-ID: \_\_\_\_\_

- Verhalten bei fehlender Datei: \_\_\_\_\_

- Fehlermeldung verständlich (ja/nein): \_\_\_\_\_

- Absturzverhalten (ja/nein): \_\_\_\_\_

- Status: ☐ verifiziert ☐ nicht verifiziert ☐ unklar

### **Abschlussfelder**

- Prüfer: \_\_\_\_\_

- Datum: \_\_\_\_\_

- Shamela-Version: \_\_\_\_\_

- Server / Umgebung: \_\_\_\_\_

- Gesamtstatus: ☐ Schritt 1 ☐ Schritt 2 ☐ Schritt 3 ☐ Schritt 4

- Offene Punkte / Auffälligkeiten: \_\_\_\_\_

## **ARBEITSBLOCK – SCHNITTSTELLE 6 – RÜCKSPIEL- UND AUSWERTUNGSLOGIK SHAMELA-IST-AUFNAHME**

**Status:** Arbeitsentwurf. Noch kein Kanon. Keine Einarbeitung in Dokument 1 oder Dokument 2. Kein Code. Keine CRs. Keine stillen Architekturänderungen. Keine reale Verifikation enthalten. Keine Ergebnisse enthalten.

(Derzeit geparkt, folgt der realen Ist-Aufnahme.)

### **R-1 – Grundsätze der Rückspielung**

- **R-1.1** Einzige zulässige Eingabe ist ein ausgefülltes Prüfprotokoll (Schritt 1–4) mit realen Felddaten und gesetztem Status pro Prüfpunkt.

- **R-1.2** Kein Prüfpunkt darf ohne ausgefülltes Protokollfeld als verifiziert behandelt werden. Leere Felder bei gesetztem Status „verifiziert" sind ein Widerspruch und erzwingen Rückfrage.

- **R-1.3** Prüfergebnisse werden zunächst als Rohdaten übernommen, nicht direkt in den Arbeitsstand integriert. Erst nach der Auswertung (R-3) und der Folgepfad-Zuordnung (R-4) entsteht ein integrationsreifer Stand.

- **R-1.4** Ergebnisse aus der realen Ist-Aufnahme dürfen die bestehende Architektur nicht still verändern. Wenn ein Ergebnis eine Architekturanpassung nahelegt, wird das als offener Punkt dokumentiert und separat entschieden.

### **R-2 – Übernahme der Prüfergebnisse**

- **R-2.1 – Formale Prüfung bei Entgegennahme:** Pro Prüfpunkt Status gesetzt? Felddaten ausgefüllt? Prüfreihenfolge eingehalten? Metadaten vollständig?

- **R-2.2 – Umgang mit unvollständigem Protokoll:** Schritt 1 fehlt → kein späterer Schritt auswertbar. Einzelne Felder fehlen → betroffener Punkt = „unklar". Rückfrage.

- **R-2.3 – Teilweise Rückspielung:** Zulässig (nur Schritt 1 oder 1+2). Auswertung nur für vorliegende Schritte. Rest = „ausstehend".

### **R-3 – Auswertungslogik pro Status**

- **Verifiziert:** Annahme wird zu verifiziertem Befund hochgestuft. Abhängige Vorbedingungen freigeschaltet. Folgefrage aus Verifikationsrahmen wird aktiv.

- **Nicht verifiziert:** Drei Untertypen:

  - teilweise anders (Zugriffslogik anpassbar?)

  - nicht vorhanden (Blocker)

  - grundlegend anders (Architekturbefund)

- Keine stille Anpassung.

- **Unklar:** Zwei Untertypen:

  - methodisch unklar (ergänzende Prüfmassnahme)

  - sachlich unklar (differenzierte Behandlung dokumentieren)

### **R-4 – Folgepfade pro Prüfpunkt**

Detaillierte Folgepfad-Tabellen für Schritt 1 (A-1/V-1), Schritt 2 (A-2/V-2, A-5, A-3/V-3, A-6), Schritt 3 (V-4, V-5, V-6), Schritt 4 (V-7, V-8, V-9, V-10) – jeweils mit Verhalten bei verifiziert / nicht verifiziert / unklar.

### **R-5 – Schwellenwert: Arbeitsstand vs. integrationsreife Präzisierung**

- **R-5.1** Punkt bleibt Arbeitsstand bei Status „unklar" oder ungelöster Abhängigkeit.

- **R-5.2** Bereit für Präzisierungsblock bei: verifiziert + alle Abhängigkeiten verifiziert + Folgefrage benennbar.

- **R-5.3** Grenze wird nie still überschritten.

- **R-5.4** Auch bei vollständig verifiziertem Schritt 1–4 bleibt Gesamtblock Arbeitsentwurf bis explizite Kanonisierungsentscheidung.

### **R-6 – Gesamtauswertungs-Schema**

Nach vollständiger Rückspielung: Anzahl verifiziert/nicht verifiziert/unklar pro Schritt, Blocker-Liste, aktive Folgefragen, präzisierungsreife Punkte, klärungsbedürftige Punkte, Kompatibilitätsaussage zur bestehenden Zugriffslogik. Als eigenständiger Arbeitsstand erzeugt.

### **R-7 – Bewusst offen gehaltene Punkte**

Format des Auswertungsblocks, Zwischen-Auswertungsblöcke bei Teilrückspielung, Befunde die andere Schnittstellen betreffen, Dokumentation von Architektur-Anpassungsbedarf.

## **ARBEITSBLOCK – SCHNITTSTELLE 6 – OPERATIVE DURCHFÜHRUNGSVORLAGE SHAMELA-IST-AUFNAHME**

**Status:** Operatives Hilfsdokument. Kein Kanon. Keine Architekturänderung. Keine Einarbeitung in Dokument 1 oder Dokument 2.

(Derzeit geparkt.)

### **Durchführungsanleitung**

Schritt-für-Schritt-Anleitung (Schritt 1–4) für den Prüfer mit echtem Systemzugriff. Pro Schritt: was konkret geöffnet/geprüft wird, was dokumentiert wird, was als genügend gilt, wann „unklar" gesetzt wird. **Grundregel:** nichts schätzen, nichts raten.

### **Erhebungsvorlage**

Kompakte ausfüllbare Vorlage gegliedert nach Schritt 1 / 2 / 3 / 4 mit allen Feldern und Status-Checkboxen (verifiziert / nicht verifiziert / unklar).

### **Rückgabeformat**

Komprimiertes Format für Rückgabe an den Co-Pilot: Metadaten → Schritt 1–4 → offene Auffälligkeiten. Nur ausfüllbare Struktur, keine Erklärungstexte.

## **ARBEITSBLOCK – TECHNISCHE ZUGRIFFSSPEZIFIKATION SCHNITTSTELLE 4 – QURʾĀN-SCHNITTSTELLE**

**Status:** Arbeitsentwurf. Noch kein Kanon. Keine Einarbeitung in Dokument 1 oder Dokument 2. Kein Code. Keine CRs. Keine stillen Architekturänderungen.

### **Q4-1 – Quellenstruktur und Zugriffspfade**

#### **Q4-1.1 – Primärquelle**

- **API:** quranenc.com

- **Base-URL:** https://quranenc.com/api/v1/

- **Authentifizierung:** Keine dokumentiert. Die API ist nach aktuellem Stand öffentlich zugänglich ohne API-Key oder Token.

- **Translation-Key für Deutsch:** german_rwwad (Rowwad Translation Center)

- **HTTP-Methode:** GET

- **Protokoll:** HTTPS

#### **Q4-1.2 – Relevante Endpunkte (aus öffentlicher API-Dokumentation verifiziert)**

**Endpunkt 1 – Einzelvers:** GET /translation/aya/{translation_key}/{sura_number}/{aya_number}

- Eingabe: translation_key (z. B. german_rwwad), sura_number (1–114), aya_number (1–n)

- Rückgabe: JSON-Objekt mit Feldern sura, aya, translation, footnotes

**Endpunkt 2 – Ganze Sure:** GET /translation/sura/{translation_key}/{sura_number}

- Eingabe: translation_key, sura_number (1–114)

- Rückgabe: JSON-Array, jedes Element mit sura, aya, translation, footnotes

**Endpunkt 3 – Verfügbare Übersetzungen:** GET /translations/list/\[\[{language}\]\]/?localization={language_iso_code}

- Rückgabe: JSON-Array mit key, language_iso_code, version, last_update, title, description

- Verwendung: Versionsprüfung der german_rwwad-Übersetzung beim wöchentlichen Abgleich.

#### **Q4-1.3 – Kritischer Befund: Arabischer Referenztext**

Die quranenc.com-API liefert nach dokumentiertem Stand nur Übersetzungen (Felder: translation, footnotes), nicht den arabischen Originaltext mit Vokalisierung.

§4.15 definiert quranenc.com als alleinigen Textträger für arabischen Referenztext, Vokalisierung und deutsche Übersetzung. Da die API den arabischen Text offenbar nicht liefert, ergeben sich zwei mögliche Auflösungen:

- **Variante A:** Der arabische Referenztext und die Vokalisierung kommen immer aus der lokalen Fallback-Kopie (die gemäss Endfassung 3 Punkt 5 den vollständigen Datenstand enthält). Die API liefert nur die deutsche Übersetzung. Die lokale Kopie ist damit nicht nur Fallback, sondern primärer Träger des arabischen Textes.

- **Variante B:** Es gibt einen nicht dokumentierten oder separaten Endpunkt für den arabischen Qurʾān-Text bei quranenc.com.

**Status dieses Befunds:** Durch den kanonischen Stand in Dokument 1 §4.15 geschlossen. Variante A ist kanonisiert. Der arabische Referenztext (inkl. Vokalisierung) wird aus dem arabischen Qurʾān-Referenzbestand bezogen, der ein eigenständiger lokaler Bestand ist und zu keinem Zeitpunkt über quranenc.com oder eine andere API bedient wird. Die Frage eines separaten arabischen API-Endpunkts (Variante B) ist damit nicht mehr relevant. Keine Arbeitshypothese mehr.

#### **Q4-1.4 – Lokaler Fallback**

Zwei getrennte lokale Bestände (kanonisch §4.15):

**(a) Lokale Fallback-Kopie(n) der Übersetzung:** Vollständige lokale Kopie der german_rwwad-Übersetzung. Fallback für die deutsche Übersetzung bei quranenc.com-API-Ausfall. Muss mindestens umfassen:

- alle 114 Suren und Āyāt

- deutsche Übersetzung (german_rwwad)

- Fussnoten (soweit in german_rwwad vorhanden)

- Versionskennung der german_rwwad-Übersetzung

- Datum des letzten Abgleichs

Analoges gilt für die lokale Fallback-Kopie der englischen Qurʾān-Übersetzung gemäss §4.15; konkreter Translation-Key offen.

**(b) Arabischer Qurʾān-Referenzbestand:** Eigenständiger lokaler Bestand mit vokalisiertem arabischem Qurʾān-Text (ʿUthmānische Schreibweise). Alleiniger Textträger für arabischen Referenztext und Vokalisierung (§4.15). Zielsprachenunabhängig. Nicht API-gestützt. Unabhängig von den Übersetzungs-Fallback-Kopien. Konkrete Quellenbenennung, Datenformat, Speicherort und Update-Mechanismus offen.

### **Q4-2 – Zugriffspfad je Auslöser**

#### **Q4-2.1 – Auslöser A: OCR-Stufe 1 (Visuelle Struktur-Analyse)**

- **Aktion:** Block wird als potenzieller Qurʾān-Block vorgemerkt.

- **Zugriff:** Kein Datenzugriff. Kein API-Ruf. Kein lokaler Lookup.

- **Output:** Blocklabel „Qurʾān-Kandidat" an Block-UUID.

- Kein externer Ruf in der OCR-Phase (kanonisch bestätigt §4.15).

#### **Q4-2.2 – Auslöser B: OCR-Stufe 5 (Qualitätsprüfung)**

- **Aktion:** Lokales Matching des OCR-Textes gegen die lokale Qurʾān-Kopie.

- **Zugriff:** Nur lokal. Kein API-Ruf.

- **Matching-Logik:** OCR-Textfragment wird gegen den arabischen Qurʾān-Referenzbestand (§4.15) gesucht. Bei Treffer: Sure, Āya-Start, Āya-Ende, Match-Konfidenz werden als Vers-Metadaten an Block-UUID gespeichert.

- **Output:** Vers-Metadaten (Sure, Āya-Range, Konfidenz) oder kein Match.

- Konfidenzschwelle für automatische Akzeptanz: Noch offen.

#### **Q4-2.3 – Auslöser C: Übersetzungsphase**

- **Aktion:** Erster und einziger externer API-Ruf.

- **Voraussetzung:** Qurʾān-Erkennung aus Stufe 5 liegt vor und ist akzeptiert (automatisch oder manuell bestätigt).

- **Zugriff:** API-Ruf an quranenc.com.

- **Primärer Endpunkt:** Einzelvers (/translation/aya/german_rwwad/{sura}/{aya}) pro Āya im erkannten Bereich. Bei zusammenhängenden Bereichen alternativ Suren-Endpunkt (/translation/sura/german_rwwad/{sura}) und lokale Filterung auf den relevanten Āya-Bereich.

- **Rückgabe verarbeiten:**

  - translation-Feld = deutsche Übersetzung.

  - footnotes-Feld = Fussnoten.

  - sura/aya-Felder = Verifikation gegen lokale Metadaten.

- **Arabischer Referenztext:** Aus dem arabischen Qurʾān-Referenzbestand (§4.15, kanonisch alleiniger Textträger, nicht API-gestützt).

- **Fallback bei API-Ausfall:** Stiller Wechsel auf lokale Kopie für deutsche Übersetzung. Log-Eintrag im Projekt-Protokoll. Fallback-Indikator an der Stelle setzen. Kein Nutzer-Popup bei Fallback – nur Protokolleintrag.

### **Q4-3 – Timeout / Retry / Ausfallbehandlung**

#### **Q4-3.1 – API-Timeout**

Noch offen: Konkreter Timeout-Wert nicht festlegbar ohne Latenzmessung. **Arbeitshypothese:** 10 Sekunden pro Request als Ausgangswert, nach realer Messung anpassbar.

#### **Q4-3.2 – Retry-Logik**

- 1× automatischer Retry bei Timeout oder HTTP-5xx-Fehler.

- Kein Retry bei HTTP-4xx (Client-Fehler = strukturelles Problem).

- Zwischen Erstversuch und Retry: kurze Pause (Arbeitshypothese 2 Sekunden).

#### **Q4-3.3 – Ausfallbehandlung**

| **Situation** | **Verhalten** |
|----|----|
| API-Timeout nach Retry | Stiller Fallback auf lokale Kopie. Log-Eintrag. Fallback-Indikator. |
| HTTP 404 (Vers nicht gefunden), lokal vorhanden | Fallback auf lokale Kopie. Log-Eintrag. Fallback-Indikator. Zusätzlicher Auffälligkeitsmarker: API und lokaler Bestand divergieren möglicherweise. |
| HTTP 404 (Vers nicht gefunden), lokal ebenfalls nicht vorhanden | Warn-Icon an der Stelle. Log-Eintrag. Manuelle Klärung durch Nutzer erforderlich. |
| HTTP 4xx (anderer Client-Fehler) | Log-Eintrag. Stelle markiert. Kein Retry. |
| HTTP 5xx nach Retry | Stiller Fallback auf lokale Kopie. Log-Eintrag. Fallback-Indikator. |
| Lokale Kopie ebenfalls nicht verfügbar | Warn-Icon. Log-Eintrag. Stelle blockiert bis Klärung. |
| Netzwerkfehler (DNS, TLS) | Wie API-Timeout behandeln. |

#### **Q4-3.4 – Kein Nutzer-Interrupt bei Fallback**

Der Fallback auf die lokale Kopie unterbricht den Übersetzungsflow nicht. Der Nutzer wird nicht aktiv informiert (kein Modal, kein Toast). Die Information ist im Projekt-Protokoll und über den Fallback-Indikator an der betroffenen Stelle nachvollziehbar.

### **Q4-4 – Fehlerklassen und Zuordnung zu §4.18**

| **Fehlertyp** | **Klasse (§4.18)** | **Behandlung** |
|----|----|----|
| API-Timeout / HTTP 5xx | Klasse B (externer Fehler) | Retry → Fallback → Protokoll |
| HTTP 404 Vers nicht gefunden | Klasse B (externer Fehler) | Fallback lokal wenn vorhanden → Protokoll + Auffälligkeitsmarker |
| Lokale Kopie korrupt / fehlend | Klasse C (systembehebbar) | Blockade → technische Wiederherstellung |
| Matching-Fehler (falscher Vers erkannt) | Klasse A (Nutzerfehler/Datenfehler) | Nutzer korrigiert im Review |
| Konfidenz unter Schwelle | Kein Fehler | Normaler Flow → manuelle Bestätigung |

**Benachrichtigungskanal für Klasse-B-Fehler:** aggregierte Nutzerinformation über Dashboard-Statusindikator bei Häufung gemäss §4.18 Spur 2 (kanonisch). Bereits kanonisierte Spezialfälle mit eigener Regel bleiben unberührt:

- Übersetzungs-KI-30-Min-Regel §3.6

- Qurʾān-Fallback-Log ohne Nutzer-Interrupt §4.15 / Q4-3.4

- Guard-nahe Blockaden §4.7

Konkrete Häufungsschwellenwerte live-messungsabhängig.

### **Q4-5 – Logging / Protokollierung / Provenienz**

#### **Q4-5.1 – Pro Qurʾān-Stelle im Projekt protokolliert**

- Sure / Āya-Range

- Arabischer Referenztext-Quelle: arabischer Qurʾān-Referenzbestand (§4.15, kanonisch alleiniger Textträger, nicht API-gestützt)

- Übersetzungsquelle: quranenc.com-API oder lokale Fallback-Kopie der Übersetzung

- Übersetzungsversion (german_rwwad-Version aus /translations/list; analog für die englische Qurʾān-Übersetzung gemäss §4.15)

- Fallback-Indikator Übersetzung (ja/nein)

- Konfidenz der Erkennung (aus OCR-Stufe 5)

- **Stellenzustand:** akzeptiert als Qurʾān-Stelle ODER abgelehnt als Qurʾān-Stelle (nicht als Qurʾān behandelt). Nur akzeptierte Stellen erhalten die hier genannten Qurʾān-Trägerfelder (Quellen, Übersetzungsversion, Fallback-Indikator). Abgelehnte Stellen werden als eigenständiger Stellenzustand mit Zeitstempel und decision_event_uuid dokumentiert und führen keine Qurʾān-Trägerfelder.

- **Akzeptanzweg** (nur bei akzeptierten Stellen):

  - automatisch akzeptiert (Konfidenz über Schwellenwert)

  - manuell bestätigt (Konfidenz unter Schwellenwert, Nutzerbestätigung der System-Vorschlag-Zuordnung)

  - manuell korrigiert (Nutzer ändert Sure/Āya-Zuordnung gegenüber dem System-Vorschlag)

- Bei ausdrücklicher Nutzeraktion zur Aktualisierung einer bereits gespeicherten Qurʾān-Stelle nach Update des arabischen Qurʾān-Referenzbestands oder der lokalen Fallback-Kopie der Übersetzung gemäss §4.15 wird der Akzeptanzweg-Wert der aktualisierten Stelle gemäss neuem Zustand gesetzt; die Aktualisierung selbst wird über das decision_event protokolliert.

- Zeitstempel des API-Rufs oder Fallback-Zugriffs

- decision_event_uuid gemäss kanonischer Handlungstypen-Matrix §4.15: translation_pipeline bei manueller Bestätigung und bei ausdrücklicher Nutzeraktion zur Aktualisierung einer bereits gespeicherten Qurʾān-Stelle; conflict_resolution bei Korrektur und Ablehnung. Kein decision_event bei automatischer Akzeptanz.

#### **Q4-5.2 – Systemweit protokolliert**

- API-Ausfälle mit Zeitstempel und HTTP-Status

- Fallback-Aktivierungen

- Wöchentliche Abgleich-Ergebnisse (Versionsänderung ja/nein)

### **Q4-6 – Versionierung der lokalen Fallback-Kopie**

#### **Q4-6.1 – Wöchentlicher automatischer Abgleich**

Waraq ruft wöchentlich den Endpunkt /translations/list/de ab. Aus der Antwort wird das Objekt mit key: "german_rwwad" extrahiert. Felder version und last_update werden mit dem lokal gespeicherten Stand verglichen.

#### **Q4-6.2 – Bei erkannter Versionsänderung**

- Neuer Vollabzug der german_rwwad-Übersetzung wird heruntergeladen (alle 114 Suren via Suren-Endpunkt).

- Alter Stand wird archiviert (nicht überschrieben).

- Neuer Stand wird als aktive lokale Kopie markiert.

- Protokolleintrag mit alter und neuer Version.

#### **Q4-6.3 – Schutz bestehender Projektstellen (kanonisch §4.15)**

Bereits in Projekten gespeicherte Qurʾān-Stellen bleiben bei Änderung der lokalen Fallback-Kopie unverändert. Kein automatischer Re-Abruf. Kein stilles Überschreiben. Die Stelle trägt die Versionskennung, mit der sie erzeugt wurde. Erst bei expliziter Nutzeraktion (z. B. „Vers aktualisieren") wird die Stelle gegen die aktuelle Kopie geprüft.

#### **Q4-6.4 – Arabischer Text bei Updates**

Der arabische Qurʾān-Referenzbestand ist kanonisch (§4.15) nicht Teil des quranenc.com-API-Abgleichs und nicht Teil der wöchentlichen Versionsprüfung der Übersetzungs-Fallback-Kopien. Der Update-Mechanismus für den arabischen Qurʾān-Referenzbestand ist eigenständig zu spezifizieren und bleibt offen.

### **Q4-7 – Konfidenzschwelle und manuelle Bestätigung**

#### **Q4-7.1 – Grundprinzip (kanonisch §4.15)**

Liegt die Konfidenz der Qurʾān-Erkennung unter dem definierten Schwellenwert: manuelle Bestätigung durch den Nutzer vorgelagert. Kein automatischer API-Ruf. Erst nach Bestätigung wird der Vers als erkannt behandelt und der Übersetzungsphasen-Zugriff (Q4-2.3) ausgelöst.

#### **Q4-7.2 – Konkreter Schwellenwert**

Noch offen. Muss nach Testläufen mit realen OCR-Ergebnissen festgelegt werden. **Arbeitshypothese:** Übernahme der bestehenden OCR-Konfidenzschwellen (85 % für automatische Akzeptanz, darunter manuelle Bestätigung). Keine stille Festlegung.

#### **Q4-7.3 – Nutzerinteraktion bei manueller Bestätigung**

**Nutzer sieht:** OCR-Textfragment, vorgeschlagene Sure/Āya, Konfidenzwert.

**Nutzerhandlungstypen** gemäss kanonischer Matrix §4.15:

- **Bestätigen** → decision_source = translation_pipeline (Akzeptanzweg: manuell bestätigt)

- **Korrigieren** (andere Sure/Āya) → decision_source = conflict_resolution (Akzeptanzweg: manuell korrigiert)

- **Ablehnen** (nicht als Qurʾān) → decision_source = conflict_resolution (kein akzeptierter Qurʾān-Stellenzustand; eigenständiger Stellenzustand gemäss Q4-5.1)

Jede dieser Aktionen erzeugt ein decision_event. Automatische Akzeptanz bei Konfidenz über Schwellenwert erzeugt kein decision_event. Die vierte Handlung der Matrix (ausdrückliche Nutzeraktion zur Aktualisierung einer bereits gespeicherten Qurʾān-Stelle) wird nicht in diesem Dialog, sondern über den in Q4-6.3 beschriebenen Aktualisierungspfad ausgelöst und mit decision_source = translation_pipeline protokolliert.

### **Q4-8 – Verknüpfung mit internen Objekten**

- **Block-UUID:** Träger der Blockklasse „Qurʾān" und der Vers-Metadaten aus OCR-Stufe 5.

- **Satz-UUID:** Träger der kanonischen Ausgabe (arabischer Text + deutsche Übersetzung).

- **Quellenattribute:** Sure, Āya-Range, Quellen-Kennung (API/Fallback), Fallback-Indikator, Übersetzungsversion.

- **Decision-Event-UUID:** Gemäss kanonischer Handlungstypen-Matrix §4.15. decision_source-Zuordnung: translation_pipeline bei manueller Bestätigung und bei ausdrücklicher Nutzeraktion zur Aktualisierung einer bereits gespeicherten Qurʾān-Stelle; conflict_resolution bei Korrektur und bei Ablehnung. Kein decision_event bei automatischer Akzeptanz.

### **Q4-9 – Explizite Liste offener Punkte**

1.  **Arabischer Referenztext über API** → GESCHLOSSEN durch §4.15 (Variante A kanonisch; arabischer Qurʾān-Referenzbestand eigenständig lokal, nicht API-gestützt).

2.  **Konkreter Konfidenz-Schwellenwert** → offen (Live-Test nach realen OCR-Ergebnissen).

3.  **Konkreter Timeout-Wert** → offen (Live-Messung, konservatives Anfrageprofil §3.5).

4.  **Rate-Limit** → offen (Live-Test).

5.  **Update-Mechanismus arabischer Qurʾān-Referenzbestand** → offen (§4.15).

6.  **Englische Qurʾān-Übersetzung** → GESCHLOSSEN durch §4.15 (quranenc.com primär mit Translation-Key english_rwwad; lokale Fallback-Kopie der englischen Qurʾān-Übersetzung analog deutscher Strang).

7.  **Versionierung german_rwwad im Detail** → offen (Designfrage Vergleichsmechanismus Versionsstring/Timestamp).

8.  **Benachrichtigungskanal Klasse B** → GESCHLOSSEN durch §4.18 Spur 2 Dashboard-Aggregation.

9.  **Datenformat und Speicherort der beiden lokalen Bestände:**

    - \(a\) arabischer Qurʾān-Referenzbestand → offen.

    - \(b\) lokale Fallback-Kopie(n) der Qurʾān-Übersetzung(en) (Deutsch und Englisch) → offen.

10. **Quellenangabe-Format im Export** → offen (nachgelagerte Designfrage).

**Qurʾān-Stellenbehandlung / decision_source-Matrix** → GESCHLOSSEN durch §4.15.

## **ARBEITSBLOCK – TECHNISCHE ZUGRIFFSSPEZIFIKATION SCHNITTSTELLE 5 – HADITH-SCHNITTSTELLE**

**Status:** Arbeitsentwurf. Noch kein Kanon. Keine Einarbeitung in Dokument 1 oder Dokument 2. Kein Code. Keine CRs. Keine stillen Architekturänderungen.

**Kanonische Grundlage:** §4.16 Dokument 1. **Fachliche Grundlage:** Endfassung 4 (Block 3).

Fünf Teilbereiche aus der Hadith-Integration kanonisiert (Quellenstruktur, Konsenslogik, Kutub-as-Sitta, decision_event-Zuordnung, Vokalisierungsprinzip). Konsolidierungsstand der erweiterten Hadith-Quellenmenge eingearbeitet. Hadith-Verifikationssemantik und Datenmodell kanonisiert (Vokalisierungs-Eskalationskriterium, Hadith-Verifikationsstatus, Gate-Verortung, Datenmodell). Dieser Arbeitsblock präzisiert die technische Zugriffsschicht, ohne die kanonisierten fachlichen Entscheidungen zu verändern.

### **H5-1 – Quellenstruktur und Zugriffspfade**

#### **H5-1.1 – Pflichtmenge (bei jedem Hadith-Verifikationslauf vollständig durchsucht)**

##### **Quelle P-1: sunnah.com**

- **Zugriffstyp:** API (extern)

- **Base-URL:** https://api.sunnah.com/v1/

- **Authentifizierung:** API-Key erforderlich (Header X-API-Key). Key wird durch Erstellen eines GitHub-Issue auf dem Repository sunnah-com/api angefragt (Template „Request for API access"). Kostenlos. Kein Self-Service – Key wird manuell durch das sunnah.com-Team vergeben. Bearbeitungszeit nicht garantiert. Key muss vor Implementierung aktiv angefragt und serverseitig gespeichert werden. Zeitlicher Vorlauf einplanen.

- **HTTP-Methode:** GET

- **Protokoll:** HTTPS

- **Sprache:** Arabisch und englische Übersetzungen verfügbar. Deutsche Übersetzung: nach Vorverifikation nicht Teil des API-Bestands (geschlossener Befund).

- **Primäre Datenstruktur:** Sammlungen (collections) → Bücher (books) → Kapitel (chapters) → Hadithe (hadiths).

- **Offizielle API-Spezifikation:** OpenAPI v1.0, öffentlich einsehbar unter github.com/sunnah-com/api/blob/master/spec.v1.yml.

**Verifizierte Endpunkte (aus OpenAPI-Spezifikation v1.0):**

- GET /collections – Alle verfügbaren Sammlungen

- GET /collections/{collectionName} – Einzelne Sammlung

- GET /collections/{collectionName}/books – Bücher einer Sammlung

- GET /collections/{collectionName}/books/{bookNumber} – Einzelnes Buch

- GET /collections/{collectionName}/books/{bookNumber}/chapters – Kapitel eines Buchs

- GET /collections/{collectionName}/books/{bookNumber}/hadiths – Hadithe eines Buchs

- GET /collections/{collectionName}/hadiths/{hadithNumber} – Einzelhadith per Sammlung + Nummer

- GET /hadiths – Hadithe mit strukturierten Filtern (collection, bookNumber, chapterId, hadithNumber)

- GET /hadiths/{urn} – Einzelhadith per URN

- GET /hadiths/urns – Mehrere Hadithe per URN-Liste

- GET /hadiths/random – Zufälliger Hadith

**Primärer Suchpfad:** Ausschliesslich strukturierte Lookups über Sammlung + Buch + Hadith-Nummer, URN oder Filterparameter am /hadiths-Endpunkt. Dieser Pfad setzt voraus, dass der Autor eine Quelle nennt oder das lokale Shamela-Matching (OCR-Stufe 5) bereits eine Sammlung/Nummer geliefert hat. Bei fehlender Quellenangabe durch den Autor und fehlendem Shamela-Treffer ist dieser Pfad allein nicht ausreichend – in diesem Fall stützt sich die Pflichtsuche auf die Textsuche der anderen Pflichtquellen (P-2 Shamela Volltextsuche, P-3 dorar.net).

**Geschlossener Befund – Keine Volltextsuche in der offiziellen API:** Die OpenAPI-Spezifikation v1.0 enthält keinen Endpunkt für eine Volltextsuche im Matn oder Isnād. Der /hadiths-Endpunkt akzeptiert ausschliesslich strukturierte Filterparameter (collection, bookNumber, chapterId, hadithNumber). Keiner dieser Parameter erlaubt eine Textsuche. Die sunnah.com-Website bietet zwar eine Volltextsuche (mit Wildcards, Fuzzy Search, Boolean Operators), diese Suchfunktion ist jedoch nicht über die offizielle API exponiert. Die frühere Arbeitshypothese eines Endpunkts GET /hadiths?q={query} ist damit widerlegt. Kein offener Punkt mehr.

**Hadith-Response-Struktur (aus OpenAPI-Spec verifiziert):** Jedes Hadith-Objekt enthält: collection (String), bookNumber (String), chapterId (String), hadithNumber (String), hadith (Array mit sprachspezifischen Objekten). Jedes sprachspezifische Objekt enthält: lang (String, z. B. en, ar), chapterNumber, chapterTitle, urn (Integer), body (String, Hadith-Text in HTML-Markup), grades (Array mit Bewertungen: graded_by + grade).

**Body-Format:** Der body-Text enthält HTML-Markup (z. B. \<p\>-Tags). Für den Vergleich mit OCR-Text muss HTML-Stripping bei der Ergebnisverarbeitung vorgesehen werden.

**Authentizitätsgrad:** Das grades-Feld ist als Array mit graded_by (String) + grade (String) strukturiert. Mehrere Bewertungen pro Hadith sind möglich. Ob das Feld bei allen Hadithen konsistent gefüllt ist, erfordert Testbetrieb mit realem API-Key.

**Paginierung:** Alle Listen-Endpunkte unterstützen limit (max 100, default 50) und page (default 1). Response enthält total, limit, previous, next.

**Sammlungsabdeckung (aus Entwicklerseite verifiziert):**

- **Kutub as-Sitta (alle 6):** Sahih al-Bukhari, Sahih Muslim, Sunan an-Nasa'i, Sunan Abi Dawud, Jami\` at-Tirmidhi, Sunan Ibn Majah.

- **Weitere verifizierte Sammlungen:** Muwatta Malik, Musnad Ahmad, Sunan ad-Darimi, An-Nawawi's 40 Hadith, Riyad as-Salihin, Al-Adab Al-Mufrad, Ash-Shama'il Al-Muhammadiyah, Mishkat al-Masabih, Bulugh al-Maram, Collections of Forty, Hisn al-Muslim.

- **Nicht gelistet:** Al-Mustadrak (al-Hakim), Majma' az-Zawa'id. Ob weitere, nicht auf der Website gelistete Sammlungen verfügbar sind, muss per API-Abfrage (GET /collections) mit realem Key verifiziert werden.

**Rate-Limit:** In der OpenAPI-Spezifikation nicht dokumentiert. Ob ein undokumentiertes Limit existiert, ist ohne Testbetrieb nicht feststellbar. Konservatives Anfrageverhalten empfohlen.

##### **Quelle P-2: Shamela (<span dir="rtl">مكتبة الشاملة</span>) – lokal**

- **Zugriffstyp:** Lokal (serverseitig)

- **Technische Zugriffsschicht:** Vollständig in Schnittstelle 6 spezifiziert (Arbeitsblöcke T6-1 bis T6-6, Verifikationsrahmen, Prüfprotokoll). Schnittstelle 5 nutzt dieselbe technische Zugriffsschicht wie Schnittstelle 6, aber in einem eigenen funktionalen Modus.

- **Funktionaler Modus für Hadith:** Shamela wird im Hadith-Kontext als Verifikationsquelle durchsucht – nicht als Lexikonquelle (das ist Schnittstelle 6 / Modus B). Die Suche läuft über den Gesamtbestand (nicht nur Lisān/Tāj), gezielt nach Hadith-Sammlungen und Werken mit Hadith-Bezug.

- **Suchraum:** Primär Hadith-Sammlungen innerhalb Shamela (Kutub as-Sitta, Musnad Ahmad, Muwatta, Sunan ad-Darimi, al-Mustadrak, Majmaʿ az-Zawāʾid etc.). Sekundär: Gesamtbestand bei erweiterter Suche.

- **Abhängigkeit:** Technische Verfügbarkeit und Suchfähigkeit hängen von der realen Shamela-Ist-Aufnahme ab (Schnittstelle 6, derzeit geparkt). Bis dahin: Arbeitshypothese, dass Shamela volltextsuchbar ist und Hadith-Sammlungen als identifizierbare Werke vorliegen.

**Abgrenzung zu Schnittstelle 6:** Schnittstelle 6 definiert den generischen Zugriffsmechanismus auf Shamela (Datenformat, Suchfähigkeit, Indizierung). Schnittstelle 5 definiert den hadith-spezifischen Suchpfad, Suchraum und Ergebnisverarbeitung. Keine Doppelspezifikation der technischen Grundschicht.

##### **Quelle P-3: dorar.net (<span dir="rtl">الدُّرَرُ السَّنِيَّة</span>)**

- **Zugriffstyp:** API-priorisiert. Scraping als sekundärer Rückfallpfad.

- **Base-URL:** https://dorar.net/

- **Authentifizierung:** Keine dokumentiert. Öffentlich zugänglich.

- **Protokoll:** HTTPS

**API-Zugang (primär):** dorar.net stellt einen offiziellen API-Dienst für die Hadith-Enzyklopädie (<span dir="rtl">الموسوعة الحديثية</span>) bereit. Die Existenz des API-Dienstes ist offiziell dokumentiert auf der dorar.net-Seite „<span dir="rtl">خدمة واجهة الموسوعة الحديثية</span> API", die den Dienst beschreibt und Nutzungsbeispiele (JavaScript) enthält. Der Dienst stellt Suchergebnisse per JSON bereit. Auf der offiziellen Seite wird ein JSONP-Nutzungsbeispiel für den clientseitigen JavaScript-Zugriff gezeigt – dies bedeutet nicht, dass die API grundsätzlich oder ausschliesslich JSONP-basiert ist. Bei serverseitigem Zugriff (wie bei Waraq) sind Standard-HTTP-Anfragen mit JSON-Response der zu erwartende Normalfall.

Die tiefere technische Spezifikation (exakte Endpunkt-URLs, vollständige Parameterliste, Response-Parsing-Details, Versionierung) ist auf der offiziellen Seite nicht erschöpfend dokumentiert. Die detaillierteste verfügbare Dokumentation stammt aus einem Open-Source-Drittanbieter-Proxy (dorar-hadith-api, MIT-Lizenz, github.com/AhmedElTabarani/dorar-hadith-api). Dieser Proxy unterscheidet explizit zwischen dem API-Pfad (offizielle dorar-API) und dem Site-Pfad (Website-Scraping) und dient als Reverse-Engineering-Grundlage für die Endpunkt- und Parameterspezifikation.

**Verifizierte Fähigkeiten** (offiziell dokumentiert: Grundlagen; praktisch beobachtbar: Details):

- Textsuche im Matn (arabisch)

- Filterung nach Sammlung/Werk (über Buch-ID-Parameter)

- Filterung nach Muhaddith (über Muhaddith-ID-Parameter)

- Filterung nach Überlieferer (über Rawi-ID-Parameter)

- Filterung nach Authentizitätsgrad (über Grad-Parameter)

- Rückgabe von Takhrij (Verweis auf andere Sammlungen)

- Rückgabe von Authentizitätsgrad (grade) und Erläuterung (explainGrade)

- JSON-Response

**Response-Felder** (aus Drittanbieter-Proxy-Dokumentation, praktisch beobachtbar): hadith (Matn, HTML-Markup), rawi, mohdith/mohdithId, book/bookId, numberOrPage, grade, explainGrade, takhrij, hadithId, hasSimilarHadith, hasAlternateHadithSahih, hasUsulHadith.

**Body-Format:** Hadith-Texte werden in HTML-Markup geliefert. HTML-Stripping ist bei der Ergebnisverarbeitung erforderlich.

**Scraping-Zugang (sekundär, nur als Rückfallpfad):** Falls der API-Zugang nicht den vollen benötigten Funktionsumfang abdeckt, nicht stabil nutzbar ist oder einzelne Suchmodi nicht unterstützt, kann die dorar.net-Suchmaske per Scraping (Playwright) als sekundärer Zugriffspfad genutzt werden. Dieser Pfad unterliegt den allgemeinen Scraping-Stabilitätsregeln (H5-11), greift aber nur, wenn der API-Pfad für die konkrete Anfrage nicht ausreicht. Der Scraping-Pfad liefert teilweise andere/zusätzliche Felder (z. B. thematische Kategorien).

**Sammlungsabdeckung:** Die dorar.net-Hadith-Enzyklopädie deckt einen breiten Bestand ab, der über die Kutub as-Sitta hinausgeht. Die vollständige Auflistung aller durchsuchbaren Bücher und Muhaddithun ist über Filterlisten des Drittanbieter-Proxys dokumentiert. Exakte Abgleichung gegen den Waraq-Bedarf erfordert Inspektion dieser Listen.

**Kritische Befunde:**

- **Befund 1 – Tiefere Endpunkt-Spezifikation:** Exakte Endpunkt-URLs und Parameter-Kodierung der Original-API (nicht des Proxys) müssen vor Implementierung durch Inspektion der dorar.net-Netzwerkanfragen (Browser-DevTools) oder Analyse des Proxy-Quellcodes verifiziert werden.

- **Befund 2 – Rate-Limit:** Nicht dokumentiert. Muss durch vorsichtigen Testbetrieb ermittelt werden. Konservatives Anfrageverhalten bis zur Klärung.

- **Befund 3 – Stabilität:** Da die API nicht offiziell versioniert ist und die tiefere Spezifikation nicht erschöpfend dokumentiert ist, gibt es keine Stabilitätsgarantie. Endpunkte, Parameter und Response-Formate können sich ohne Vorankündigung ändern. Ein Monitoring-Mechanismus für Endpunkt-Verfügbarkeit und Response-Konsistenz muss vorgesehen werden.

- **Befund 4 – Harakāt-Sensitivität:** Ob die Textsuche Harakāt-insensitiv arbeitet, ist aus der verfügbaren Dokumentation nicht ablesbar und erfordert Testbetrieb.

#### **H5-1.2 – Erweiterte Menge (Konsolidierungsstand der erweiterten Hadith-Quellenmenge massgeblich)**

- **Quelle E-1: islamweb.net** – Option B faktisch suspendiert. Web-Scraping-Kandidat ohne API. Siehe Block-3-Vorverifikation.

- **Quelle E-2: <span dir="rtl">جامع السنة النبوية</span>** (Alifta-/Harf-Variante) – Option B faktisch suspendiert. Keine API. Scraping-Kandidat auf Regierungsinfrastruktur.

- **Quelle E-3: <span dir="rtl">المكتبة الوقفية</span>** – Option B faktisch suspendiert. Nur noch als mögliche manuelle Referenzquelle geführt.

- **Quelle E-4: <span dir="rtl">جَامِعُ الكُتُبِ التِّسْعَة</span>** (Arabia-IT) – Option B faktisch suspendiert. Nur Mobile App, keine Web-/API-Integration.

- **Quelle E-5: <span dir="rtl">مَوْسُوعَةُ الأَحَادِيثِ النَّبَوِيَّة</span>** (hadeethenc.com) – Option B nicht suspendiert. Sonderrolle „deutsche Übersetzungsquelle / mehrsprachige Referenzquelle". Offizielle API, Bulk-Downloads. Kein API-Volltextsuchpfad.

**Ausschluss:** hadithportal.com ausdrücklich ausgeschlossen.

**Eskalationslogik:** Bei automatischer Zuschaltung der erweiterten Menge faktisch ausschliesslich E-5 wirksam, solange E-1–E-4 suspendiert bleiben.

#### **H5-1.3 – Kein lokaler Fallback-Bestand für Hadith (Abgrenzung zu §4.15)**

Anders als bei Qurʾān (§4.15) gibt es für Hadith bewusst keinen alleinigen Textträger und keine vollständige lokale Fallback-Kopie. Die Verifikation ist mehrdimensional und quellenübergreifend. Es gibt keine Situation, in der ein einzelner lokaler Bestand die gesamte Hadith-Verifikation übernehmen könnte.

### **H5-2 – Zugriffspfad je Auslöser**

- **H5-2.1 – Auslöser A (OCR-Stufe 1, Visuelle Struktur-Analyse):** Block wird als potenzieller Hadith-Block vorgemerkt. Kein Datenzugriff, kein externer Ruf.

- **H5-2.2 – Auslöser B (OCR-Stufe 5, Qualitätsprüfung):** Lokales Matching gegen Shamela-Hadith-Bestand (Modus A). Kein externer API-Ruf. Vorläufige Hadith-Metadaten (Werk, Nummer, Matn-Fragment, Konfidenz).

- **H5-2.3 – Auslöser C (Vor Übersetzung, Konfidenzprüfung):** Konfidenz ≥ Schwelle → automatisch an Übersetzungsphasen-Verifikation; Konfidenz \< Schwelle → manuelle Bestätigung; kein OCR-Treffer → direkt in Mehrquellen-Verifikation mit OCR-Rohtext.

- **H5-2.4 – Auslöser D (Übersetzungsphase, Mehrquellen-Verifikation):**

  - Schritt 1 Pflichtsuche P-1/P-2/P-3 parallel.

  - Schritt 2 Pflichtauswertung nach §4.16 Konsenslogik.

  - Schritt 3 Erweiterte Menge automatisch zugeschaltet (faktisch nur E-5 wirksam), manuell auslösbar.

  - Schritt 4 Ergebniszusammenführung; drei Zielausgaben A (Referenz-Matn), B (Referenz-Vokalisierung), C (Provenienz-/Vergleichspaket); lineares Ranking als Tie-Breaker; Kutub-as-Sitta als Gewichtungsfaktor.

### **H5-3 – Timeout / Retry / Ausfallbehandlung**

- **H5-3.1 – Timeout-Werte pro Quelle (alle Arbeitshypothesen):**

  - sunnah.com API: 10 s

  - Shamela lokal: 5 s

  - dorar.net API: 10 s

  - dorar.net Scraping-Rückfall: 15 s

  - islamweb.net / <span dir="rtl">جامع السنة / الوقفية</span> Scraping: je 15 s

  - E-4 / E-5: je nach Zugriffstyp

- **H5-3.2 – Retry-Logik:**

  - API-Quellen 1× Retry bei Timeout/5xx, kein Retry bei 4xx, Pause 2 s.

  - Scraping 1× Retry bei Timeout/Ladefehler, kein Retry bei 4xx/DOM-Bruch, Pause 3 s.

  - Shamela lokal 1× Retry bei DB-Lock/IO, kein Retry bei leerem Ergebnis.

- **H5-3.3 – Ausfallbehandlung:**

  - Einzelquellenausfall → Quelle als ausgefallen markiert, Rest läuft weiter.

  - Alle Pflicht ausgefallen → erweiterte Menge versuchen, dann Warn-Icon und Review.

  - Alle ausgefallen → Gesamt-Verifikationsausfall (N-5, H-2).

- **H5-3.4 – Keine Blockade des Übersetzungsflows:** Hadith-Verifikationsausfälle blockieren Flow nicht. Preflight-Verortung nicht-verifizierter Stellen gemäss §4.16 Hadith-Verifikationsstatus.

### **H5-4 – Suchmodi und Normalisierung**

- **H5-4.1 – Suchmodi:** S-1 exakter Wortlaut, S-2 Teilwortlaut, S-3 Quelle+Wortlaut, S-4 Kurzfassung, S-5 Isnād-Anfang, S-6 normalisierte OCR-Variante, S-7 ohne Harakāt.

- **H5-4.2 – Normalisierung:** Harakāt-Stripping parallel, Tatweel-Entfernung, Hamza-Normalisierung, Alif-Maqsura/Ya-Varianten, Taʾ Marbuta/Hāʾ, OCR-typische Verwechslungen als Varianten.

- **H5-4.3 – Suchstrategie pro Quelle** (wie im ursprünglichen H5-Arbeitsstand beschrieben; sunnah.com nur strukturierte Lookups, Shamela volltextsuchbar innerhalb Werken \[Arbeitshypothese\], dorar.net API-Textsuche mit Filter, erweiterte Scraping-Quellen).

### **H5-5 – Ergebnisobjekt pro Quelle und Gesamtergebnis**

Kanonisiert als Mehrquellen-Datenmodell (vier Ebenen, §4.16 / Kapitel 5). Hier ursprüngliche Feldlisten als Werkbank-Herleitung:

- **H5-5.1 – Einzelquellen-Ergebnisobjekt:** quelle_id, treffer_status, matn_arabisch, matn_vokalisiert, isnad, sammlung, werk_nummer, direktlink, hukm, hukm_quelle, website_uebersetzung, textnaehe, technischer_status, zugriffszeitpunkt. Präzisiert: einzelquelle_uuid, gesamtergebnis_uuid, quellen_rolle Pflicht-Snapshot; website_uebersetzung als Liste von {lang, text}; Enums treffer_status und technischer_status erweitert um quelle_suspendiert / quelle_nicht_durchsucht / http_4xx / http_5xx.

- **H5-5.2 – Gesamtergebnisobjekt:** autorwortlaut, autor_genannte_quelle, referenz_matn, referenz_matn_quelle, referenz_vokalisierung, referenz_vokalisierung_quelle, provenienz_paket, konsens_status, kutub_as_sitta_signal, kutub_as_sitta_abweichung_aktiv, eskalation_ausgefuehrt, ausgefallene_quellen, vokalisierungs_konflikt (strikt binär, Klassen-Differenzierung über abgeleitete vokalisierungsklasse), decision_events. **Abgeleitete Zustände:** entscheidungsstatus, vokalisierungsklasse, hadith_stellen_typ, hadith_verifikationsklasse.

### **H5-6 – Nutzerinteraktion und Konfliktfälle**

- Fall A: Konsens, automatisch.

- Fall B: Autorquelle bestätigt, automatisch.

- Fall C: Autorquellen-Konflikt, drei Nutzeroptionen.

- Fall D: keine Autorquelle, Nutzerentscheidung.

- Fall E: kein Treffer, fünf Nutzeroptionen.

Plus Vokalisierungskonflikt (getrennt bestimmbar, V-2 → Nutzereinbezug).

Alle Handlungen auf die 7 kanonisierten Typen gemäss §4.16 abgebildet.

### **H5-7 – Fehlerklassen und Zuordnung zu §4.18**

Vollständige Fehlertyp-Tabelle wie im ursprünglichen H5-Arbeitsstand; Klasse A/B/C gemäss §4.18. Benachrichtigungskanal Klasse B (L-24) offen.

### **H5-8 – Logging / Protokollierung / Provenienz**

**Pro Hadith-Stelle:** Autorwortlaut, durchsuchte Quellen und Ergebnisse, Referenz-Matn und Quelle, Referenz-Vokalisierung und Quelle, Konsens-Status, Kutub-as-Sitta-Signal, Eskalation, ausgefallene Quellen, Authentizitätsgrad, Website-Übersetzungen, Autorquelle, Vokalisierungskonflikt-Status, decision_events, Einzelquellen-Trefferobjekte.

**Systemweit:** Quellen-Ausfälle, DOM-Brüche, API-Key-Probleme, Häufungsmuster.

### **H5-9 – Verknüpfung mit internen Objekten**

- **Block-UUID:** Blockklasse „Hadith", vorläufige Metadaten.

- **Satz-UUID:** Übersetzungsausgabe.

- **Quellenattribute.**

- **Decision-Event-UUID:** gemäss 7 Handlungstypen.

### **H5-10 – Parallelisierung und Performance**

- Pflichtquellen parallel.

- Erweiterte Menge (effektiv nur E-5) parallel.

- Aggregationspunkt nach allen Pflichtantworten.

- Maximale Wartezeiten (Arbeitshypothesen): Pflicht 20 s, Eskalation 30 s.

### **H5-11 – Scraping-Wartung und Stabilitätssicherung**

Gilt für alle Scraping-Quellen (dorar.net Rückfall, islamweb.net, <span dir="rtl">جامع السنة, الوقفية, موسوعة الأحاديث</span> als Scraping-Fall). DOM-Bruch = Klasse B ohne Retry. Keine stille Selbstheilung.

### **H5-12 – Explizite Liste offener Punkte (Werkbank-Stand, teilweise kanonisiert/geschlossen)**

**Operative Aufgaben:**

- sunnah.com API-Key anfragen

- vollständige Sammlungsliste per API verifizieren

- Authentizitätsgrad-Konsistenz per Testbetrieb

- HTML-Stripping implementieren

- dorar.net Endpunkte reverse-engineeren

- Rate-Limits empirisch ermitteln

- Harakāt-Sensitivität testen

- Monitoring für dorar.net

- Scraping-Selektoren inspizieren

- Konfidenz-Schwellenwerte festlegen

- Timeout-Werte nach Messung

- verbleibende Testbetriebsfragen zu E-5 (siehe eigener E-5-Testbetriebs-Arbeitsblock)

**Geschlossen (Quellenlage der erweiterten Menge):** Quellenlage der erweiterten Menge.

**Geschlossen (Hadith-Verifikationssemantik und Datenmodell):** Vokalisierungs-Eskalationskriterium, Datenmodell Mehrquellen-Ergebnisobjekte, Preflight-Verortung nicht-verifizierter Hadith-Stellen, englischer Strang K-4 R-1/R-2.

**Teil-offen:** englischer Strang K-4 R-3 (Ausgabestrang).

**Weiterhin offen:** Benachrichtigungskanal Klasse B (L-24), reale Shamela-Ist-Aufnahme (P-2-Tragfähigkeit, geparkt).

## **ARBEITSBLOCK – VORVERIFIKATION SCHNITTSTELLE 5 – sunnah.com und dorar.net**

**Status:** Arbeitsentwurf. Noch kein Kanon.

(Inhaltlich vollständig erhalten wie im vorherigen Stand.)

**Kernbefunde:**

- sunnah.com API existiert, Key per GitHub-Issue.

- Keine Volltextsuche.

- Kutub as-Sitta vollständig abgedeckt.

- Musnad Ahmad und Darimi gelistet.

- Al-Mustadrak / Majma' az-Zawa'id nicht gelistet.

- Rate-Limit undokumentiert.

- dorar.net API offiziell dokumentiert, JSON.

- Keine offizielle Volltext-/Endpunkt-Spezifikation.

- Drittanbieter-Proxy als Reverse-Engineering-Grundlage.

- HTML-Stripping erforderlich.

- Rate-Limit undokumentiert.

- Stabilität nicht garantiert.

- Szenario-3-Risikobefund dokumentiert: dorar.net als einzige externe Textsuche bei fehlendem Shamela-Treffer.

## **ARBEITSBLOCK – VORVERIFIKATION SCHNITTSTELLE 5 – islamweb.net**

**Status:** Arbeitsentwurf. Noch kein Kanon. Option B entschieden (faktisch suspendiert).

(Inhaltlich vollständig erhalten.)

**Kernbefunde:**

- Webbasierter Hadith-Zugang nur über Bibliothekssektion.

- Keine API.

- Keine strukturierten Hadith-Objekte.

- Keine webbasierte Takhrij.

- Hoher Implementierungsaufwand bei geringem Mehrwert.

## **ARBEITSBLOCK – IDENTIFIKATION UND TECHNISCHE KLÄRUNG SCHNITTSTELLE 5 – E-2 / „<span dir="rtl">جَامِعُ السُّنَّةِ النَّبَوِيَّة</span>"**

**Status:** Arbeitsentwurf. Noch kein Kanon. Hoch belastbar identifiziert als Alifta-/Harf-Variante, Option B entschieden (faktisch suspendiert).

(Inhaltlich vollständig erhalten.)

**Kernbefunde:**

- Saudi-arabische Rifasa al-Iftaa und ägyptische Harf Company.

- Web-Version sunnah.alifta.gov.sa und www.alifta.net.

- Mobile App.

- Historische Desktop-Version.

- 33 Matn-Bücher und 55–75 Hilfswerke.

- 261'000+ Ahadith.

- Keine API.

- Scraping-Kandidat auf Regierungsinfrastruktur mit Unsicherheiten.

## **ARBEITSBLOCK – VORVERIFIKATION SCHNITTSTELLE 5 – <span dir="rtl">جَامِعُ الكُتُبِ التِّسْعَة</span>**

**Status:** Arbeitsentwurf. Noch kein Kanon. Option B entschieden (faktisch suspendiert).

(Inhaltlich vollständig erhalten.)

**Kernbefunde:**

- Sammelbegriff.

- Aktive Variante Arabia-IT Mobile App iOS/Android ohne Web/API.

- Historische Harf Desktop veraltet.

- Statische PDFs.

- Inhaltliche Redundanz mit Pflichtmenge.

## **ARBEITSBLOCK – VORVERIFIKATION SCHNITTSTELLE 5 – <span dir="rtl">مَوْسُوعَةُ الأَحَادِيثِ النَّبَوِيَّة</span>**

**Status:** Arbeitsentwurf. Noch kein Kanon. Option B entschieden (nicht suspendiert, Sonderrolle „deutsche Übersetzungsquelle / mehrsprachige Referenzquelle").

(Inhaltlich vollständig erhalten.)

**Kernbefunde:**

- hadeethenc.com, IslamHouse-Familie.

- Offizielle REST-API v1 mit fünf Endpunkten, keine Authentifizierung, JSON, HTTPS.

- Keine Volltextsuche über API.

- Offizielle Bulk-Downloads Excel/PDF pro Sprache.

- Kuratierte thematische Enzyklopädie ca. 3000 Einträge in 7 Hauptkategorien.

- Deutsche und englische Übersetzung verfügbar.

- Institutionelle Trägerschaft.

- Strukturelle Parallele zu §4.15 quranenc.com.

## **ARBEITSBLOCK – VOKALISIERUNGS-ESKALATIONSKRITERIUM SCHNITTSTELLE 5 – HADITH**

**Status:** Inhaltlich kanonisiert in §4.16 (Klassen V-0/V-1/V-2, Aggregationsregel, Rückfallregel, vokalisierungs_konflikt strikt binär mit Klassen-Differenzierung über vokalisierungsklasse). Der Block bleibt hier als Herleitungsvolltext mitgetragen. Keine Kanonwirkung aus diesem Block selbst; massgeblich ist §4.16.

(Typologie T-1 bis T-9 mit Relevanzklassen V-0/V-1/V-2, Eskalationsregel, Nutzerinteraktion gemäss 7 Handlungstypen, Restoffenheiten R-1 bis R-10 inhaltlich vollständig erhalten wie in der ursprünglichen Arbeitsfassung.)

## **ARBEITSBLOCK – PREFLIGHT-VERORTUNG NICHT-VERIFIZIERTER HADITH-STELLEN – SCHNITTSTELLE 5**

**Status:** Inhaltlich kanonisiert in §4.16 und §4.7 (Stellentypen N-1 bis N-10, Verifikationsklassen H-0/H-1/H-2, Gate-Verortung als eigene benannte Gruppe innerhalb der Gate-Prüfungsschicht ohne neue Schicht und ohne P-/W-Slot-Belegung, H-2 blockierend, H-1 warnungsbasiert mit go_with_warning analog §4.9 E-1 und decision_source preflight_confirmation). Der Block bleibt hier als Herleitungsvolltext mitgetragen. Keine Kanonwirkung aus diesem Block selbst.

(Typologie N-1 bis N-10 mit Klassenzuordnung H-0/H-1/H-2, Zustandsregel pro Stelle, Nutzerinteraktion, Restoffenheiten R-1 bis R-10 inhaltlich vollständig erhalten wie in der ursprünglichen Arbeitsfassung.)

## **ARBEITSBLOCK – DATENMODELL MEHRQUELLEN-ERGEBNISOBJEKTE – SCHNITTSTELLE 5**

**Status:** Inhaltlich kanonisiert in §4.16 und Kapitel 5 (vier logische Ebenen, quellen_rolle als Pflicht-Snapshot ohne dynamische Rückableitung, abgeleitete Zustände entscheidungsstatus / vokalisierungsklasse / hadith_stellen_typ / hadith_verifikationsklasse, satz_uuid als Pflicht sobald Satzsegmentierung vorhanden, Unveränderlichkeit analog §4.9 E-10). Der Block bleibt hier als Herleitungsvolltext mitgetragen. Keine Kanonwirkung aus diesem Block selbst.

(Vier Ebenen, Einzelquellen-Ergebnisobjekt-Felder, Gesamtergebnisobjekt-Felder, abgeleitete Zustandslogik, Restoffenheiten R-1 bis R-11 inhaltlich vollständig erhalten wie in der ursprünglichen Arbeitsfassung.)

## **ARBEITSBLOCK – E-5 TESTBETRIEB UND TECHNISCHE VERIFIKATION – hadeethenc.com**

**Status:** Arbeitsentwurf. Werkbank. Noch kein Kanon. β-Teilbefunde aus früherem Testbetrieb erhoben (F-1 bis F-16) – kein Kanon, keine Auswirkung auf Dokument 1 oder Dokument 2.

### **β-Befunde (Werkbank-Stand)**

**In β verifiziert:**

- F-1 (nur für AR und EN; Strukturasymmetrie AR vs. Nicht-AR; Feld reference nur in AR)

- F-2 (Harakāt vollständig in AR-Feldern aus API)

- F-3 (kein HTML in JSON-Textfeldern)

- F-8 (Sprachliste 68 Sprachen)

**Teilverifiziert in β:**

- F-6 (Excel-Link für alle 68 Sprachen strukturell belegt; Spaltenumfang/Encoding/Harakāt-Haltung nicht abgedeckt)

- F-7 (PDF nur für 7 Sprachen, kein PDF für Deutsch; Eignungsprüfung lokaler Index nicht abgedeckt)

- F-12 (Website-Übersetzung strukturell belegt; inhaltliche Passung ans Datenmodell nicht vollständig abgedeckt)

- F-15 (deutsche Abdeckung ca. 20–21 % Stichprobe; Qualitätsstichprobe und systematische Abdeckungsmatrix nicht abgedeckt)

**Unklar wegen Tool-Grenze der früheren Testumgebung** (kein Negativbefund ableitbar):

- F-1 DE-API-Direktcall

- F-12 DE-API-Direktcall

- F-13 Fehlverhalten

**Zeitabhängig offen** (nicht simulierbar, realer Testbetrieb erforderlich):

- F-4, F-5, F-9, F-14, F-16

**Keine β-Aussage zu:** F-10, F-11.

### **Offene Testbetriebsfragen F-1 bis F-16**

- **F-1** Feldstruktur /hadeeths/one/ pro Sprache

- **F-2** Harakāt-Rückgabe

- **F-3** HTML-Markup in Response

- **F-4** Rate-Limit

- **F-5** Stabilität und Versionierung

- **F-6** Excel-Bulk (Feldumfang, Encoding, Harakāt)

- **F-7** PDF-Bulk (Eignung lokaler Index)

- **F-8** Sprachliste per API

- **F-9** Versionierungsmechanik

- **F-10** Konsistenz API vs. Bulk-Download

- **F-11** Frontend-Suche als Scraping-Pfad

- **F-12** Website-Übersetzung als Datenmodell-Referenzfeld

- **F-13** Fehlverhalten

- **F-14** Latenzprofil

- **F-15** Deutsche Abdeckung und Qualitätsstichprobe

- **F-16** ID-Stabilität

### **Testplan Prüfblöcke T-1 bis T-8**

Sprachliste, Einzel-Hadith-Feldstruktur, Authentizitätsgrad/Takhrij, Excel-Bulk, PDF-Bulk, Rate-Limit/Stabilität/Latenz, Versionierung/ID-Stabilität, defensive Frontend-Suche.

### **Minimalbedingungen für spätere Kanonisierung**

- F-1 und F-2 mind. differenziert

- F-3 mind. bestätigt/differenziert

- F-8 mind. bestätigt

- F-6 oder F-7 mind. differenziert

- F-4 mind. differenziert

- F-9 mind. differenziert

- F-16 mind. bestätigt

### **Restoffenheiten R-1 bis R-10**

Timeout-Werte, Rate-Limit-Policy, Scraping-Pfad, ID-Instabilität Worst-Case, Bulk-Download-Pipeline, systematische deutsche Vollständigkeitsanalyse, englischer Strang-Verknüpfung, Stilfeature-Abgrenzung, §4.18-Kompatibilität, Datenschutz/Lizenz.

## **ARBEITSBLOCK – ENGLISCHER HADITH-STRANG – SCHNITTSTELLE 5**

**Status:** Inhaltlich teilkanonisiert in §4.16 und §5.1.1 (R-1 Englisch als Referenzfeld / R-2 Englisch als Vergleichssprache). R-3 (Englisch als Ausgabestrang, Waraq-KI als Primärproduzent, Keine-Kaskade-Regel für Hadith, englische Quellenangabe-/Transliterations-/Fussnoten-/Stilfeature-Logik) bleibt Werkbank. Der Block bleibt hier als Herleitungsvolltext mitgetragen.

(Drei Rollen R-1/R-2/R-3, symmetrische Matn-Behandlung, asymmetrische Übersetzungsebene, Nutzerinteraktion pro Projekt-Sprachkombination, Restoffenheiten R-1 bis R-10 inhaltlich vollständig erhalten wie in der ursprünglichen Arbeitsfassung.)

## **ARBEITSBLOCK – REALE SHAMELA-IST-AUFNAHME – SCHNITTSTELLE 6 / HADITH-BEZUG**

**Status:** Arbeitsentwurf. Noch kein Kanon. Geparkt. Wird erst wieder bearbeitet, wenn der Nutzer ausdrücklich wieder aufgreift.

Stufe-S-1-Erwartung für P-2 bleibt Arbeitshypothese; keine stille Hochstufung. Reale Ergebnisse aus Schnittstelle 6 dürfen den Konsolidierungsstand der erweiterten Hadith-Quellenmenge nicht still verändern.

(Methodik mit Vier-Status-Klassifikation, zulässige Annahmen, hadithrelevante Zugriffslage, drei Realisierungsstufen S-1/S-2/S-3, Konsequenzen für H5, Restoffenheiten R-1 bis R-11 inhaltlich vollständig erhalten wie in der ursprünglichen Arbeitsfassung.)

## **ARBEITSBLOCK – SCHNITTSTELLE 5 – LIVE-TESTPAKET (GEPARKT)**

**Status:** Operativer Werkbank-/Hilfsblock. Kein Kanon. Keine Einarbeitung in Dokument 1. Keine Kanonwirkung. Inhalt ist strukturell abschlussreif und wartet ausschliesslich auf die reale externe Ausführung und die Rückspielung eines ausgefüllten Rückgabeformats. Reale Ergebnisse dürfen den bereits kanonisierten Stand (insbesondere A-4 / A-6 / A-7 / A-8, §4.16 E-5-Sonderrolle, §3.5 Modell U, §5.1.1 HTML-Stripping) nicht still verändern; Eintragungen erfolgen erst nach expliziter Freigabe.

### **Zweck**

Schliessen der live- und API-testabhängigen Restpunkte:

- E-5-Testbetriebsfragen F-1 / F-4 / F-9 / F-13 / F-14 / F-16

- F-3 konkrete Werte (Raten, Backoff, Obergrenzen, Wiederaufnahme, Häufungsschwelle §4.18 Spur 2)

- F-4 konkrete Werte (Timeout- und Retry-Werte pro Quelle)

### **Teil 1 – Ausführungsreifer Testlauf-Block**

#### **T-A – E-5-Testbetrieb (hadeethenc.com)**

**Ziel:** Schliessen von F-1, F-4, F-9, F-13, F-14, F-16; Vervollständigung der Teilbefunde zu F-6, F-7, F-12, F-15.

**Vorbedingungen:** offizielle API-Basis-URL bestätigt; keine Authentifizierung erforderlich; stabile Netzwerkverbindung; Prüfzeit und Zeitzone dokumentierbar.

**T-A.1 Sprachliste** GET /languages (oder dokumentierter Äquivalent-Endpunkt). Erhebung: Anzahl Sprachen, ISO-Codes-Liste, Präsenz de und en, Content-Type, Roh-Response (gekürzt).

**T-A.2 Einzel-Hadith-Feldstruktur** (feste Referenz-Hadith-ID)

- A.2.1 AR abrufen

- A.2.2 EN abrufen

- A.2.3 DE abrufen (schliesst F-1 DE)

- A.2.4 weitere Sprache abrufen (Kontrolle Asymmetrie)

Erhebung pro Fall: Feldnamen-Liste, Präsenz/Abwesenheit reference, Harakāt-Haltung im Matn, HTML-Markup ja/nein, grade-Feld Name+Wert, Takhrij-Feld, ID-Schema.

**T-A.3 Authentizitätsgrad und Takhrij** 10 Hadithe aus verschiedenen Kategorien AR. Erhebung: Konsistenz der Feldnamen, Wertebereich grade, Mehrfachbewertungen ja/nein, Takhrij-Strukturierung.

**T-A.4 Bulk-Downloads Feldumfang**

- A.4.1 Excel-Bulk DE: Spaltennamen, Anzahl Zeilen, Encoding, Harakāt-Haltung.

- A.4.2 PDF-Bulk einer Sprache: Feldumfang, Eignung lokaler Index.

**T-A.5 Rate-Limit / Stabilität / Latenz**

- A.5.1 20 sequentielle Requests, 1 s Abstand

- A.5.2 20 Requests Burst

- A.5.3 5 Requests – 10 min Pause – 5 Requests

Erhebung pro Serie: Latenz Min/Max/Median/P95, HTTP-Statuscodes, Rate-Limit-Header, Fehlerquote, Recovery-Verhalten.

**T-A.6 Versionierung / ID-Stabilität**

- A.6.1 10-ID-Set Snapshot erzeugen.

- A.6.2 Nach ≥ 7 Tagen denselben Set erneut abrufen.

Erhebung: Versionsfeld vorhanden, Content-Identität, ID-Stabilität.

**T-A.7 Fehlverhalten**

- A.7.1 Nicht-existierende Hadith-ID

- A.7.2 Falscher Sprachcode

- A.7.3 Malformierter Request-Pfad

Erhebung: HTTP-Statuscode, Response-Body, Timeout-Verhalten.

**T-A.8 Deutsche Abdeckungsmatrix** DE-Hadith-Liste gegen AR-Masterliste (Excel-Bulk oder Listen-Endpunkt). Erhebung: Abdeckungsquote in %, nicht abgedeckte Kategorien.

#### **T-B – Timeout-/Retry-Kalibrierung**

**Ziel:** Kalibrierte Timeout- und Retry-Werte pro externer Quelle.

**T-B.1 Latenzprofil pro Quelle** (20 sequentielle Abrufe; 10 bei Scraping): sunnah.com, dorar.net API, dorar.net Scraping, E-5 (aus A.5.1), islamweb.net, <span dir="rtl">جامع السنة, الوقفية</span>, Shamela lokal. Erhebung: Min, Max, Median, P95.

**T-B.2 Stabilität 24 h pro Quelle** (100 Abrufe verteilt). Erhebung: Ausreisserquote \> 3× Median, Timeout-Rate, Tageszeitmuster.

**T-B.3 Retry-Verhalten pro Quelle** (10 kontrollierte Fehler-Szenarien). Erhebung: Erfolgsquote erster Retry, Zeit bis Erfolg.

#### **T-C – Raten / Backoff / Häufungsschwellen**

**Ziel:** Kalibrierte Raten, Backoff, Obergrenzen, Wiederaufnahme, Häufungsschwelle §4.18 Spur 2.

**T-C.1 Rate-Obergrenze pro Quelle** – schrittweise Steigerung bis zum ersten stabilen Auftreten von 429/503/DOM-Bruch/Timeout-Häufung. Erhebung: Schwelle in req/min bzw. req/h, Antworttyp am Limit.

**T-C.2 Backoff-Wirkung pro Quelle** (10 s / 60 s / 300 s). Erhebung: Mindestpause bis erste erfolgreiche Wiederaufnahme, Mindestpause bis volle Normalrate.

**T-C.3 Häufungsschwelle §4.18 Spur 2** – aus B.2 ableiten. Erhebung: Schwellenvorschlag pro Quelle (Fehler/100 Req; Fehler/h; Fehler/Tag).

**T-C.4 Gesamthaushalt pro Quelle.** Erhebung: Zielrate, Backoff-Plan, Wiederaufnahme-Zeit, Häufungsschwelle – als Vorschlagsmatrix.

### **Teil 2 – Operator-Kurzfassung (Minimalblock erster Schliesslauf)**

**Vorbereitung:**

- hadeethenc.com testbereit

- eine Referenz-Hadith-ID fixieren und notieren

**Schritt 1 – Sprachliste**

- /languages einmal abrufen

- notieren: Anzahl Sprachen, DE ja/nein, EN ja/nein

**Schritt 2 – Feldstruktur derselben Hadith-ID**

- AR abrufen → Feldnamen, reference ja/nein, Harakāt, HTML, grade, ID-Schema

- EN abrufen → Feldnamen, reference ja/nein, HTML

- DE abrufen → Feldnamen, reference ja/nein, HTML

**Schritt 3 – Latenzreihe mit Abstand**

- 20 Abrufe derselben AR-Hadith-ID, je 1 s Abstand

- pro Request Latenz in ms und Statuscode loggen

- am Ende Min, Max, Median, P95; Rate-Limit-Header notieren

**Schritt 4 – Latenzreihe Burst**

- 20 Abrufe ohne Abstand

- pro Request Latenz und Statuscode loggen

- am Ende Min, Max, Median, P95, Fehlerquote

**Rückgabe:**

- Werte in das Rückgabeformat (Teil 3) eintragen

- leer lassen, was nicht gemessen wurde

### **Teil 3 – Kompaktes Rückgabeformat**

WARAQ LIVE-TESTLAUF RÜCKGABE

Prüfer: \_\_\_\_\_

Datum Start: \_\_\_\_\_

Datum Ende: \_\_\_\_\_

Umgebung / Netzwerk: \_\_\_\_\_

Zeitzone: \_\_\_\_\_

===== T-A E-5 TESTBETRIEB =====

Hadith-ID Referenzfall: \_\_\_\_\_

T-A.1 Sprachliste

Endpunkt: \_\_\_\_\_

Anzahl Sprachen: \_\_\_\_\_

DE vorhanden: \_\_\_\_\_

EN vorhanden: \_\_\_\_\_

Content-Type: \_\_\_\_\_

Auffälligkeiten: \_\_\_\_\_

Status: ☐

T-A.2 Einzel-Hadith-Feldstruktur

A.2.1 AR Feldnamen: \_\_\_\_\_

A.2.1 AR reference vorhanden: \_\_\_\_\_

A.2.1 AR Harakāt: \_\_\_\_\_

A.2.1 AR HTML-Markup: \_\_\_\_\_

A.2.2 EN Feldnamen: \_\_\_\_\_

A.2.2 EN reference vorhanden: \_\_\_\_\_

A.2.3 DE Feldnamen: \_\_\_\_\_

A.2.3 DE reference vorhanden: \_\_\_\_\_

A.2.3 DE Abweichungen zu AR: \_\_\_\_\_

A.2.4 Weitere Sprache: \_\_\_\_\_

Status: ☐

T-A.3 Authentizitätsgrad / Takhrij

Stichprobengrösse: \_\_\_\_\_

Feldname grade: \_\_\_\_\_

Wertebereich grade: \_\_\_\_\_

Mehrfachbewertungen: \_\_\_\_\_

Takhrij-Strukturierung: \_\_\_\_\_

Konsistenz (hoch/mittel/niedrig): \_\_\_\_\_

Status: ☐

T-A.4 Bulk-Downloads

A.4.1 Excel DE Spaltenanzahl: \_\_\_\_\_

A.4.1 Excel DE Spaltennamen: \_\_\_\_\_

A.4.1 Excel DE Encoding: \_\_\_\_\_

A.4.1 Excel DE Harakāt: \_\_\_\_\_

A.4.1 Excel DE Zeilenzahl: \_\_\_\_\_

A.4.2 PDF Sprache: \_\_\_\_\_

A.4.2 PDF Feldumfang: \_\_\_\_\_

A.4.2 PDF Index-Eignung: \_\_\_\_\_

Status: ☐

T-A.5 Rate-Limit / Stabilität / Latenz

A.5.1 20 seq 1s Min/Max/Median/P95 ms: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

A.5.1 HTTP-Statuscodes: \_\_\_\_\_

A.5.2 Burst 20 Min/Max/Median/P95 ms: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

A.5.2 HTTP-Statuscodes: \_\_\_\_\_

A.5.2 Fehlerquote: \_\_\_\_\_

A.5.3 5+Pause+5 Auffälligkeiten: \_\_\_\_\_

Rate-Limit-Header: \_\_\_\_\_

Status: ☐

T-A.6 Versionierung / ID-Stabilität

Snapshot-Datum: \_\_\_\_\_

Rerun-Datum: \_\_\_\_\_

Versionsfeld vorhanden (Name): \_\_\_\_\_

Content-Identität: \_\_\_\_\_

ID-Stabilität: \_\_\_\_\_

Status: ☐

T-A.7 Fehlverhalten

A.7.1 Nicht-existierende ID – Status / Body: \_\_\_\_\_ / \_\_\_\_\_

A.7.2 Falscher Sprachcode – Status / Body: \_\_\_\_\_ / \_\_\_\_\_

A.7.3 Malformierter Pfad – Status / Body: \_\_\_\_\_ / \_\_\_\_\_

Timeout-Verhalten: \_\_\_\_\_

Status: ☐

T-A.8 Deutsche Abdeckung

Methode: \_\_\_\_\_

AR-Masterliste Anzahl: \_\_\_\_\_

DE-Liste Anzahl: \_\_\_\_\_

Abdeckungsquote %: \_\_\_\_\_

Nicht abgedeckte Kategorien: \_\_\_\_\_

Status: ☐

===== T-B TIMEOUT-/RETRY-KALIBRIERUNG =====

T-B.1 Latenzprofil (Min/Max/Median/P95 ms)

sunnah.com: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

dorar.net API: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

dorar.net Scraping: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

E-5: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

islamweb.net: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

<span dir="rtl">جامع السنة</span>: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

<span dir="rtl">الوقفية</span>: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

Shamela lokal: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

Status: ☐

T-B.2 Ausreisser / Stabilität 24h (Ausreisser / Timeout-Rate / Tageszeitmuster)

sunnah.com: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

dorar.net API: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

dorar.net Scraping: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

E-5: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

islamweb.net: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

<span dir="rtl">جامع السنة</span>: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

<span dir="rtl">الوقفية</span>: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

Shamela lokal: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

Status: ☐

T-B.3 Retry-Verhalten (Erfolg % / Zeit bis Erfolg)

sunnah.com: \_\_\_\_\_ / \_\_\_\_\_

dorar.net API: \_\_\_\_\_ / \_\_\_\_\_

dorar.net Scraping: \_\_\_\_\_ / \_\_\_\_\_

E-5: \_\_\_\_\_ / \_\_\_\_\_

islamweb.net: \_\_\_\_\_ / \_\_\_\_\_

<span dir="rtl">جامع السنة</span>: \_\_\_\_\_ / \_\_\_\_\_

<span dir="rtl">الوقفية</span>: \_\_\_\_\_ / \_\_\_\_\_

Shamela lokal: \_\_\_\_\_ / \_\_\_\_\_

Status: ☐

===== T-C RATEN / BACKOFF / HÄUFUNGSSCHWELLEN =====

T-C.1 Rate-Obergrenze (req/min bzw. req/h / Antworttyp am Limit)

sunnah.com: \_\_\_\_\_ / \_\_\_\_\_

dorar.net API: \_\_\_\_\_ / \_\_\_\_\_

dorar.net Scraping: \_\_\_\_\_ / \_\_\_\_\_

E-5: \_\_\_\_\_ / \_\_\_\_\_

islamweb.net: \_\_\_\_\_ / \_\_\_\_\_

<span dir="rtl">جامع السنة</span>: \_\_\_\_\_ / \_\_\_\_\_

<span dir="rtl">الوقفية</span>: \_\_\_\_\_ / \_\_\_\_\_

Status: ☐

T-C.2 Backoff-Wirkung (Mindestpause bis Wiederaufnahme / bis Normalrate)

sunnah.com: \_\_\_\_\_ / \_\_\_\_\_

dorar.net API: \_\_\_\_\_ / \_\_\_\_\_

dorar.net Scraping: \_\_\_\_\_ / \_\_\_\_\_

E-5: \_\_\_\_\_ / \_\_\_\_\_

islamweb.net: \_\_\_\_\_ / \_\_\_\_\_

<span dir="rtl">جامع السنة</span>: \_\_\_\_\_ / \_\_\_\_\_

<span dir="rtl">الوقفية</span>: \_\_\_\_\_ / \_\_\_\_\_

Status: ☐

T-C.3 Häufungsschwelle §4.18 Spur 2 (Fehler/100 Req / Fehler/h / Fehler/Tag)

sunnah.com: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

dorar.net API: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

dorar.net Scraping: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

E-5: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

islamweb.net: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

<span dir="rtl">جامع السنة</span>: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

<span dir="rtl">الوقفية</span>: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

Status: ☐

T-C.4 Gesamthaushalt (Zielrate / Backoff-Plan / Wiederaufnahme / Häufungsschwelle)

sunnah.com: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

dorar.net API: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

dorar.net Scraping: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

E-5: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

islamweb.net: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

<span dir="rtl">جامع السنة</span>: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

<span dir="rtl">الوقفية</span>: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

Status: ☐

===== ABSCHLUSS =====

Abgeschlossene Teiltests: \_\_\_\_\_

Offen gebliebene Teiltests: \_\_\_\_\_

Auffälligkeiten quer über alle Quellen: \_\_\_\_\_

Gesamtstatus: ☐ T-A ☐ T-B ☐ T-C

### **Teil 4 – Abschluss-/Schliessmatrix**

| **Befund** | **Schliesst** | **Resultat** | **Dokumentbereich** |
|----|----|----|----|
| A.1 Sprachliste | F-8 | Bestätigung β-Befund | §4.16 |
| A.2.3 DE-Feldstruktur | F-1 DE | Kanonisierbarer Mini-Block | §5.1.1 / §4.16 |
| A.2.1 Harakāt AR | F-2 (E-5) | Bestätigung β-Befund | §4.16 |
| A.2 HTML-Markup-Präsenz | F-3 (E-5) | Bestätigung β-Befund | §4.16 / §5.1.1 |
| A.3 grade-Feldstruktur | F-6 Modell H | unter Schema-Filter prüfen | §5.1.1 |
| A.4.1 Excel-Feldumfang | F-6 | Kanonisierbarer Mini-Block | §4.16 / §5.1.1 |
| A.4.2 PDF-Feldumfang | F-7 | Mini-Block oder Werkbank | §4.16 |
| A.4 vs A.2 Konsistenz | F-10 | Werkbank bleibt offen | — |
| A.5 Latenzprofil E-5 | F-14 | Kanonisierbarer Mini-Block | §3.5 Modell U |
| A.5 Rate-Limit-Header / Burst | F-4 Rate E-5 | Kanonisierbarer Mini-Block | §3.5 Modell U |
| A.6 Versionsfeld | F-9 | Kanonisierbarer Mini-Block | §4.16 |
| A.6 ID-Stabilität | F-16 | Kanonisierbarer Mini-Block | §4.16 / §5.1.1 |
| A.7 Fehlverhalten | F-13 | Kanonisierbarer Mini-Block | §4.16 / §4.18 |
| A.8 DE-Abdeckungsquote | F-15 | Kanonisierbarer Mini-Block | §4.16 |
| — | F-11 | Ausbaupfad / optional | — |
| — | F-12 | bereits kanonisiert (R-1/R-2) | — |
| B.1 Latenzprofile aller Quellen | F-4 Timeouts | Kanonisierbarer Mini-Block | §3.5 Modell U |
| B.2 Ausreisser / Timeout-Raten | F-4 Retry | Kanonisierbarer Mini-Block | §3.5 Modell U / §4.18 |
| B.3 Retry-Erfolgsquoten | F-4 Obergr. | Kanonisierbarer Mini-Block | §3.5 Modell U |
| C.1 Rate-Obergrenzen | F-3 Rate | Kanonisierbarer Mini-Block | §3.5 Modell U |
| C.2 Backoff-Erholung | F-3 Backoff | Kanonisierbarer Mini-Block | §3.5 Modell U |
| C.3 Häufungsschwellen | F-3 §4.18 Sp.2 | Kanonisierbarer Mini-Block | §4.18 Spur 2 |
| C.4 Gesamthaushalt pro Quelle | F-3 kons. | Kanonisierbarer Mini-Block | §3.5 Modell U |
| — | F-4 Modell W | Werkbank bleibt offen | — |
| — | Modell A | Ausbaupfad / optional | — |
| — | Modell S | Ausbaupfad / optional | — |

**Ende Block 3.**
