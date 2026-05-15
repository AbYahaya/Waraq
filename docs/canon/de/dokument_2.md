<!-- Converted from "Dokument 2 _ ARBEITS- UND REFERENZDOKUMENT.docx" via pandoc 3.9.0.2 on 2026-05-02 -->
<!-- The .docx in this directory remains source-of-truth per docs/canon/README.md authority rule -->
<!-- Conversion is content-faithful (text, tables, identifiers, Swiss German ss, Arabic RTL spans, §-refs); Word-specific visual styling is dropped -->

# **DOKUMENT 2 – ARBEITS- UND REFERENZDOKUMENT**

Bereinigte Volltextfassung.

## **1. VERWEIS AUF DEN KANONISCHEN STAND**

Das lebende Master-Dokument (Dokument 1) ist die einzige kanonische Hauptquelle.

Zusätzlich massgebliche Einzeldokumente (alle eingefroren):

- Waraq Core Architecture Baseline v1.0

- Waraq Implementation Translation Baseline v1.0

- Waraq Engineering Execution Baseline v1.0

- Waraq Delivery Backlog Baseline v1.0

- Sprint-0 bis Sprint-6 Pläne v1.0

- OCR-Export-Endfassung v1.3

- Dokument A – Kanonischer Nutzerstil-Korpus v1.0

- Dokument B v1.2 – Feature-Spezifikation „Erkenne meinen Übersetzungsstil"

- Dokument C v1.1 – Integrationsnachricht

- Kanonische Formatvorlagen-Baseline v1.1

## **2. EINGEFRORENE PUNKTE**

### **2.1 Übergreifend eingefroren**

- Alle oben genannten Baselines und Dokumente.

- OCR-Export-Endfassung v1.3: eingefroren, implementierungsbereit, keine Coding-Freigabe.

- Dokument A, Dokument B v1.2, Dokument C v1.1: eingefroren, kanonisch.

- Formatvorlagen-Baseline v1.1: eingefroren.

- Vorranglogik Stilfeature (Rang 1 / Rang 2 / Rang 3): unveränderlich.

- decision_source-Enum (10 Werte): unveränderlich.

- Audit-Matrix A-01–D-03: baseline-basiert eingefroren.

### **2.2 Trennungsregeln**

- OCR-Export-Strang vom Stilfeature: absolut getrennt.

- Preflight-Konfigurationsschicht von Gate-Prüfungsschicht: konzeptionell getrennt.

- Wortpanel-Strang vom Schnittstellen-Strang: getrennte Arbeitsfronten.

### **2.3 Neu eingefroren – P-Slot-Belegungslogik**

| **Entscheid** | **Inhalt** |
|----|----|
| P-01–P-02 / P-05–P-06 – Belegungslogik | Freie Slots werden ausschliesslich mit blockierenden Zuständen belegt, die im bestehenden Kanon bereits angelegt sind. |
| P-01–P-02 / P-05–P-06 – Kandidatenstand | Derzeit keine sauberen Kandidaten identifizierbar. Slots bleiben offen. |

### **2.4 Neu eingefroren – W-Slot-Minimalmodell II und P-03**

| **Entscheid** | **Inhalt** |
|----|----|
| W-01 / W-02 / W-03 – Belegung Minimalmodell II | W-01 = Mittel-Audit-Befunde. W-02 = K-01–K-07 Konsistenzwarnungen. W-03 = Graduelle Formatvorlagen-Abweichungen. |
| P-03 – strukturelle Rolle im Preflight | Eigenständiges blockierendes Gate in der Preflight-Gate-Prüfungsschicht, strukturell gleichrangig neben P-04. |

### **2.5 Neu eingefroren – Kritische Schriftart-Verfügbarkeit und W-04 bis W-08**

| **Entscheid** | **Inhalt** |
|----|----|
| Kritische Schriftart-Verfügbarkeit – Einordnung | Guard-nah vor dem Preflight-Dialog. Fehlt eine der vier kritischen Schriftarten, wird der Preflight-Dialog nicht geöffnet. Auflösung nur durch technische Wiederherstellung. Kein P-Slot belegt. |
| W-04 bis W-08 – Kandidatenstand | Im bestehenden Kanon des Publikationsexports derzeit keine weiteren sauberen Kandidaten identifizierbar. Slots bleiben offen. Keine Richtungsbindung vorweggenommen. Keine neuen warnungsbasierten Zustände eingeführt. |

### **2.6 Neu eingefroren – Übersetzungs-Pipeline-Verhalten, Qurʾān-Erkennungsregeln, Shamela-Modi, OCR-Qualitätsprinzip**

| **Entscheid** | **Inhalt** |
|----|----|
| Prüf-Modell-Korrekturrecht (§3.6) | Vier Situationstypen: Einigkeit → Primär übernommen; objektiv-deterministischer Befund → Auto-Korrektur, protokolliert; substanziell-interpretativ → Konfidenz sinkt, Review; echte Ambiguität → Nutzerhinweis. Modellzuweisung bleibt offen. |
| Kein stiller Rollentausch (§3.6) | Primärpfad-Ausfall → kein stiller Wechsel; Prüfpfad-Ausfall → Primär weiter, betroffene Stellen gelten als nicht gegengeprüft und werden protokolliert. |
| Audit-Befunde im Übersetzungsflow (§3.6) | A-01 bis D-03 stoppen den Flow nicht; Befunde persistiert und in Preflight weitergeführt. |
| Qurʾān-Vokalisierungs-Regel (§4.15) | Nach akzeptierter Erkennung: quranenc.com alleiniger Textträger. Kein freier Wahlfall. Prüfbedürftig nur die Erkennungsfrage. |
| Qurʾān-API-Ruf-Zeitpunkt (§4.15) | Erster externer API-Ruf erst in Übersetzungsphase. Kein externer Ruf in der OCR-Phase. |
| Qurʾān-Konfidenz-Schutz (§4.15) | Unter Schwellenwert: manuelle Bestätigung vorgelagert. Schwellenwert offen. |
| Qurʾān-Projektstellen-Schutz (§4.15) | Bestehende Projektstellen bei Änderung der lokalen Kopie unverändert. Kein stilles Überschreiben. |
| Shamela Nutzungsmodi (§3.5) | Modus A (OCR-intern, systemausgelöst in OCR-Stufe 3) und Modus B (nutzergesteuert, Lexikon-Workflow in der Übersetzungsphase). |
| Shamela Lisān/Tāj (§3.5) | Als eigenständig abfragbare Einheiten innerhalb Shamela behandelt. |
| OCR-Qualitätsprinzip (§3.4) | Kein künstlicher Sieger bei ungelöster Mehrdeutigkeit nach Durchlauf der vorgesehenen Rekonstruktionsstufen. Konfidenz sinkt, Review priorisiert. |

### **2.7 Neu eingefroren – Hadith-Integration**

| **Entscheid** | **Inhalt** |
|----|----|
| Hadith-Quellenstruktur (§4.16) | Zweistufig: Pflichtmenge (sunnah.com, Shamela, dorar.net) und erweiterte Menge (islamweb.net, <span dir="rtl">جامع السنة النبوية, المكتبة الوقفية, جامع الكتب التسعة, موسوعة الأحاديث النبوية). المكتبة الوقفية</span> bewusst als Eskalationsquelle in der erweiterten Menge, nicht in der Pflichtmenge (übernommener Integrationsstand). |
| Hadith-Konsenslogik (§4.16) | Mehrdimensionale Vergleichs- und Konsenslogik (Wortlautnähe, Trägerschaft, Autornähe, Isnād, Vokalisierung, Authentizität). Lineares Konfidenz-Ranking (§3.5) als Tie-Breaker. |
| Kutub as-Sitta (§4.16) | Starker Gewichtungsfaktor, kein absoluter Vorrang. Wortlautnäherer belastbarer Treffer ausserhalb kann Vorrang brechen; Abweichung im Review sichtbar. |
| Hadith decision_event-Zuordnung (§4.16) | 7 Handlungstypen → translation_pipeline (2) + conflict_resolution (5). Kein neuer decision_source-Wert. |
| Hadith-Vokalisierungsprinzip (§4.16) | Referenz-Matn und Referenz-Vokalisierung als getrennt bestimmbare Felder. Kein alleiniger Textträger (Abgrenzung zu §4.15). Relevante Konflikte → Nutzereinbezug → conflict_resolution. Konkretes Eskalationskriterium geschlossen. |

### **2.8 Neu eingefroren – Konsolidierung Schnittstelle 5**

| **Entscheid** | **Inhalt** |
|----|----|
| Pflichtmenge (§4.16) | P-1 sunnah.com, P-2 Shamela, P-3 dorar.net bleiben Pflichtquellen. Unverändert. |
| E-1 islamweb.net (§4.16) | Option B entschieden: dokumentiert, faktisch suspendiert. |
| E-2 <span dir="rtl">جَامِعُ السُّنَّةِ النَّبَوِيَّة</span> (§4.16) | Hoch belastbar identifiziert als Alifta-/Harf-Variante. Option B entschieden: dokumentiert, faktisch suspendiert. |
| E-3 <span dir="rtl">المكتبة الوقفية</span> (§4.16) | Option B entschieden: dokumentiert, faktisch suspendiert; nur noch als mögliche manuelle Referenzquelle geführt. |
| E-4 <span dir="rtl">جَامِعُ الكُتُبِ التِّسْعَة</span> (§4.16) | Option B entschieden: dokumentiert, faktisch suspendiert. |
| E-5 <span dir="rtl">مَوْسُوعَةُ الأَحَادِيثِ النَّبَوِيَّة</span> (§4.16) | Option B entschieden: nicht suspendiert. Sonderrolle „deutsche Übersetzungsquelle / mehrsprachige Referenzquelle". Keine breite Korpus-Ersatzquelle. Kein API-Volltextsuchpfad. Technischer Anschluss über offizielle API und offizielle Bulk-Downloads. |
| Ausschluss (§4.16) | hadithportal.com als Quelle für die Hadith-Verifikation ausgeschlossen. |
| Eskalationslogik (§4.16) | Bei automatischer Zuschaltung der erweiterten Menge faktisch ausschliesslich E-5 in Sonderrolle wirksam, solange E-1–E-4 suspendiert bleiben. Zweistufige Struktur Pflicht/erweitert strukturell unverändert. |

### **2.9 Neu eingefroren – Kanonisierungsrunde K-1 / K-2 / K-3 Hadith-Strang**

| **Entscheid** | **Inhalt** |
|----|----|
| Vokalisierungs-Eskalationskriterium (§4.16) | Klassen V-0 (automatisch tolerierbar) / V-1 (protokollpflichtig ohne Eskalation) / V-2 (eskalationspflichtig) mit Typologie, Aggregationsregel (höchste Klasse gewinnt), Rückfallregel (im Zweifel V-2). Feld vokalisierungs_konflikt strikt binär (nein / ja); Klassen-Differenzierung ausschliesslich über die abgeleitete vokalisierungsklasse. Bei unklarer Typ-Zuordnung bleibt das Feld auf ja; Unklarheit wird nur im Logging bzw. in der Konfliktbegründung dokumentiert. Schliesst die in §4.16 benannte Restoffenheit zum konkreten Eskalationskriterium. |
| Hadith-Verifikationsstatus (§4.16) | Stellentypen N-1 bis N-10; Verifikationsklassen H-0 (review-intern tolerierbar) / H-1 (protokollpflichtig, warnungsfähig) / H-2 (export-blockierend bis Auflösung). Auflösung ausschliesslich über die 7 kanonisierten Handlungstypen. Markierung „für spätere Klärung" hebt H-2 nicht auf. Kein Audit-Fall im Sinne §4.6. Keine neuen decision_source-Werte. |
| Gate-Verortung Hadith-Verifikationsstatus (§4.7) | Eigene benannte Gruppe „Hadith-Verifikationsstatus" innerhalb der bestehenden Gate-Prüfungsschicht. Keine neue Schicht. Keine Belegung offener P-01/P-02/P-05/P-06- oder W-04–W-08-Slots. H-2 blockierend, H-1 warnungsbasiert (go_with_warning analog §4.9 E-1, decision_source preflight_confirmation gemäss §4.10). Slot-unabhängig geführt; spätere formale Slot-Belegung bleibt möglich. |
| Datenmodell Hadith-Mehrquellen-Ergebnisobjekte (§4.16 / Kapitel 5) | Vier logische Ebenen (Stellenanker / Einzelquellen-Lesung / Aggregiertes Gesamtergebnis / Nutzerentscheidungs-Overlay). quellen_rolle ist Pflicht-Snapshot-Feld pro Einzelquellen-Lesung (Werte pflicht / erweitert_aktiv / erweitert_sonderrolle / erweitert_suspendiert), zum Zeitpunkt des Verifikationslaufs festgeschrieben; keine dynamische Rückableitung. Abgeleitet, nicht persistiert: entscheidungsstatus, vokalisierungsklasse, hadith_stellen_typ, hadith_verifikationsklasse. satz_uuid ist Pflicht, sobald Satzsegmentierung für die Stelle vorhanden ist. Unveränderlichkeit analog §4.9 E-10. Keine neuen Kernobjekte. Keine neuen decision_source-Werte. |

### **2.10 Neu eingefroren – Teilkanonisierung K-4 R-1 / R-2 (englischer Hadith-Strang)**

| **Entscheid** | **Inhalt** |
|----|----|
| Englischer Hadith-Strang – Teilkanonisierung R-1 / R-2 (§4.16 / §5.1.1) | Englischsprachige Website-Übersetzungen aus Hadith-Verifikationsquellen (P-1 sunnah.com, E-5 hadeethenc.com) werden in website_uebersetzung mit lang = "en" geführt. Einträge entstehen unabhängig von der Projekt-Zielsprache und wirken ausschliesslich als Provenienz- und Vergleichsmaterial. Anzeige als Vergleichssprache im Hadith-Review ist zulässig, nicht verpflichtend, erzeugt keinen eigenen decision_event. Keine Auswirkung auf Matn-Konsens, Referenz-Matn, Referenz-Vokalisierung, Primärübersetzung. Kein neues Feld, kein neuer decision_source-Wert, keine neue Architektur. R-3 Strukturentscheidung kanonisiert: Englische Hadith-Ausgabe als eigener Primärproduktionspfad aus dem arabischen Matn, parallel und strukturell gleichwertig zur deutschen Hadith-Ausgabe; Keine-Kaskade-Regel für die Hadith-Matn-Übersetzung. Detaillierte R-3-Regeln (Quellenangabe-Format, Transliteration, Fussnotenlogik, Verhältnis zum Stilfeature und zu Schnittstelle 3) bleiben Werkbank. |

### **2.11 Neu eingefroren – Qurʾān-Trägerstruktur M3**

| **Entscheid** | **Inhalt** |
|----|----|
| Q4-9 AR-Referenzbestand-Status (§4.15) | AR-Referenzbestand ist eigenständiger lokaler Bestand, unabhängig von den Übersetzungs-Fallback-Kopien. Zielsprachenunabhängig genutzt. Zu keinem Zeitpunkt API-gestützt, kein API-Primärpfad, kein Fallback-Status. Kanonisch genannte APIs (quranenc.com DE und EN) und ihre lokalen Fallback-Kopien betreffen ausschliesslich die Übersetzungsträger, nicht den AR-Referenzbestand. AR-Quellenbenennung und AR-Update-Mechanismus bleiben ausdrücklich offen (Schnittstelle-4-Detailpunkte). |

### **2.12 Neu eingefroren – Schnittstelle-5-Strukturnachzüge A-4 / A-6 / A-7 / A-8**

| **Entscheid** | **Inhalt** |
|----|----|
| A-4 HTML-Stripping (Modell R, §5.1.1) | Für Quellen mit Markup-Antwort wird der Roh-Body in matn_arabisch_raw persistiert; matn_arabisch enthält die deterministisch abgeleitete Textfassung. Textnähe-, Vergleichs- und Konsenslogik arbeiten auf matn_arabisch. Bei Quellen ohne Markup entfällt matn_arabisch_raw. |
| A-6 Scraping-Zweitpfad (Modell D, §3.5) | Scraping ist strikter Zweitpfad gegenüber einer vorhandenen API derselben Quelle. Für dorar.net: API-Pfad primär, Scraping nur als Rückfall. DOM-Bruch = §4.18-Klasse-B-Ausfall ohne Retry; keine stille Selbstheilung zur Laufzeit. |
| A-7 Anfrageprofil externer Quellen (Modell U, §3.5) | Externe HTTP-basierte Quellen (APIs und Scraping-Pfade) folgen einem einheitlichen konservativen Anfrageprofil. Lokale Quellen ausgenommen; Shamela ausdrückliche Ausnahme. Konkrete Raten, Pausen, Obergrenzen und Wiederaufnahme-Zeiten bleiben offen und werden nach realer Messung festgelegt. |
| A-8 E-5-Laufzeitmodus (§4.16) | Offizielle Live-API primärer Laufzeitpfad. Offizielle Bulk-Downloads sekundärer Hilfs- und Analysepfad, nicht Laufzeitquelle für die Hadith-Verifikation. Kein Offline-Index als Normalpfad. Kein Frontend-Scraping als Normalmodell. |

## **3. OFFENE PUNKTE**

### **3.1 Klasse 1 – Bestätigt und kanonisch eingefroren**

**Audit- und Konsistenzpunkte:**

- C-01, C-02

- L-01, L-07–L-09, L-13, L-15–L-17, L-19–L-21, L-23, L-25

- L-02–L-06, L-10–L-12, L-14

- Audit-Matrix A-01 bis D-03

**Übersetzungs-Pipeline und API-Verhalten:**

- API-Ausfall-Kanal

- Dashboard-Statusindikator

- Persistenz Stilmarker

- Kalibrierungswerte Stilfeature

- Modellzuweisung Übersetzungs-Pipeline (§3.6): Primär GPT-4o / Prüf Gemini 2.5 Pro; systemweit; Rollenlogik unverändert; OCR-Stufe 3 davon nicht berührt

- Modellzuweisung OCR-Stufe 3 (§3.4): GPT-4o + Gemini 2.5 Pro parallel als Konsens-Signalgeber innerhalb der KI-Validierungslinie; keine Primär/Prüf-Rollen; Uneinigkeit priorisiert ins OCR-Review, kein künstlicher Sieger; Revidierbarkeit analog §3.6

- Prüf-Modell-Korrekturrecht (vier Situationstypen)

- Kein stiller Rollentausch Übersetzungs-KI

- Audit-Befunde stoppen Übersetzungsflow nicht

**Preflight und Gates:**

- Formatvorlage / RTL / Ziffern-Verortung

- Preflight-Schichtenmodell

- Formatvorlagen-Integritätsverstösse Auflösungspfad und Prüfzeitpunkt

- P-01–P-02 / P-05–P-06 Belegungslogik und Kandidatenstand

- W-01 / W-02 / W-03 Belegung (Minimalmodell II)

- P-03 strukturelle Rolle im Preflight

- Kritische Schriftart-Verfügbarkeit Einordnung

- W-04–W-08 Kandidatenstand

**Qurʾān-Strang (§4.15):**

- Qurʾān-Vokalisierungs-Regel (alleiniger Textträger nach Akzeptanz)

- Qurʾān-API-Ruf-Zeitpunkt (erst Übersetzungsphase)

- Qurʾān-Konfidenz-Schutz (manuelle Bestätigung, Schwellenwert offen)

- Qurʾān-Projektstellen-Schutz (kein stilles Überschreiben)

- Qurʾān-Stellenbehandlung: 4 Handlungstypen plus Auto-Akzeptanz; decision_source-Zuordnung translation_pipeline für Bestätigung und für ausdrückliche Nutzeraktion zur Aktualisierung einer bereits gespeicherten Qurʾān-Stelle, conflict_resolution für Korrektur und Ablehnung; Auto-Akzeptanz ohne decision_event; keine neuen decision_source-Werte; strukturell analog §4.16

- Ausklammerung akzeptierter Qurʾān-Stellen im Übersetzungsfluss (§3.6): akzeptierte Qurʾān-Stellen gemäss §4.15 werden als geschützte Stellen geführt; ausgeklammert wird die akzeptierte Qurʾān-Stelle selbst, nicht der umgebende Chunk; kanonischer arabischer Referenztext und kanonische Zielsprachen-Übersetzung aus den Trägersträngen gemäss §4.15; Glossar, Stilprofil und RAG wirken nicht auf die geschützte Stelle; übriger Übersetzungsfluss unberührt; keine neue Architektur; Hadith-Seite nicht Gegenstand dieser Regelung

**Shamela und OCR-Qualitätsprinzip:**

- Shamela Nutzungsmodi (Modus A = OCR-Stufe 3 / Modus B = Lexikon-Workflow)

- Shamela Lisān/Tāj als eigenständige Abfrageeinheiten

- OCR-Qualitätsprinzip (kein künstlicher Sieger nach Rekonstruktionsstufen)

- Bereinigung Schnittstelle 1 / 2 gegen §3.4: Die KI-basierte Validierung ist eine der drei §3.4-Stufe-3-Validierungslinien; innerhalb der KI-Linie gelten die kanonisierten Regeln (GPT-4o und Gemini 2.5 Pro als gleichrangige Konsens-Signalgeber, keine Primär/Prüf-Rollen, kein künstlicher Sieger bei Uneinigkeit innerhalb der KI-Linie, Revidierbarkeit analog §3.6); das OCR-Qualitätsprinzip §3.4 greift, wenn nach Durchlauf der vorgesehenen Rekonstruktionsstufen mehrere starke konkurrierende Lesungen bestehen bleiben; die konkrete Gewichtungs- und Auslösematrix zwischen den drei Linien bleibt offen

**Hadith-Strang (§4.16):**

- Hadith-Quellenstruktur zweistufig (Pflicht + erweitert)

- Hadith-Konsenslogik (mehrdimensional + Tie-Breaker)

- Kutub-as-Sitta (starker Gewichtungsfaktor, kein absoluter Vorrang)

- Hadith decision_event-Zuordnung (7 Handlungstypen)

- Hadith-Vokalisierungsprinzip (getrennte Felder, kein alleiniger Textträger)

- Hadith-Quellenlage erweiterte Menge: E-1 Option B; E-2 Option B mit Identifikation als Alifta-/Harf-Variante; E-3 Option B mit Rolle manuelle Referenzquelle; E-4 Option B; E-5 Option B mit Sonderrolle deutsche Übersetzungsquelle / mehrsprachige Referenzquelle; Ausschluss hadithportal.com; Eskalationslogik faktisch nur E-5 wirksam

- Vokalisierungs-Eskalationskriterium: Klassen V-0/V-1/V-2 mit Aggregations- und Rückfallregel; vokalisierungs_konflikt strikt binär (nein / ja) mit Klassen-Differenzierung nur über die abgeleitete vokalisierungsklasse und Unklarheit nur im Logging bzw. in der Konfliktbegründung

- Hadith-Verifikationsstatus: Stellentypen N-1 bis N-10, Klassen H-0/H-1/H-2, Auflösung ausschliesslich über die 7 Handlungstypen, kein Audit-Fall

- Gate-Verortung Hadith-Verifikationsstatus: eigene benannte Gruppe innerhalb der Gate-Prüfungsschicht ohne neue Schicht und ohne P-/W-Slot-Belegung; H-2 blockierend; H-1 warnungsbasiert mit go_with_warning analog §4.9 E-1 und decision_source preflight_confirmation

- Datenmodell Hadith-Mehrquellen-Ergebnisobjekte: vier logische Ebenen; quellen_rolle als Pflicht-Snapshot pro Einzelquellen-Lesung ohne dynamische Rückableitung; entscheidungsstatus und Klassen-Zustände abgeleitet und nicht persistiert; satz_uuid Pflicht, sobald Satzsegmentierung vorhanden; Unveränderlichkeit analog §4.9 E-10; keine neuen Kernobjekte; keine neuen decision_source-Werte

- Englischer Hadith-Strang Teilkanonisierung R-1/R-2: englischsprachige Website-Übersetzungen aus P-1 und E-5 als sprachneutrales Referenz- und Vergleichsfeld in §4.16 / §5.1.1; Einträge projekt-zielsprachenunabhängig; Anzeige als Vergleichssprache im Review zulässig und nicht verpflichtend; kein eigener decision_event; keine Auswirkung auf Matn-Konsens, Referenz-Matn, Referenz-Vokalisierung, Primärübersetzung; R-3 Strukturentscheidung kanonisiert; detaillierte R-3-Regeln bleiben Werkbank

**Schnittstelle-5-Strukturnachzüge:**

- A-4 HTML-Stripping (Modell R, §5.1.1)

- A-6 Scraping-Zweitpfad (Modell D, §3.5)

- A-7 Anfrageprofil (Modell U, §3.5)

- A-8 E-5-Laufzeitmodus (§4.16)

- Alle strukturell kanonisch; konkrete Werte live-messungsabhängig und geparkt

**Fehler- und Klassifikationssystem:**

- L-24 Klasse-B-Generallogik (§4.18): aggregierte Nutzerinformation über Dashboard-Statusindikator bei Häufung gemäss Spur 2; bestehende Spezialfälle unberührt; konkrete Häufungsschwellenwerte als Werkbank live-messungsabhängig

**Geparkt – Schnittstelle-5-Live-Testpaket:** Die live- und API-testabhängigen Restpunkte werden bis zur realen Ausführung geparkt. Umfasst:

- E-5-Testbetriebsfragen F-1 / F-4 / F-9 / F-13 / F-14 / F-16

- F-3 konkrete Werte (Raten, Backoff-Pausen, Obergrenzen, Wiederaufnahme-Zeiten, Häufungsschwelle §4.18 Spur 2)

- F-4 konkrete Werte (Timeout- und Retry-Werte pro Quelle)

Keine stille Vorwegnahme. Keine Rekonstruktion ohne reale Messung. Der zugehörige ausführungsreife Testlauf-Block (Operator-Kurzfassung, kompaktes Rückgabeformat, Abschluss- und Schliessmatrix) wird als separater operativer Werkbank-/Hilfsblock in Block 3 geführt („Schnittstelle 5 – Live-Testpaket (geparkt)") und erst bei realer Ausführung zurückgespielt.

### **3.2 Klasse 2 – Vorläufig / empfohlen / ausstehend**

#### **2A – Audit-Matrix**

Baseline-basiert abgeglichen. Konsistent mit §4.6.

#### **2B – Stilfeature-Integration E-1 bis E-8**

Aufgelöst. Für diesen Arbeitsstand wird die Kennung „E-1 bis E-8" als Bezeichnung der acht Hauptabschnitte §1–§8 von Dokument C v1.1 behandelt. Dokument C v1.1 ist als Integrationsrahmen formal bestätigt (siehe Klasse-1-Eintrag).

Die in Dokument C v1.1 §3 genannten Folgearbeiten bleiben ausdrücklich offen und sind nicht Gegenstand dieser Bestätigung:

- formale Integrationsanalyse

- CRs für Core Architecture Baseline / Engineering Execution Baseline / Delivery Backlog Baseline

- Erweiterung bestehender Objekte (account, decision_event, Übersetzungs-Job/Recovery, Provenance/EXPORT_EVENT)

- Audit-Integration in A-01–D-03-Struktur

- Ticket-Definition

- Sprint-Planung

- Kalibrierung der offenen Schwellenwerte nach Gold-Corpus-Tests

- Coding-Freigabe

#### **2C – Gruppe-3-UI-Defaults**

Alle bestätigt und eingearbeitet.

#### **2D – Offene Einzelpunkte**

- **L-24:** Klasse-B-Generallogik nicht kanonisch ausformuliert. Separat offen ohne Prioritätsnummer.

- **Hintergrund-Archive-Liste (Frühphase, Nr. 6–10):**

  - Nr. 8 (Entitäten-Datenbank): im heutigen Kanon funktional im Referenz- und Entitäten-System aufgegangen.

  - Nr. 6 (Übersetzungsgedächtnis) und Nr. 7 (Vokalisierungs-Korrekturen): teilweise funktional abgedeckt, aber nicht als eigene Archivkategorie geführt.

  - Nr. 9 (Hadith-Verifikations-Cache): im heutigen Kanon nicht explizit geführt, bleibt vorerst Implementierungs-/Performancefrage.

  - Nr. 10 (<span dir="rtl">بلاغة</span>-Lernarchiv): im heutigen Kanon nicht abgebildet, bleibt Wiedervorlage für einen späteren Stilfeature-/Coding-Freigabe-Schritt.

  - scope_type-Enum-Erweiterung (DBB-Substanzbefund Paket 4): Der scope_type-Enum-Werteraum ist in der heutigen Core Architecture Baseline §B.1 mit \`segment, page, block, account\` festgelegt; die Delivery Backlog Baseline v1.0 verwendet darüber hinaus aktiv den Wert \`project\` (T-1.3.1, T-1.3.2, T-4.3.1, T-6.1.1, T-7.3.2, T-8.2.1, T-9.1.1, T-10.1.2, T-10.2.1). Beide Konzepte sind legitim: \`account\` accountweit für Stilprofile gemäss §4.12.2 / §5.2; \`project\` werkweit. Dokument 1 §4.11 erwähnt in der Abfrageregel \`active_decision_event_uuids\[\]\` nur \`segment\` und \`page\` und lässt die übrigen Werte implizit. Entschieden: Der Enum-Werteraum wird auf \`segment \| page \| block \| account \| project\` erweitert. Diese Erweiterung ist eine Kanon-Änderung an Core Architecture Baseline §B.1 und an Dokument 1 §4.11 (inkl. Abfrageregel). Sie wird nicht innerhalb von Paket 4 retrograd eingepflegt, sondern als bestätigter Befund mitgetragen und im Schluss-Audit (Paket 7) sauber als ALT→NEU-Block in CAB §B.1 und Dokument 1 §4.11 verankert. DBB v1.0 bleibt im Wortlaut unverändert; die Konsistenz mit dem entschiedenen Endzustand ist gegeben.

  - Kein stiller Kanonnachzug. Kein Verwurf. Gebundener Resthinweis.

  - Heading-4/5/6-Abdeckungsgap (Bereinigungsbefund Formatvorlagen-Baseline v1.1, Chat {AKTUELLER_CHAT}): Die Kerntabelle der Formatvorlagen-Baseline v1.1 §7.2 enthält für die deutsche Heading-Reihe nur Heading 1, Heading 2 und Heading 3. Die IVZ-Konfiguration derselben Baseline setzt mit \`TOC \o "1-4"\` ausdrücklich Heading 4 voraus. Dokument 1 §7.1 nennt für Calibri ausdrücklich „Heading 1–6"; Engineering Execution Baseline v1.0 §3.4 bestätigt Heading 1–6 als Teil der kritischen Schriftart-Verfügbarkeit für Calibri. Es besteht damit ein Substanz-Gap zwischen drei kanonischen Quellen: Formatvorlagen-Baseline v1.1 §7.2 (Heading 1–3 explizit) versus Dokument 1 §7.1 / EEB v1.0 §3.4 (Heading 1–6) versus IVZ-Konfiguration derselben Formatvorlagen-Baseline (Heading 1–4 vorausgesetzt). Mögliche Auflösungsrichtungen sind: (a) implizite Vererbung von Heading 3 für Ebenen 4/5/6 explizit dokumentieren; (b) Heading 4/5/6 als eigene Zeilen in die Kerntabelle aufnehmen; (c) Inkonsistenz zwischen Dok. 1 §7.1 / EEB §3.4 und der Formatvorlagen-Baseline anders auflösen. Eigenständige Auflösung in einer Bereinigungsrunde wäre eine Kanon-Änderung und ist daher unterblieben. Die Auflösung wird im Schluss-Audit (Paket 7) sauber als ALT→NEU-Block in der Formatvorlagen-Baseline v1.1 §7.2 und gegebenenfalls in Dokument 1 §7.1 sowie EEB v1.0 §3.4 verankert. Formatvorlagen-Baseline v1.1, Dokument 1 §7.1 und EEB v1.0 §3.4 bleiben im Wortlaut unverändert; die Konsistenz mit dem entschiedenen Endzustand ist herzustellen.

  - **Status (Schluss-Audit Paket 7, 2026-05-08): geschlossen — Variante (a)**. Auf Grundlage der bestehenden Heading 1–6 Definitionen in Formatvorlagen-Baseline v1.1 §7.2 sowie der ausdrücklichen „Heading 1–6"-Erwähnung in Dokument 1 §7.1 und EEB v1.0 §3.4 wird die IVZ-Konfiguration auf \`TOC \o "1-6"\` erweitert; toc5 = 44 pt und toc6 = 55 pt werden ergänzt. Vollständige IVZ-Navigierbarkeit aller kanonisch definierten Heading-Ebenen. ALT→NEU verankert in Formatvorlagen-Baseline v1.1 §7.2 (DE und EN); Implementierungs-Anpassung in waraq.export.docx_builder._add_toc.

  - Kein stiller Kanonnachzug. Kein Verwurf. Gebundener Resthinweis.

  - Account-scoped Decision-Event-Lesepfad: account-scoped Decision Events (insbesondere Stilprofil-Entscheidungen mit decision_source = style_management) sind kanonisch vorhanden, verfügen jedoch aktuell über keinen expliziten scope-getrennten Lesepfad in der Historien-Schicht (WS-10). Diese Lücke ist als gebundener Resthinweis festgehalten und wird im Rahmen der Stilfeature-Folgearbeit (Dokument C v1.1 §3 und DBB §7) adressiert. Keine Vorwegnahme im aktuellen Backlog. Decision-Event-Mapping decision_source × scope_type:

  - Die Zuordnung zwischen decision_source und zulässigem scope_type ist im aktuellen Kanon nicht zentral definiert, sondern verteilt über mehrere Dokumente (CAB §B–§C, Dokument 1 §4.x, DBB T-x.x.x, OCR-Export v1.3). Eine vollständige und konsistente Mapping-Tabelle ist aktuell nicht vorhanden. Diese Lücke ist als gebundener Resthinweis festgehalten und erfordert eine systematische, quellengestützte Konsolidierung vor einer möglichen Kanonisierung. Keine implizite Verdichtung oder Vorwegnahme.

  - **Status (Schluss-Audit Paket 7, 2026-05-08): formale Kanonisierung zurückgestellt — Variante (β)**. Eine empirische Mappung der bisher von der Implementierung (M2–M6) tatsächlich beschriebenen Zellen ist informativ in docs/canon/CR-Paket-7-Schluss-Audit.md §3 dokumentiert (12 belegte Zellen aus 50 möglichen). Die Tabelle ist **nicht kanonisch**; sie erzeugt keine normative Wirkung im aktuellen Kanon und kein Validierungs-Pflichtschema gegen Implementierung. Formale Kanonisierung erfolgt im Rahmen der Stilfeature-Folgearbeit (CR-3, F1/F3/F4/F5), sobald die heute offenen Zellen — insbesondere style_management × account (Account-Lesepfad WS-10) und gegebenenfalls translation_pipeline × segment für §4.16.5 (Hadith-Per-Stelle) — ausgeführt sind. Bis dahin bleibt jede neue Zellen-Belegung pro Modul lokal entscheidbar; eine zentrale Sperrliste existiert nicht.

#### **2E – Gate-Verknüpfung P-01–P-06 / W-01–W-08**

**Kanonisch bestätigt:**

- Guard-nahe Blockaden vor Preflight: Ziffernstandard, kritische RTL-Fehler, Formatvorlagen-Integritätsverstösse, kritische Schriftart-Verfügbarkeit.

- Preflight-Schichtenmodell: Konfigurationspflichten vs. Gate-Prüfungen.

- P-03: eigenständiges blockierendes Gate, gleichrangig neben P-04.

- P-04: Hoch-Audit-Befunde.

- W-01: Mittel-Audit-Befunde.

- W-02: K-01–K-07.

- W-03: Graduelle Formatvorlagen-Abweichungen.

- Hadith-Verifikationsstatus als eigene benannte Gruppe innerhalb der Gate-Prüfungsschicht (ohne neue Schicht, ohne P-/W-Slot-Belegung; H-2 blockierend, H-1 warnungsbasiert).

**Noch offen:**

- P-01–P-02 / P-05–P-06: keine sauberen Kandidaten. Slots offen.

- W-04 bis W-08: keine sauberen Kandidaten im bestehenden Kanon. Slots offen. Keine Richtungsbindung.

#### **2F – Externe Quellen / Schnittstellen-Arbeitsentwürfe**

**OCR-Maximum-Qualitätslogik:** Eigene Endfassung des Arbeitsentwurfs vorhanden. Volltext als separate Endfassung mitgetragen. Noch kein Kanon. Strukturell entschieden als Arbeitsstand (Block 3 Endfassung 1 Punkt 8.2): projektweise Aktivierung mit blockklassen-gesteuerter Tiefe; minimale Verankerung über ein Projekt-Flag für den Maximum-Modus und ein Provenienzfeld für den aktiven OCR-Modus pro OCR-Lauf auf Blockebene, ohne neues Kernobjekt und mit offener finaler Feldbenennung; Aktivierung als Log-Eintrag auf Projektebene im Projekt-Protokoll, ohne decision_event gemäss §4.10 und ohne neuen decision_source-Wert. Werkkategorien-Automatik, Schwellen, Eskalationszahlen, weitere zusätzliche Engines/Provider über Google Cloud Vision hinaus, Kosten-/Latenzgrenzen, Kandidatenmatrix-Persistenzform, UI-Darstellung und finale Feldbenennung bleiben offen. Google Cloud Vision (DOCUMENT_TEXT_DETECTION) ist als zusätzliche OCR-Leselinie im Kanon ergänzt; die konkrete Primärrolle und Gewichtung bleibt Gold-Corpus-abhängig.

**Schnittstelle 1 – OCR-Hauptengine:** Endfassung des Arbeitsentwurfs vorhanden, plus verschärfte Zusatz-Endfassung im Maximum-Modus. Volltext als separate Endfassung mitgetragen. Noch kein Kanon.

**Schnittstelle 2 – OCR-semantische Zusatzvalidierung:** Endfassung des Arbeitsentwurfs vorhanden, plus verschärfte Zusatz-Endfassung im Maximum-Modus. Volltext als separate Endfassung mitgetragen. Noch kein Kanon.

**Schnittstelle 3 – Übersetzungs-KI:** Endfassung des Arbeitsentwurfs vorhanden. Volltext als separate Endfassung mitgetragen. Noch kein Kanon.

**Schnittstelle 4 – Qurʾān-Schnittstelle:** Endfassung 3 (Arbeitsentwurf, 8 Punkte) vorhanden. Technische Zugriffsspezifikation als separater Volltext-Arbeitsstand erstellt (Q4-1 bis Q4-9). API-Endpunkte und Response-Format aus öffentlicher Dokumentation verifiziert. Zugriffspfade je Auslöser, Timeout/Retry, Fehlerklassen, Logging, Versionierung und Objektverknüpfung als Arbeitsentwurf präzisiert. Kritischer offener Befund: API liefert nach dokumentiertem Stand nur Übersetzungen, nicht arabischen Referenztext (Variante A als Arbeitshypothese). 10 explizite offene Punkte dokumentiert (Q4-9). Punkt 5 der Endfassung 3 unverändert: lokale Fallback-Basis = vollständiger Datenstand. Volltext als separater Arbeitsstand mitgetragen. Noch kein Kanon.

**Schnittstelle 5 – Hadith-Schnittstelle:**

Bereinigte Endfassung des Arbeitsentwurfs vorhanden (8 Punkte). Keine stille Drift.

*Kanonisierungen:*

- Quellenstruktur, Konsenslogik, Kutub-as-Sitta, decision_event-Zuordnung, Vokalisierungsprinzip kanonisiert. Integrationsblöcke A-1–A-5 und B-1–B-4 eingearbeitet.

- Quellenlage erweiterte Menge konsolidiert (E-1, E-2, E-3, E-4 suspendiert; E-5 in Sonderrolle), Ausschluss hadithportal.com, Auswirkung auf Eskalationslogik.

- Vokalisierungs-Eskalationskriterium V-0/V-1/V-2 in §4.16; Hadith-Verifikationsstatus N-1 bis N-10 / H-0/H-1/H-2 in §4.16; Gate-Verortung als eigene benannte Gruppe innerhalb der Gate-Prüfungsschicht in §4.7; Datenmodell Mehrquellen-Ergebnisobjekte in vier logischen Ebenen mit quellen_rolle als Pflicht-Snapshot, abgeleiteten Zuständen und Unveränderlichkeit analog §4.9 E-10 in §4.16 / Kapitel 5.

- Teilkanonisiert: K-4 R-1/R-2 (englischsprachige Website-Übersetzungen als sprachneutrales Referenz- und Vergleichsfeld in §4.16 / §5.1.1).

*Status Schnittstelle 5 insgesamt:*

- Quellenfront abgeschlossen.

- Zentrale Schnittstelle-5-Semantik (Vokalisierungs-Eskalation, Verifikationsstatus-/Preflight-Verortung, Mehrquellen-Datenmodell) kanonisiert.

- Englischer Strang R-1/R-2 teilkanonisiert.

- Restliche technische Ausarbeitung (Suchmodi, Nutzerlogik-Details, Nachvollziehbarkeits-Feinarbeit, K-4 R-3 des englischen Strangs) bleibt Arbeitsentwurf.

*Werkbank weiterhin mitgetragen:* Neun Block-3-Volltext-Arbeitsstände zu Schnittstelle 5:

1.  Technische Zugriffsspezifikation H5

2.  Vorverifikation sunnah.com / dorar.net

3.  Vorverifikation islamweb.net

4.  Vorverifikation <span dir="rtl">جَامِعُ الكُتُبِ التِّسْعَة</span>

5.  Vorverifikation <span dir="rtl">مَوْسُوعَةُ الأَحَادِيثِ النَّبَوِيَّة</span>

6.  Identifikation / Klärung E-2

7.  E-5-Testbetrieb

8.  Englischer Hadith-Strang

9.  Reale Shamela-Ist-Aufnahme Hadith-Bezug

Die kanonisierten Teilbereiche Vokalisierungs-Eskalationskriterium, Preflight-Verortung Hadith-Verifikationsstatus und Datenmodell Mehrquellen-Ergebnisobjekte sind nicht mehr Teil der Werkbank, sondern Teil des Kanons (§4.16 / §4.7 / §5.1.1 / §5.1.2).

*Verbleibende Restoffenheiten:*

- Testbetriebsfragen zu E-5 (API-Feldstruktur, Harakāt-Rückgabe, HTML-Markup, Rate-Limit, Versionierungsmechanik, Bulk-Download-Feldumfang).

- Im β-Testbetrieb sind Werkbank-Teilbefunde zu F-1 bis F-16 erhoben (keine Kanonwirkung; siehe E-5-Testbetriebs-Arbeitsblock).

*Englischer Hadith-Strang K-4 R-3 – differenzierter Werkbank-Stand:*

- Strukturell aus bestehendem Kanon ableitbar und nicht mehr eigenständige Werkbank-Frage:

  - Quellenangabe-Format EN (§4.16 bereits kanonisch)

  - Transliteration (§2.2 EI2 mit Q/J sprachpaar-unabhängig)

  - Verhältnis zu Schnittstelle 3 (§3.6-Rollenlogik sprachpaar-unabhängig gemäss §8-Verifikationsblock-Eintrag zum Nicht-AR-Ausgangssprachen-Verhalten; eigener Primärproduktionspfad und Keine-Kaskade-Regel gemäss §4.16)

- Echte Werkbank und weiterhin blockiert:

  - Fussnotenlogik im englischen Strang (keine belastbare Grundlage im aktuellen Material)

  - Verhältnis zum Stilfeature bei englischer Ausgabe (an blockierte E-1–E-8-Front gekoppelt)

*Weitere Werkbank-Punkte:*

- Reale Shamela-Ist-Aufnahme (für P-2-Anschluss, geparkt).

- Operative Peripheriefragen (F-2 bis F-6 der Restoffenheiten-Matrix).

- Live-Testpaket für F-1 / F-4 / F-9 / F-13 / F-14 / F-16 sowie konkrete Werte zu F-3 und F-4: als separater Volltext-Arbeitsblock „Schnittstelle 5 – Live-Testpaket (geparkt)" in Block 3 geführt; geparkt bis zur realen Ausführung.

**Schnittstelle 6 – Shamela-/Lexikon-Schnittstelle:**

Endfassung 5 liegt als vollständiger separater Volltext-Arbeitsstand vor. Massgeblich ist die detaillierte Fassung (nicht die kompaktere gebündelte Kurzfassung). Zusammen mit den drei Schnittstelle-6-Arbeitsblöcken (Technische Zugriffsschicht T6-1–T6-6, Verifikationsrahmen A-1–A-6 / V-1–V-10, Prüfprotokoll reale Ist-Aufnahme Schritt 1–4) und dem Arbeitsblock Rückspiel- und Auswertungslogik Shamela-Ist-Aufnahme bildet Endfassung 5 den vollständigen aktuellen Arbeitsstand von Schnittstelle 6.

Status: Arbeitsentwurf, noch kein Kanon. Keine Einarbeitung in Dokument 1. Keine stille Kanonisierung.

Die reale Shamela-Ist-Aufnahme ist auf unbestimmte Zeit geparkt und wird erst dann wieder bearbeitet, wenn der Nutzer sie ausdrücklich wieder aufgreift. Bis dahin keine weitere substanzielle Theoriearbeit an der Shamela-Zugriffsschicht und keine stille Vorwegnahme von Ergebnissen, die reale Prüfung voraussetzen.

**Arbeitsblock – Schnittstelle 6 – Rückspiel- und Auswertungslogik Shamela-Ist-Aufnahme:** Separater Volltext-Arbeitsstand. Status: Arbeitsentwurf, noch kein Kanon. Funktion: schliesst die Lücke zwischen ausgefülltem Prüfprotokoll und strukturierter Rückführung der realen Ist-Aufnahme in den Arbeitsstand. Definiert Übernahme-, Auswertungs- und Folgepfad-Logik (R-1 bis R-7). Keine Ergebnisse vorweggenommen. Keine Architekturänderung.

**Arbeitsblock – Schnittstelle 6 – Operative Durchführungsvorlage Shamela-Ist-Aufnahme:** Separater Volltext-Arbeitsstand. Status: operatives Hilfsdokument, kein Kanon. Enthält Durchführungsanleitung (Schritt 1–4), Erhebungsvorlage und Rückgabeformat. Keine Ergebnisse enthalten.

**Arbeitsblock – Technische Zugriffsspezifikation Schnittstelle 4 – Qurʾān-Schnittstelle:** Separater Volltext-Arbeitsstand. Status: Arbeitsentwurf, noch kein Kanon. API-Endpunkte aus öffentlicher Dokumentation verifiziert. 10 offene Punkte explizit dokumentiert (Q4-9).

**Modellzuweisung:**

- §3.6 Übersetzungs-Pipeline: kanonisch bestätigt (Primär GPT-4o / Prüf Gemini 2.5 Pro). Vorläufig kanonisch und revidierbar gemäss §3.6 Revidierbarkeits-Satz bei Auftreten neuerer oder klar besserer Modelle (auch innerhalb derselben Familie) in einem strukturierten Entscheid. Rollenlogik und Trennung zur OCR-Stufe-3-Zuweisung bleiben unberührt.

- §3.4 OCR-Stufe 3: kanonisch bestätigt (GPT-4o + Gemini 2.5 Pro parallel als Konsens-Signalgeber innerhalb der KI-Validierungslinie; keine Primär/Prüf-Rollen; Uneinigkeit priorisiert die Stelle ins OCR-Review, kein künstlicher Sieger). Vorläufig kanonisch und revidierbar analog §3.6 bei neueren oder klar besseren Modellen (auch innerhalb derselben Familie) in einem strukturierten Entscheid; keine stille Modellwechsel-Änderung. Revision betrifft ausschliesslich die Modellwahl, nicht die Konsens-Architektur.

**Schnittstelle 7 und weitere:** noch nicht begonnen.

**Alle externen Quellen im Einzelnen** (Endpunkte, Auth, Rate-Limits, Fehlerverhalten, Scraping): unspezifiziert – aktive Arbeitsfront.

#### **2G – Schnittstelle 6 – Stabilisierter Analyseebenen-Stand**

Drei Ebenen vor dem lexikalischen Fussnoten-Eintrag:

**Ebene 1 – Morphologische Kurzanalyse:** Kompakte Wortidentifikation (Wort, Wurzel, Wortart, Wazn, Kurzbedeutung). Keine Projektwirkung. Kurzbedeutung ist reine Nutzer-Orientierung, nicht Teil der Suchlogik.

**Ebene 2 – Lexikonlage:**

- Arabischer Originalausschnitt immer sichtbar.

- Treffer pro Quelle separat (Lisān / Tāj).

- Optionale deutsche Arbeitshilfe (KI-generiert, klar markiert).

- Drei-Stufen-Klassifikation:

  - lexikalisch abgesichert

  - indirekt abgesichert

  - manuell ohne belastbare Lexikonabsicherung

- Suchpfad-Transparenz bei indirekter Evidenz.

**Quellenbasis-Auswahl (Zwischenschritt vor Ebene 3):**

- Optionen: nur Lisān / nur Tāj / beide / eigene manuelle Synthese.

- Pflicht, wenn beide Quellen Treffer haben.

- Bei Treffer in nur einer Quelle: Quellenbasis-Auswahl entfällt; die betreffende Quelle ist die allein verfügbare Quellenbasis.

**Ebene 3 – Fussnoten-Generator:**

- Vordefinierter oder benutzerdefinierter Stil.

- Bei Bestätigung: Fussnote wird angelegt und Registereintrag in Kategorie „Lexikalische Einträge" automatisch erzeugt.

- Zusatzfrage „Auch als Terminologie-Regel vormerken?" (optional).

- Quellenabsicherungs-Stufe als Metadatum an jeder Fussnote.

#### **2H – Schnittstelle 6 – Zugriffs- und Suchlogik**

Bereinigte vorläufige Endfassung vorhanden. Detaillierter Volltext liegt als separate Endfassung 5 vor und wird als eigenständiger Volltext-Arbeitsstand mitgetragen.

**Kernentscheidungen dieses Arbeitsblocks:**

- Shamela-Gesamtbestand = Eskalationssuchraum, nicht dritte gleichartige Lexikonquelle.

- Dreistufiger Suchlauf:

  - Stufe 1: exakt

  - Stufe 2: erweitert

  - Stufe 3a: gröbere Lexikonsuche

  - Stufe 3b: Eskalation Shamela-Gesamtbestand

- Stufe 3b wird nur auf explizite Nutzeranforderung ausgelöst (Variante B). Spätere Hybrid-Logik (Variante C) bleibt als mögliche Verfeinerung offen.

- Qualitative Prüflogik für „belastbar" als strukturierte Leitkriterien-Reihenfolge verankert (5 Dimensionen: Quellentyp, Formnähe, Bedeutungsnähe, Stützungsbreite, bei Shamela zusätzlich Werkautorität).

- Optionaler morphologisch-kontextueller Fussnoten-Entwurf als Fallback bei fehlendem Lexikontreffer – klar markiert als Arbeitshypothese, nur auf Nutzeranforderung, keine Gleichstellung mit lexikalischer Absicherung.

- Abgrenzung Fallback vs. §4.17: für diesen Arbeitsstand getrennte Stränge; Überschneidung bei Fachbegriffen ohne Treffer explizit benannt; Zusammenführung/Prioritätsregel bewusst offen gehalten.

- Shamela zwei Nutzungsmodi: Modus A (OCR-nahe, systemausgelöst), Modus B (nutzergesteuert, Lexikon-Workflow).

Status: Arbeitsentwurf, noch kein Kanon. Keine Einarbeitung in Dokument 1.

#### **2I – Wortanalyse-Panel – Arbeitsstrang (getrennt von Schnittstellen)**

- Grosser Wortpanel-Entwurf vorhanden (3 Panel-Typen: Nomen / Verb / Partikel; 4 Analyse-Schichten). Kein Kanon.

- **Nomen-Panel:** stabilisierter Arbeitsentwurf, vorläufig geparkt. Replacement-Kandidat für §4.17. Richtungsentscheidungen vorläufig übernommen:

  1.  Ersatz statt Ergänzung von §4.17.

  2.  Seitenpanel bleibt.

  3.  Wortformen-Häufigkeitsanalyse bleibt separater Modal-Dialog.

  4.  Unsicherheitslogik harmonisiert mit bestehenden Schwellenwerten (\> 85 % / 50–85 % / \< 50 %).

  5.  §4.17-Felder = Minimal-Kern; tiefe Felder kontext-/typabhängig.

- Drei Präzisierungen eingearbeitet:

  1.  Wurzel als Pflichtfeld im Kopfbereich; Block 4 nur für tiefe Ableitung.

  2.  Block 2 mit Primär- und sekundären Klassifikationen.

  3.  Kompatibilitätstabelle auf Nomen beschränkt.

- **Verb-Panel / Partikel-Panel:** noch nicht weiter ausgebaut. Folgen nach demselben Strukturprinzip.

#### **2J – Stilfeature-Integrationsnachricht Dokument C v1.1**

Dokument C v1.1 §1–§8 als Integrationsrahmen formal bestätigt:

- Einordnung in Waraq-Kanon (§1).

- Bestätigung Keine-Überschreibung bestehender Systemregeln inkl. Subordinierung manueller Stilregeln (§2 mit \[KANON\]-Markern §2.1 und §2.2).

- Kanonisch / Konfigurierbar / Kalibrierbar – Gesamtübersicht (§4).

- Konflikte-Ausschlussliste (§5).

- Accountbindungs-Grundsatz mit \[KANON\]-Marker §6.1 (§6).

- Reihenfolge der Folgeschritte orientierend (§7.3).

Keine Baseline-Verschiebung, keine Implementierungsfreigabe, keine neue Architektur. Keine Änderung an Dokument 1; die drei \[KANON\]-markierten Grundsätze sind bereits in Dokument 1 §4.12 (Vorranglogik Stilfeature) und §5.2 (Accountbindung) verankert.

Die in Dokument C v1.1 §3 genannten Folgearbeiten (formale Integrationsanalyse §3.1, CRs §3.2, neue Kernobjekt-Integration in Baselines §3.3, Audit-Integration §3.4) bleiben ausdrücklich offen und werden nicht still vorweggenommen.

## **4. NÄCHSTE ARBEITSFRONT**

### **4.1 Priorität 1 – Externe Quellen vollständig spezifizieren**

- Schnittstellen-Arbeitsentwürfe 1–6 vorhanden (Volltexte als separate Endfassungen mitgetragen).

- OCR-Maximum-Qualitätslogik als eigene Endfassung vorhanden.

**Schnittstelle 4:** Technische Zugriffsspezifikation als Arbeitsentwurf erstellt (Q4-1 bis Q4-9). Kritischer offener Befund (arabischer Referenztext über API) dokumentiert. 10 offene Punkte explizit benannt.

**Schnittstelle 6:** Endfassung 5 liegt als vollständiger Volltext-Arbeitsstand vor. Zusammen mit den drei Schnittstelle-6-Arbeitsblöcken (Technische Zugriffsschicht, Verifikationsrahmen, Prüfprotokoll), dem Arbeitsblock Rückspiel-/Auswertungslogik und der operativen Durchführungsvorlage bildet sie den vollständigen aktuellen Arbeitsstand von Schnittstelle 6.

**Reale Shamela-Ist-Aufnahme für Schnittstelle 6:** geparkt. Kein aktiver nächster operativer Schritt. Wird erst wieder bearbeitet, wenn der Nutzer sie ausdrücklich wieder aufgreift. Solange die Ist-Aufnahme geparkt ist, gilt:

- keine weitere substanzielle Theoriearbeit an der Shamela-Zugriffsschicht

- keine Rückspielung / Auswertung R-1 bis R-7

- kein hadithbezogener P-2-Abgleich

Die Stufe-S-1-Erwartung für P-2 bleibt ausdrücklich Arbeitshypothese und wird nicht still hochgestuft.

**Schnittstelle 5 – Status:**

- Quellenfront abgeschlossen. Pflichtmenge P-1/P-2/P-3 unverändert.

- Erweiterte Menge kanonisch konsolidiert (E-1/E-2/E-3/E-4 Option B suspendiert; E-2 hoch belastbar identifiziert als Alifta-/Harf-Variante; E-3 nur noch als mögliche manuelle Referenzquelle; E-5 Option B nicht suspendiert in Sonderrolle „deutsche Übersetzungsquelle / mehrsprachige Referenzquelle"). hadithportal.com ausdrücklich ausgeschlossen.

- Strukturelle Nachzüge A-4 / A-6 / A-7 / A-8 kanonisiert.

- Live-/API-testabhängige Restpunkte (E-5-Testbetriebsfragen F-1 / F-4 / F-9 / F-13 / F-14 / F-16; F-3 konkrete Werte; F-4 konkrete Werte) geparkt bis zur realen Ausführung; zugehöriger ausführungsreifer Testlauf-Block als separater operativer Volltext-Arbeitsblock „Schnittstelle 5 – Live-Testpaket (geparkt)" in Block 3 geführt.

- Vokalisierungs-Eskalationskriterium, Preflight-Verortung Hadith-Verifikationsstatus und Datenmodell Mehrquellen-Ergebnisobjekte bleiben kanonisiert.

- Teilkanonisierung K-4 R-1/R-2 bleibt kanonisiert.

**K-4 R-3 differenziert:**

- Aus dem bestehenden Kanon sauber ableitbar und nicht mehr als eigenständige Werkbank-Fragen geführt: Quellenangabe-Format EN, Transliteration, Verhältnis zu Schnittstelle 3 (eigener Primärproduktionspfad aus dem arabischen Matn, strukturell gleichwertig zum deutschen Pfad, Keine-Kaskade-Regel, §3.6-Rollenlogik sprachpaar-unabhängig).

- Werkbank, nicht still nachgezogen: Fussnotenlogik im englischen Strang und Verhältnis zum Stilfeature bei englischer Ausgabe. Wiederaufnahme dieser zwei Teilpunkte erfordert belastbare Grundlage für die englische Fussnotenkonvention bzw. den Wortlaut von Dokument C v1.1 für das Stilfeature-Verhältnis.

- Die konkrete englische Qurʾān-Übersetzung auf Translation-Key-Ebene (§4.15) bleibt davon unberührt geparkt.

**Reale Shamela-Ist-Aufnahme für P-2:** geparkt. Der hadithbezogene P-2-Abgleich bleibt geparkt und folgt zeitlich der Wiederaufnahme der realen Ist-Aufnahme.

**Fazit:** Keine aktive offene Schnittstelle-5-Arbeitsfront mit dem aktuell vorliegenden Material.

### **4.2 Priorität 2 – erledigt**

Die formale Bestätigung der Stilfeature-Integrationsnachricht Dokument C v1.1 (§1–§8) ist abgeschlossen (siehe §3 Klasse 1, Eintrag 2J). Die §3-Folgearbeiten aus Dokument C v1.1 bleiben ausdrücklich offen und werden ohne ausdrücklichen Nutzerauftrag nicht gezogen.

### **4.3 Geparkt (kein aktiver Ausbau)**

- **Wortpanel-Strang:** Nomen-Panel stabilisiert und geparkt. Verb-/Partikel-Panel erst nach Wiederaufnahme.

- **Reale Shamela-Ist-Aufnahme Schnittstelle 6 inkl. Rückspielung/Auswertung R-1 bis R-7 und hadithbezogenem P-2-Abgleich:** geparkt. Wird erst wieder bearbeitet, wenn der Nutzer sie ausdrücklich wieder aufgreift. Keine stille Vorwegnahme realer Ergebnisse. Stufe-S-1-Erwartung für P-2 bleibt Arbeitshypothese. Der Konsolidierungsstand der erweiterten Menge bleibt von späteren realen Ergebnissen unberührt, solange keine ausdrückliche Wiederaufnahme erfolgt.

- **Schnittstelle 5 – Live-Testpaket** (E-5-Testbetriebsfragen F-1 / F-4 / F-9 / F-13 / F-14 / F-16; F-3 konkrete Werte; F-4 konkrete Werte): geparkt bis zur realen Ausführung; als separater Volltext-Arbeitsblock „Schnittstelle 5 – Live-Testpaket (geparkt)" in Block 3 geführt. Wird erst wieder bearbeitet, sobald ein ausgefülltes Rückgabeformat aus realer Messung vorliegt.

- **L-24 Häufungsschwellenwerte Klasse-B-Generallogik:** struktureller Mechanismus kanonisch in §4.18; konkrete Schwellenwerte an das Live-Testpaket gekoppelt (F-3 Häufungsschwelle §4.18 Spur 2) und bleiben geparkt bis zur realen Messung.

### **4.4 Separat offen (ohne Prioritätsnummer)**

- L-24 konkrete Häufungsschwellenwerte der Klasse-B-Generallogik: weiterhin offen, live-messungsabhängig und an das geparkte Schnittstelle-5-Live-Testpaket gekoppelt. Der strukturelle Mechanismus der Klasse-B-Generallogik ist in §4.18 kanonisch: aggregierte Nutzerinformation über Dashboard-Statusindikator bei Häufung gemäss Spur 2; bestehende Spezialfälle bleiben unberührt. Nicht mit dem API-Ausfall-Spezialfall verschmelzen.

## **5. SPÄTERE IDEEN / SPÄTERE MÖGLICHE FEATURES**

- Adobe InDesign / Affinity Publisher Export.

- Weitere Sprachen (Französisch, Türkisch) und Quellsprachen (Persisch, Osmanisch).

- Plugin-System.

- Eigenes Word-Dokument hochladen als Export-Ziel.

- Enterprise-Verträge mit OpenAI / Google.

- Weitere Layout-Templates.

- Kollaboration / Kommentar-System.

- Automatisierter Fehlerbehebungsprozess (Grundstruktur beschlossen, Details offen).

## **6. NOCH NICHT ERLAUBTE DINGE**

- Kein Code ohne explizite Coding-Freigabe.

- Keine stillen Architekturänderungen.

- Keine neue Sprint-Planung ohne expliziten Auftrag.

- Keine neuen Features ohne vollständigen CR-Durchlauf.

- Kein stilles Re-Baselining.

- Keine Umformulierung des bestehenden Kanons.

- OCR-Export-Strang bleibt vom Stilfeature getrennt.

- Keine Coding-Freigabe, bevor externe Quellen vollständig spezifiziert sind.

- Wortpanel-Strang nicht mit Schnittstellen-Strang verschmelzen.

## **7. PERSÖNLICHES PROFIL DES NUTZERS**

- Professioneller Übersetzer arabischer islamischer Werke ins Deutsche.

- Übersetzt primär klassische islamische Literatur, Fiqh-Texte, historische Manuskripte.

- Tiefes Fachwissen über arabische Sprache, islamische Wissenschaften und Übersetzung.

- Sitzt in Medina (Saudi-Arabien).

- Denkt sehr strukturiert und präzise – erwartet dasselbe.

- Erwartet proaktives Qualitätsdenken – nie warten, bis er fragt.

- Gibt klare Korrekturen – direkt annehmen ohne übermässige Entschuldigung.

- Spricht Deutsch (Schweizer Stil: „ss" statt „ß").

- Arbeitet iterativ: definieren → prüfen → freigeben → weiter.

## **8. VERIFIKATIONSBLOCK FÜR NEUEN CHAT**

**Vorranglogik Stilfeature?** Rang 1: Systemregeln. Rang 2: Nutzerstil (Dokument A + Dokument B v1.2). Rang 3: Referenzsätze.

**T-7.3.1 / T-7.3.2?** Baseline-seitig vollständig definiert (Delivery Backlog Baseline v1.0). Sprint-Verortung bewusst bedingt (T-7.3.1 optional in Sprint 2, T-7.3.2 bedingt in Sprint 3, falls T-7.3.1 vorhanden). Keine Implementierungsfreigabe.

**E-1 bis E-8 Stilfeature?** Aufgelöst. Für diesen Arbeitsstand wird die Kennung „E-1 bis E-8" als Bezeichnung der acht Hauptabschnitte §1–§8 von Dokument C v1.1 behandelt. Dokument C v1.1 als Integrationsrahmen formal bestätigt. §3-Folgearbeiten (Integrationsanalyse, CRs, Ticket-Definition, Sprint-Planung, Audit-Integration, Kalibrierung, Coding-Freigabe) bleiben ausdrücklich offen. Keine Änderung an Dokument 1.

**OCR-Export vs. Stilfeature?** Absolut getrennt.

**Ohne Coding-Freigabe?** Kein Code, keine Implementierung.

**Formatvorlagen-Quelldatei?** FINAL.docx – alle Werte in Baseline v1.1 kanonisch.

**Grösste offene Lücke vor Code?** Externe Quellen nicht spezifiziert. Schnittstellen-Arbeitsentwürfe 1–6 vorhanden (Volltexte als separate Endfassungen mitgetragen), noch kein Kanon.

**Audit-Matrix Status?** Baseline-basiert abgeglichen. P-03 und P-04 kanonisch bestätigt.

**Stilprofil teilbar?** Nein. Absolut accountgebunden.

**L-24 Status?** Strukturell kanonisiert in §4.18 (aggregierte Nutzerinformation über Dashboard-Statusindikator bei Häufung gemäss Spur 2; Spezialfälle unberührt). Konkrete Häufungsschwellenwerte live-messungsabhängig; an das geparkte Live-Testpaket gekoppelt.

**Modellzuweisung Übersetzungs-Pipeline?** Kanonisch bestätigt für §3.6: Primär GPT-4o, Prüf Gemini 2.5 Pro. Systemweit. Rollenlogik unverändert. Vorläufig kanonisch, revidierbar in einem strukturierten Entscheid bei neueren oder klar besseren Modellen (auch innerhalb derselben Familie); keine stille Modellwechsel-Änderung.

**Modellzuweisung OCR-Stufe 3 (§3.4 semantische Rekonstruktion)?** Kanonisch bestätigt: GPT-4o + Gemini 2.5 Pro parallel als Konsens-Signalgeber innerhalb der KI-Validierungslinie. Keine Primär/Prüf-Rollen. Uneinigkeit beider Modelle wirkt nicht als künstlicher Sieger, sondern senkt die Konfidenz und priorisiert die Stelle ins OCR-Review gemäss §3.4-Qualitätsprinzip. Vorläufig kanonisch, revidierbar analog §3.6 in einem strukturierten Entscheid bei neueren oder klar besseren Modellen (auch innerhalb derselben Familie); keine stille Modellwechsel-Änderung. Revision betrifft ausschliesslich die Modellwahl, nicht die Konsens-Architektur.

**Qurʾān-Stellenbehandlung?** Kanonisiert in §4.15. Vier Handlungstypen plus Auto-Akzeptanz. decision_source translation_pipeline bei Bestätigung und bei ausdrücklicher Nutzeraktion zur Aktualisierung einer bereits gespeicherten Qurʾān-Stelle; conflict_resolution bei Korrektur und Ablehnung. Auto-Akzeptanz ohne decision_event. Keine neuen decision_source-Werte.

**Übersetzungs-KI – Ausklammerung akzeptierter Qurʾān-Stellen?** Akzeptierte Qurʾān-Stellen gemäss §4.15 werden als geschützte Stellen geführt. Ausgeklammert wird die akzeptierte Qurʾān-Stelle selbst, nicht der umgebende Chunk. Kanonischer arabischer Referenztext und kanonische Zielsprachen-Übersetzung kommen aus den Trägersträngen gemäss §4.15. Glossar, Stilprofil und RAG wirken nicht auf die geschützte Stelle. Der übrige Übersetzungsfluss bleibt unberührt. Die Hadith-Seite ist nicht Gegenstand dieser Regelung.

**Schnittstelle 1 / 2 – Bereinigung gegen §3.4?** KI-basierte Validierung ist eine der drei §3.4-Stufe-3-Validierungslinien. Innerhalb der KI-Linie: GPT-4o und Gemini 2.5 Pro als gleichrangige Konsens-Signalgeber, keine Primär/Prüf-Rollen, kein künstlicher Sieger bei Uneinigkeit innerhalb der KI-Linie, Revidierbarkeit analog §3.6. OCR-Qualitätsprinzip §3.4 greift bei mehreren starken konkurrierenden Lesungen nach Durchlauf der Rekonstruktionsstufen. Konkrete Gewichtungs- und Auslösematrix zwischen den drei Linien offen.

**Preflight-Schichten?** Konfigurationspflichten (4 Pflichtfragen) und Gate-Prüfungen konzeptionell getrennt.

**P-03 Status?** Eigenständiges blockierendes Gate, gleichrangig neben P-04. Bestätigt.

**W-01 / W-02 / W-03?** Minimalmodell II bestätigt. W-01 = Mittel-Audit-Befunde. W-02 = K-01–K-07. W-03 = Graduelle Formatvorlagen-Abweichungen.

**W-04 bis W-08?** Offen. Keine sauberen Kandidaten im bestehenden Kanon. Keine Richtungsbindung.

**P-01–P-02 / P-05–P-06?** Belegungslogik bestätigt. Keine sauberen Kandidaten. Slots offen.

**Kritische Schriftart-Verfügbarkeit?** Kanonisch bestätigt als Guard-nah vor Preflight-Dialog. Kein P-Slot belegt.

**Schnittstellen-Arbeitsentwürfe?** 1 (OCR-Hauptengine), 2 (OCR-semantische Zusatzvalidierung), 3 (Übersetzungs-KI), 4 (Qurʾān), 5 (Hadith), 6 (Shamela/Lexikon) – alle als Arbeitsentwurf vorhanden, Volltexte als separate Endfassungen mitgetragen, noch kein Kanon. OCR-Maximum-Qualitätslogik als eigene Endfassung vorhanden. Google Cloud Vision (DOCUMENT_TEXT_DETECTION) ist im Kanon als zusätzliche OCR-Leselinie ergänzt; die konkrete Primärrolle und Gewichtung bleibt Gold-Corpus-abhängig. Technische Zugriffsspezifikation Schnittstelle 4 als separater Volltext-Arbeitsstand vorhanden.

**Schnittstelle 4 Besonderheit?** Punkt 5 präzisiert: lokale Fallback-Basis = vollständiger Qurʾān-Datenstand. Technische Zugriffsspezifikation (Q4-1 bis Q4-9) als Arbeitsentwurf vorhanden. Kritischer offener Befund: API liefert nur Übersetzungen, nicht arabischen Referenztext (Variante A als Arbeitshypothese). 10 offene Punkte dokumentiert.

**Schnittstelle 5 – Kanonisierungsstand?** Quellenfront abgeschlossen. Fünf Teilbereiche aus der Hadith-Integration kanonisiert. Pflichtmenge P-1/P-2/P-3 unverändert. Erweiterte Menge kanonisiert: E-1, E-2 (hoch belastbar identifiziert als Alifta-/Harf-Variante), E-3 (nur manuelle Referenzquelle), E-4 jeweils nach Option B dokumentiert, faktisch suspendiert. E-5 nach Option B nicht suspendiert, in Sonderrolle „deutsche Übersetzungsquelle / mehrsprachige Referenzquelle" (keine Korpus-Ersatzquelle, kein API-Volltextsuchpfad, Anschluss über offizielle API und offizielle Bulk-Downloads). hadithportal.com ausdrücklich ausgeschlossen. Kanonisiert: Vokalisierungs-Eskalationskriterium V-0/V-1/V-2; Hadith-Verifikationsstatus N-1 bis N-10 / H-0/H-1/H-2; Gate-Verortung Hadith-Verifikationsstatus als eigene benannte Gruppe innerhalb der Gate-Prüfungsschicht; Datenmodell Mehrquellen-Ergebnisobjekte in vier logischen Ebenen. Teilkanonisiert: K-4 R-1/R-2 (englischsprachige Website-Übersetzungen als sprachneutrales Referenz- und Vergleichsfeld). Neun Block-3-Volltexte weiterhin als Werkbank mitgetragen. Offen bleiben insbesondere: Testbetriebsfragen zu E-5, englischer Strang K-4 R-3, verbleibende operative Peripheriefragen, reale Shamela-Ist-Aufnahme (aus Schnittstelle 6, geparkt).

**Nächster Arbeitsschritt?** Verdichtung und Abschluss der verbleibenden echten Restoffenheiten Schnittstelle 5 (E-5-Testbetriebsfragen, englischer Hadith-Strang K-4 R-3, verbleibende operative Peripheriefragen). Reale Shamela-Ist-Aufnahme, Rückspielung R-1 bis R-7 und hadithbezogener P-2-Abgleich sind geparkt und nicht Teil der aktiven Arbeitsfront.

**Arbeitsentwürfe vorhanden?** Ja – Volltexte als separate Endfassungen 1–5 mitgetragen. Zusätzlich:

- Fünf Schnittstelle-6-Arbeitsblöcke (Technische Zugriffsschicht, Verifikationsrahmen, Prüfprotokoll, Rückspiel-/Auswertungslogik, operative Durchführungsvorlage).

- Ein Schnittstelle-4-Arbeitsblock (Technische Zugriffsspezifikation Q4-1 bis Q4-9).

- Neun Schnittstelle-5-Arbeitsblöcke (Technische Zugriffsspezifikation Hadith, Vorverifikation sunnah.com / dorar.net, Vorverifikation islamweb.net, Vorverifikation <span dir="rtl">جَامِعُ الكُتُبِ التِّسْعَة</span>, Vorverifikation <span dir="rtl">مَوْسُوعَةُ الأَحَادِيثِ النَّبَوِيَّة</span>, Identifikation/Klärung E-2, E-5-Testbetrieb, englischer Hadith-Strang, reale Shamela-Ist-Aufnahme Hadith-Bezug).

Der H5-Arbeitsstand enthält die bereinigte Einarbeitung der sunnah-/dorar-Befunde. islamweb, <span dir="rtl">الوقفية</span>, E-4 und E-2 sind als dokumentierte Suspendierungsbefunde separat festgehalten; E-5 ist als nicht suspendierte Sonderrolle separat festgehalten. Nicht nur referenziert.

**Schnittstelle 6 – aktueller Stand?**

- Analyseebene (3 Ebenen + Quellenbasis-Auswahl) stabilisiert.

- Zugriffs-/Suchlogik als bereinigte vorläufige Endfassung abgeschlossen (detaillierte Fassung massgeblich).

- Endfassung 5 liegt als vollständiger Volltext-Arbeitsstand vor.

- Drei Schnittstelle-6-Arbeitsblöcke (Technische Zugriffsschicht, Verifikationsrahmen, Prüfprotokoll), Arbeitsblock Rückspiel-/Auswertungslogik und operative Durchführungsvorlage als weitere Volltext-Arbeitsstände mitgetragen.

- Schnittstelle 6 als Arbeitsstand vollständig.

- Reale Shamela-Ist-Aufnahme geparkt; wird erst wieder bearbeitet, wenn der Nutzer sie ausdrücklich wieder aufgreift.

- Rückspielung R-1 bis R-7 und hadithbezogener P-2-Abgleich damit ebenfalls geparkt.

- Weiterhin Arbeitsentwurf, noch kein Kanon.

**Wortpanel-Strang?** Eigener Arbeitsstrang, getrennt von Schnittstellen. Nomen-Panel stabilisiert, geparkt, Replacement-Kandidat für §4.17. Verb-/Partikel-Panel noch nicht ausgebaut.

**Hadith-Integrationsblöcke?** Eingearbeitet. Abgeschlossen.

**Prüf-Modell-Korrekturrecht?** Vier Situationstypen. Objektiv-deterministisch → Auto-Korrektur (protokolliert). Interpretativ → Konfidenz sinkt, Review. Ambiguität → Nutzerhinweis. Modellzuweisung offen.

**Stiller Rollentausch Übersetzungs-KI?** Verboten. Primär fällt aus → Chunk wartet. Prüf fällt aus → Primär weiter, betroffene Stellen gelten als nicht gegengeprüft.

**Audit-Befunde im Übersetzungsflow?** Stoppen den Flow nicht. Werden persistiert und in Preflight weitergeführt.

**Qurʾān-Vokalisierung nach Erkennung?** Getrennte Trägerstruktur. Arabischer Qurʾān-Referenzbestand = alleiniger Textträger für arabischen Referenztext und Vokalisierung; eigenständiger lokaler Bestand, unabhängig von Übersetzungs-Fallback-Kopien; zu keinem Zeitpunkt API-gestützt. quranenc.com (bzw. lokale Fallback-Kopie der german_rwwad-Übersetzung bei API-Ausfall) = alleiniger Textträger für die deutsche Übersetzung. Kein Wahlfall. Nur Erkennungsfrage prüfbedürftig. Konkrete Quellenbenennung des AR-Referenzbestands und dessen Update-Mechanismus noch offen (Schnittstelle-4-Detailpunkte).

**Qurʾān-API-Ruf wann?** Erst in Übersetzungsphase. Kein externer Ruf im OCR-Lauf.

**Qurʾān-Konfidenz unter Schwelle?** Manuelle Bestätigung vorgelagert. Schwellenwert offen.

**Qurʾān-Projektstellen bei Update der lokalen Kopie?** Bleiben unverändert. Kein stilles Überschreiben.

**Shamela Modi?** Modus A = OCR-intern (Stufe 3). Modus B = nutzergesteuert, Lexikon-Workflow in der Übersetzungsphase.

**Shamela Lisān/Tāj?** Eigenständig abfragbare Einheiten innerhalb Shamela.

**OCR ungelöste Mehrdeutigkeit?** Kein künstlicher Sieger nach Durchlauf der vorgesehenen Rekonstruktionsstufen. Konfidenz sinkt, Review priorisiert.

**Hadith-Quellenstruktur?** Zweistufig: Pflicht (sunnah.com, Shamela, dorar.net) + erweitert (E-1 islamweb.net, E-2 <span dir="rtl">جَامِعُ السُّنَّةِ النَّبَوِيَّة</span> hoch belastbar identifiziert als Alifta-/Harf-Variante, E-3 <span dir="rtl">المكتبة الوقفية</span> als bewusster Eskalationsquelle, E-4 <span dir="rtl">جَامِعُ الكُتُبِ التِّسْعَة</span>, E-5 <span dir="rtl">مَوْسُوعَةُ الأَحَادِيثِ النَّبَوِيَّة</span>). Konsolidierungsstand der erweiterten Hadith-Quellenmenge: E-1, E-2, E-3, E-4 nach Option B dokumentiert, faktisch suspendiert; E-3 nur noch als mögliche manuelle Referenzquelle. E-5 nach Option B nicht suspendiert, in Sonderrolle „deutsche Übersetzungsquelle / mehrsprachige Referenzquelle" (keine Korpus-Ersatzquelle, kein API-Volltextsuchpfad, Anschluss über offizielle API und offizielle Bulk-Downloads). hadithportal.com ausdrücklich ausgeschlossen. Eskalationslogik: bei automatischer Zuschaltung faktisch nur E-5 wirksam.

**Hadith-Konsenslogik?** Mehrdimensional. Lineares Ranking als Tie-Breaker.

**Kutub-as-Sitta?** Starker Gewichtungsfaktor, kein absoluter Vorrang.

**Hadith decision_events?** 7 Handlungstypen → translation_pipeline (2) + conflict_resolution (5).

**Hadith-Vokalisierung?** Getrennte Felder, kein alleiniger Textträger. Konflikte → Nutzer → conflict_resolution.

**Vokalisierungs-Eskalationskriterium?** Kanonisiert. Klassen V-0 (automatisch tolerierbar), V-1 (protokollpflichtig, keine Eskalation), V-2 (eskalationspflichtig). Aggregationsregel höchste Klasse gewinnt; Rückfallregel im Zweifel V-2. Feld vokalisierungs_konflikt strikt binär (nein / ja); Klassen-Differenzierung ausschliesslich über die abgeleitete vokalisierungsklasse. Bei unklarer Typ-Zuordnung bleibt das Feld auf ja; die Unklarheit wird nur im Logging bzw. in der Konfliktbegründung dokumentiert.

**Hadith-Verifikationsstatus?** Kanonisiert. Stellentypen N-1 bis N-10. Verifikationsklassen H-0 (review-intern tolerierbar), H-1 (protokollpflichtig, warnungsfähig), H-2 (export-blockierend bis Auflösung). Auflösung ausschliesslich über die 7 kanonisierten Handlungstypen. Kein Audit-Fall. Markierung „für spätere Klärung" hebt H-2 nicht auf.

**Gate-Verortung Hadith-Verifikationsstatus?** Kanonisiert. Eigene benannte Gruppe innerhalb der bestehenden Gate-Prüfungsschicht gemäss §4.7. Keine neue Schicht. Keine Belegung offener P-/W-Slots. H-2 blockierend; H-1 warnungsbasiert mit go_with_warning analog §4.9 E-1, decision_source preflight_confirmation.

**Datenmodell Hadith-Mehrquellen-Ergebnisobjekte?** Kanonisiert. Vier Ebenen (Stellenanker / Einzelquellen-Lesung / Aggregiertes Gesamtergebnis / Nutzerentscheidungs-Overlay). quellen_rolle ist Pflicht-Snapshot-Feld pro Einzelquellen-Lesung (pflicht / erweitert_aktiv / erweitert_sonderrolle / erweitert_suspendiert), zum Zeitpunkt des Verifikationslaufs festgeschrieben, keine dynamische Rückableitung. Abgeleitet, nicht persistiert: entscheidungsstatus, vokalisierungsklasse, hadith_stellen_typ, hadith_verifikationsklasse. satz_uuid ist Pflicht, sobald Satzsegmentierung für die Stelle vorhanden ist. Unveränderlichkeit analog §4.9 E-10. Keine neuen Kernobjekte. Keine neuen decision_source-Werte.

**Englischer Hadith-Strang?** Teilkanonisiert (K-4 R-1/R-2): englischsprachige Website-Übersetzungen aus P-1 und E-5 als sprachneutrales Referenz- und Vergleichsfeld in §4.16 / §5.1.1. Einträge projekt-zielsprachenunabhängig. Anzeige als Vergleichssprache im Review zulässig, nicht verpflichtend, kein eigener decision_event. Keine Auswirkung auf Matn-Konsens, Referenz-Matn, Referenz-Vokalisierung, Primärübersetzung. Strukturentscheidung K-4 R-3 kanonisiert: englische Hadith-Ausgabe als eigener Primärproduktionspfad aus dem arabischen Matn, parallel und strukturell gleichwertig zur deutschen Hadith-Ausgabe; Keine-Kaskade-Regel für die Hadith-Matn-Übersetzung. Detaillierte R-3-Regeln (Quellenangabe-Format, Transliteration, Fussnotenlogik, Verhältnis zum Stilfeature und zu Schnittstelle 3) bleiben Werkbank.

**E-5-Testbetrieb?** Werkbank. β-Teilbefunde vorhanden (F-1 bis F-16); kein Kanon.

- In β verifiziert: F-1 für AR und EN (DE unklar wegen Tool-Grenze), F-2 (Harakāt vollständig in AR-API), F-3 (kein HTML in JSON-Textfeldern), F-8 (68 Sprachen).

- Teilverifiziert in β: F-6, F-7, F-12, F-15.

- Zeitabhängig offen: F-4, F-5, F-9, F-14, F-16.

- Keine β-Aussage zu F-10, F-11.

**Nicht-AR-Ausgangssprachen-Verhalten Übersetzungs-KI?** §3.6-Rollenlogik gilt sprachpaar-unabhängig für EN→DE und DE→EN. Die §4.15-Ausklammerung akzeptierter Qurʾān-Stellen ist an die akzeptierte Qurʾān-Erkennung gebunden, nicht an die Ausgangssprache; sie greift auch bei EN→DE und DE→EN, wenn an der Stelle eine akzeptierte Qurʾān-Erkennung vorliegt. Für DE→EN bleibt der konkrete englische Zielsprachen-Träger auf Translation-Key-Ebene gemäss §4.15 weiterhin offen. Hadith-Seite bei Nicht-AR-Ausgangssprachen und K-4 R-3 bleiben ausserhalb dieser Einordnung.

**Englischer Hadith-Strang K-4 R-3?** Differenzierter Werkbank-Stand. Strukturell aus bestehendem Kanon ableitbar: Quellenangabe-Format EN (§4.16), Transliteration EI2 mit Q/J (§2.2, sprachpaar-unabhängig), Verhältnis zu Schnittstelle 3 (eigener Primärproduktionspfad gemäss §4.16, §3.6-Rollenlogik sprachpaar-unabhängig gemäss vorherigem §8-Eintrag). Weiterhin Werkbank: Verhältnis zum Stilfeature bei englischer Ausgabe (an E-1–E-8 gekoppelt). Die Fussnotenlogik des englischen Hadith-Strangs ist gemäss §4.16 strukturell auf die deutsche Logik gezogen; konkrete englische Marker-Abkürzungen sind dort ausdrücklich nicht festgezogen. Keine Änderung an Dokument 1. Der englische Zielsprachen-Träger der Qurʾān-Übersetzung auf Translation-Key-Ebene ist gemäss §4.15 als english_rwwad festgelegt; lokale Fallback-Kopie analog german_rwwad. Option A (KI-Übersetzung nach definiertem Systemstil) gilt systemseitig für Deutsch und Englisch gleichermassen. Option B (Stilfeature) ist im kanonischen Spezifikationsstand auf den bestehenden AR→DE-Stilfeature-Strang ausgearbeitet (Dokument B v1.2). Das Verhältnis Stilfeature ↔ englische Ausgabe bleibt späterer eigener Nachzug im Rahmen der §3-Folgearbeiten Dokument C v1.1 und wird heute nicht still vorweggenommen.

## **VERSIONSSTAND**

**Status:** Arbeits- und Referenzdokument – bereinigte Volltextfassung. Dokument 1 bleibt unverändert als einzige kanonische Hauptquelle.

**Kanonisierungsstand:**

- Kanonisierte Teilbereiche Schnittstelle 5 sind Teil des Kanons und nicht mehr Teil der offenen Arbeitsfront: Vokalisierungs-Eskalationskriterium V-0/V-1/V-2; Hadith-Verifikationsstatus N-1 bis N-10 / H-0/H-1/H-2; Gate-Verortung als eigene benannte Gruppe innerhalb der Gate-Prüfungsschicht ohne neue Schicht und ohne P-/W-Slot-Belegung; Datenmodell Mehrquellen-Ergebnisobjekte in vier logischen Ebenen.

- Teilkanonisiert: K-4 R-1/R-2 (englischsprachige Website-Übersetzungen als sprachneutrales Referenz- und Vergleichsfeld in §4.16 / §5.1.1).

- Schnittstelle 6 liegt als Arbeitsstand vollständig vor.

**Geparkt:**

- Reale Shamela-Ist-Aufnahme: wird erst wieder bearbeitet, wenn der Nutzer sie ausdrücklich wieder aufgreift.

- Rückspielung R-1 bis R-7 und hadithbezogener P-2-Abgleich.

- Stufe-S-1-Erwartung für P-2 bleibt Arbeitshypothese und wird nicht still hochgestuft.

**Nächster inhaltlicher Arbeitsbereich** (nicht aktiver nächster operativer Schritt ohne ausdrücklichen Nutzerauftrag):

- E-5-Testbetriebsfragen

- Englischer Hadith-Strang K-4 R-3

- Verbleibende operative Peripheriefragen Schnittstelle 5

**Schutzregel:** Reale Ergebnisse aus Schnittstelle 6 dürfen den Konsolidierungsstand der erweiterten Hadith-Quellenmenge nicht still verändern. Weiterhin Arbeitsentwurf, noch kein Kanon, soweit nicht ausdrücklich kanonisiert. Keine stille Kanonisierung. Kein stilles Re-Baselining.
