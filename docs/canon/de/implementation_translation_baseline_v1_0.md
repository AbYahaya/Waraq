<!-- Converted from "Implementation Translation Baseline v1.0.docx" via pandoc 3.9.0.2 on 2026-05-02 -->
<!-- The .docx in this directory remains source-of-truth per docs/canon/README.md authority rule -->
<!-- Conversion is content-faithful (text, tables, identifiers, Swiss German ss, Arabic RTL spans, §-refs); Word-specific visual styling is dropped -->

# **WARAQ IMPLEMENTATION TRANSLATION BASELINE v1.0**

## **1. Zweck und Stellung dieser Baseline**

Die Implementation Translation Baseline v1.0 beschreibt die technische Ausgestaltung der Übersetzungs- und Prüfpfade innerhalb von Waraq. Sie ist eine der eingefrorenen Baselines und wird in Dokument 1 §3.2 ausdrücklich als solche geführt. Sie ist insbesondere die massgebliche Quelle für die vollständigen Kategorien-Definitionen und die Klassifikation der Audit-Kategorien A-01 bis D-03 gemäss Dokument 1 §4.6.

Die Kernfunktion dieser Baseline ist:

- die verbindliche Definition der Audit-Regeln A-01 bis D-03 mit Klasse, Schweregrad und Konsequenz,

- die technische Verortung der Audit- und Regel-Engine als mehrschichtiges Modell,

- die verbindliche Liste der gesperrten Aktionen auf Backend-Ebene,

- die Liste der Decision Gates, die nicht ohne aktive Nutzerquittierung weiterlaufen dürfen.

## **2. Export-Preflight (§3.7)**

### **2.1 Preflight-Zustände**

Der Export-Preflight bewegt sich zwischen folgenden Zuständen:

6.  nicht_gestartet → läuft → exportierbar \| exportierbar_mit_warnungen \| blockiert

exportierbar_mit_warnungen darf nur nach aktiver Bestätigung der offenen Warnungen durch den Nutzer erreicht werden (go_with_warning, kanonisch in §4.9 E-1 mit doppelter Warnung).

### **2.2 Preflight-Schichtenmodell**

Der Preflight-Dialog enthält zwei konzeptionell eigenständige Schichten:

**Schicht 1 – Konfigurationspflichten.** Die vier Pflichtfragen bilden eine eigenständige Konfigurationsschicht. Sie fordern notwendige Exportparameter und prüfen keinen Befund im Dokument. Sie belegen keinen P-Slot automatisch. Die vier Pflichtfragen lauten:

1.  Welche Überschriftenebene soll in der Kopfzeile angezeigt werden?

2.  Welche Überschriftenebene markiert Kapitelumbrüche?

3.  Position des Inhaltsverzeichnisses (vorne / hinten)?

4.  Arabische Kapitelüberschriften im Text anzeigen (ja / nein)?

Zusätzlich beim PDF-Export: Digital (RGB) oder Druck (PDF/X-1a, CMYK, 3 mm Beschnitt).

**Schicht 2 – Gate-Prüfungen.** Blockierende P-Gates und warnungsbasierte W-Gates prüfen Sachverhalte im Dokument oder im Exportzustand gegen definierte Bedingungen.

### **2.3 Guard-nahe Blockaden vor Preflight**

Vor Öffnung des Preflight-Dialogs werden folgende Zustände Guard-nah geprüft. Liegt ein Verstoss vor, wird der Preflight-Dialog nicht geöffnet. Keine dieser Blockaden belegt einen P-Slot.

- Ziffernstandard-Verstösse (nur westliche Ziffern): blockierend, direkter Systemmechanismus.

- Kritische RTL-Encoding- / RTL-Anwendungsfehler: blockierend als Integritätsverstoss.

- Formatvorlagen-Integritätsverstösse: blockierend; Auflösung setzt technische Beseitigung voraus.

- Kritische Schriftart-Verfügbarkeit: blockierend; Auflösung setzt technische Wiederherstellung voraus, blosse Nutzerbestätigung genügt nicht.

### **2.4 Belegte Gates in der Gate-Prüfungsschicht**

- **P-03** – Kritische Audit-Verstösse (C-01, D-03) einzeln aufgelöst. Eigenständiges blockierendes Gate, strukturell gleichrangig neben P-04.

- **P-04** – Hoch-Audit-Verstösse einzeln aktiv entschieden.

- **W-01** – Mittel-Audit-Verstösse (A-02, A-03, B-03, B-04, D-01, D-02) als Hinweise.

- **W-02** – K-01 bis K-07 Konsistenzwarnungen.

- **W-03** – Graduelle Formatvorlagen-Abweichungen.

- **Hadith-Verifikationsstatus-Gruppe** – eigene benannte Gruppe innerhalb der Gate-Prüfungsschicht, keine neue Schicht, keine Belegung offener P-/W-Slots. H-2-Stellen sind blockierend (nicht exportierbar, bis eine Auflösung über die sieben kanonisierten Handlungstypen gemäss §4.16 erfolgt). H-1-Stellen sind warnungsbasiert mit go_with_warning analog §4.9 E-1 und decision_source = preflight_confirmation gemäss §4.10. H-0-Stellen erzeugen keinen Gruppen-Eintrag.

### **2.5 Offene Gate-Slots**

- P-01, P-02, P-05, P-06: Im bestehenden Kanon des Publikationsexports derzeit keine sauberen Kandidaten identifizierbar. Slots bleiben offen.

- W-04 bis W-08: Ebenfalls keine sauberen Kandidaten. Slots offen, keine Richtungsbindung.

### **2.6 Verbotene Übergänge**

- Export ohne aktive Bestätigung aller vier Pflichtfragen (Schicht 1 von §2.2) ist nicht zulässig. Bestätigung liegt in der Konfigurationsschicht und belegt kein P-Gate.

- Pflichthinweise (Hoch-Verstösse) dürfen nicht als allgemeine Warnung passieren. Sie sind P-04-blockierend und müssen einzeln entschieden werden.

- Ein Template-Wert darf nicht ohne aktive Bestätigung über eine Nutzerregel durchgesetzt werden.

## **3. Audit- und Regel-Engine als technische Schicht (§4)**

### **3.1 Schichtenmodell**

Die Engine ist in vier technische Schichten aufgeteilt. Diese Schichten haben klar abgegrenzte Aufgaben und dürfen sich gegenseitig nicht übersteuern.

**Schicht 1 – Invarianten-Guard (INVARIANT-Modul).** Prüft die harten Invarianten H-1 bis H-7 vor jeder Operation. Gibt ausschliesslich binäre Entscheidung: erlaubt / blockiert. Erzeugt keine Befunde, keine UI-Meldungen – nur Sperrung und technisches Log. Kann durch nichts deaktiviert oder übersteuert werden. Die vollständigen Definitionen von H-1 bis H-7 liegen in der Core Architecture Baseline v1.0. Sie werden hier nicht wiederholt.

**Schicht 2 – Befund-Engine (AUDIT-Modul + CONSISTENCY-Modul).** Prüft die Audit-Regeln A-01 bis D-03 sowie die Konsistenzregeln K-01 bis K-07. Liefert ausschliesslich Befunde: Segment-UUID, Regelkennung, Verstossklasse, Schweregrad. Trifft keine Entscheidungen. Erzeugt keine Revisions-UUIDs und keine Decision-Event-UUIDs. Schreibt Log-Einträge im Ereignis-Log.

**Schicht 3 – Decision-Gate-Layer (PREFLIGHT-Modul).** Aggregiert die Befunde aus Schicht 2. Klassifiziert sie nach blockierend (Kritisch, Pflichthinweis) und nicht-blockierend (Warnung). Stellt dem Nutzer Auflösungsoptionen bereit. Erzeugt Decision-Event-UUIDs nach Nutzerentscheidung über das REVISION-Modul, gemäss dem kanonischen decision_source-Enum (§4.10) und der Abfrageregel für active_decision_event_uuids\[\] (§4.11). Schreibt Exportlauf-Ereignisse über das EVENTING-Modul. Trägt das Preflight-Schichtenmodell gemäss §2.2 (Konfigurationspflichten vs. Gate-Prüfungen) und die benannte Hadith-Verifikationsstatus-Gruppe gemäss §2.4.

**Schicht 4 – UI-Reporting-Layer.** Reine Darstellung von Befunden und Auflösungsstatus. Keine eigene Logik. Zeigt Verstoss-Indikatoren, Auflösungsoptionen, Preflight-Zusammenfassung.

### **3.2 Trennregel**

Keine Schicht darf die Aufgaben einer anderen übernehmen. Insbesondere:

- Die Befund-Engine trifft keine Entscheidungen.

- Der Decision-Gate-Layer ersetzt nicht den Invarianten-Guard.

- Die UI-Schicht darf keine Preflight-Logik lokal implementieren.

## **4. Audit-Regeln A-01 bis D-03**

### **4.1 Grundprinzip**

Das Audit hat keinen Gesamtscore. Es prüft pro Segment, ob konkrete definierte Regeln eingehalten oder verletzt wurden. Jeder Verstoss hat eine Klasse, einen Schweregrad und eine Konsequenz. Das Audit läuft parallel zur Übersetzungsausgabe. Es stoppt den Übersetzungsflow nicht (§3.6 Kanon); Befunde werden persistiert und in die Preflight-Logik weitergeführt. Das Ignorieren eines Audit-Befunds wird immer protokolliert als decision_event mit decision_source = audit_resolution und Entscheid = ignoriert.

### **4.2 Verzeichnistypen und Bindungsstufen**

Verzeichnisse sind explizite Nutzerfestlegungen. Eine Abweichung ist eine Verletzung der entsprechenden Governable Rule und wird als kritisch behandelt.

- Terminologie-Verzeichnis und Glossar → Verletzung G-2 → Kritisch.

- Religiöse Formeln-Verzeichnis → Verletzung G-3 → Kritisch.

Konsequenz für D-03: Wird von Hoch auf Kritisch hochgestuft.

Die vollständigen Definitionen von G-1 bis G-4 liegen in der Core Architecture Baseline v1.0.

### **4.3 Kategorie A – Partikeltreue**

**A-01 – <span dir="rtl">إِنَّ / أَن</span>َّ nicht übertragen.** Beide Partikel müssen explizit übertragen werden: <span dir="rtl">إِن</span>َّ als betonende Einleitung, <span dir="rtl">أَن</span>َّ als dass-Einleitung. Erkennung: Partikel im Quellsegment, keine Entsprechung im Zielsegment. Schweregrad: Hoch – Pflichthinweis. Muss vor Export aktiv pro Stelle entschieden werden.

**A-02 – <span dir="rtl">ل</span>َ (Betonung) nicht als Emphase übertragen.** Emphatisches <span dir="rtl">ل</span>َ ist mit „wahrlich" oder „fürwahr" zu übertragen. Erkennung: emphatisches <span dir="rtl">ل</span>َ im Quellsegment, kein Emphase-Äquivalent im Zielsegment. Schweregrad: Mittel – Hinweis. Export mit Warnung möglich.

**A-03 – <span dir="rtl">ف</span>َ nicht kontextsensitiv übertragen.** <span dir="rtl">ف</span>َ ist kontextsensitiv mit „so", „dann" oder einer Folge-Konjunktion zu übertragen. Erkennung: <span dir="rtl">ف</span>َ im Quellsegment, keine oder falsch klassifizierte Entsprechung. Schweregrad: Mittel – Hinweis. Export mit Warnung möglich.

**A-04 – <span dir="rtl">أَمَّا...ف</span>َ-Konstruktion nicht vollständig übertragen.** Die Konstruktion muss als „Was … betrifft, so" übertragen werden. Erkennung: Konstruktion im Quellsegment, Übersetzung weicht ab. Schweregrad: Hoch – Pflichthinweis. Muss vor Export aktiv pro Stelle entschieden werden.

### **4.4 Kategorie B – Strukturtreue**

**B-01 – Idāfa zu frei aufgelöst.** Idāfa-Konstruktionen sind wortgetreu zu übertragen, nicht zu paraphrasieren. Erkennung: Idāfa im Quellsegment, keine direkte Genitivkonstruktion im Zielsegment. Schweregrad: Hoch – Pflichthinweis. Muss vor Export aktiv pro Stelle entschieden werden.

**B-02 – Dual nicht sichtbar.** Der arabische Dual muss explizit als Dual in der Übersetzung erkennbar sein. Erkennung: Dual-Form im Quellsegment, keine Dual-Markierung im Zielsegment. Schweregrad: Hoch – Pflichthinweis. Muss vor Export aktiv pro Stelle entschieden werden.

**B-03 – Genusunterschied nicht übertragen.** Semantisch relevanter Genusunterschied ist, wenn im Deutschen übertragbar, zu erhalten. Erkennung: relevanter Genusunterschied erkannt, Übersetzung verliert ihn. Schweregrad: Mittel – Hinweis. Export mit Warnung möglich.

**B-04 – Konditionalsatz nicht textnah.** Konditionalkonstruktionen sind textnah und wortgetreu zu übertragen. Erkennung: Konditionalsatz im Quellsegment, Übersetzung paraphrasiert. Schweregrad: Mittel – Hinweis. Export mit Warnung möglich.

### **4.5 Kategorie C – Terminologie und Belege**

**C-01 – Terminologieeintrag verletzt.** Jeder Begriff im Terminologie-Verzeichnis oder Glossar ist exakt nach Eintrag zu übertragen. Erkennung: Begriff im Quellsegment, Übersetzung weicht vom Verzeichniseintrag ab. Schweregrad: Kritisch. Stelle blockiert, bis aufgelöst durch Korrektur gemäss Eintrag, lokale Ausnahme mit Begründung oder bestätigte Regelanpassung.

**C-02 – Islamischer Fachbegriff ohne Erstauftreten-Behandlung.** Beim ersten Auftreten ist die deutsche Fachübersetzung plus das arabische Original in Klammern plus eine Fussnote erforderlich. Erkennung: Fachbegriff im Quellsegment, Erstauftreten-Markierung oder Fussnote fehlt. Schweregrad: Hoch – Pflichthinweis. Muss vor Export aktiv pro Stelle entschieden werden.

**C-03 – Translatorische Ergänzung nicht markiert.** Jede Ergänzung des Übersetzers erfordert eine Fussnote \[Ü.\]. Erkennung: Ergänzung ohne Quelläquivalent, keine Fussnote vorhanden. Schweregrad: Hoch – Pflichthinweis. Muss vor Export aktiv pro Stelle entschieden werden.

### **4.6 Kategorie D – Stilistik und Rhetorik**

**D-01 – Metapher oder Redewendung nicht wörtlich mit Fussnote.** Rhetorische Figuren sind wörtlich zu übertragen und mit Fussnote \[Ü.\] zu versehen. Erkennung: rhetorische Figur identifiziert, wörtliche Übertragung oder Fussnote fehlt. Schweregrad: Mittel – Hinweis. Export mit Warnung möglich.

**D-02 – Sajʿ ohne Hinweis in Fussnote.** Ein erkanntes Sajʿ-Muster muss mit der Fussnote „Im arabischen Original als Sajʿ (Reimprosa) formuliert" versehen werden. Erkennung: Sajʿ-Muster erkannt, Fussnote fehlt. Schweregrad: Mittel – Hinweis. Export mit Warnung möglich.

**D-03 – Religiöse Formel nicht nach Verzeichnis.** Religiöse Formeln sind ausschliesslich nach Verzeichniseintrag auszugeben. Erkennung: Formel erkannt, Ausgabe weicht vom Verzeichniseintrag ab. Schweregrad: Kritisch (hochgestuft gemäss §4.2). Stelle blockiert, bis aufgelöst durch Korrektur gemäss Verzeichnis, lokale Ausnahme mit Begründung oder Anpassung des Verzeichniseintrags.

### **4.6a Stilfeature-Verstösse (CR-2)**

Ergänzung der A-01–D-03 Audit-Matrix um Stilfeature-Verstösse entlang der in Dokument 1 §4.12, §4.14 und §5.3 kanonisierten Konzepte. Die Verstösse werden in die bestehende Dreiteilung der Verstossklassen (§4.7) eingeordnet und tragen die jeweils strukturanaloge Gate-Wirkung gemäss Dokument 1 §4.7.

**Kritisch-Klasse-Verstösse (Stilfeature):**

- Vorranglogik-Verstoss: eine Stilregel-Anwendung verletzt eine Systemregel gemäss Dokument 1 §4.12. Schweregrad: Kritisch. Wirkung: blockierend, P-03-strukturanalog gemäss Dokument 1 §4.7.

- Anwendung einer Stilregel im Status vom_nutzer_gesperrt gemäss Dokument 1 §4.14. Schweregrad: Kritisch. Wirkung: blockierend, P-03-strukturanalog gemäss Dokument 1 §4.7.

**Hoch-Klasse-Verstoss (Stilfeature):**

- Verletzung einer PF-12-Negativliste-Regel gemäss Dokument 1 §5.3. Schweregrad: Hoch – Pflichthinweis. Wirkung: P-04-strukturanalog gemäss Dokument 1 §4.7. Muss vor Export aktiv pro Stelle entschieden werden.

**Mittel-Klasse-Verstoss (Stilfeature):**

- Verletzung einer aktiven Stilregel ohne Vorranglogik-Bezug und ohne PF-12-Bezug. Schweregrad: Mittel – Hinweis. Wirkung: W-01-strukturanalog gemäss Dokument 1 §4.7 (go_with_warning). Export mit Warnung möglich.

### **4.7 Verstossklassen – vollständige Dreiteilung**

- **Kritisch** = Verzeichnisverletzung oder Verletzung einer expliziten projektweiten Nutzerfestlegung; zusätzlich Stilfeature-Verstösse der Kritisch-Klasse gemäss §4.6a (Vorranglogik-Verstoss, Anwendung einer Stilregel im Status vom_nutzer_gesperrt). Stelle blockiert, bis aufgelöst. Belegt P-03 bzw. ist P-03-strukturanalog.

- **Hoch – Pflichthinweis** = muss vor Export pro Stelle aktiv entschieden werden; zusätzlich Stilfeature-Verstoss der Hoch-Klasse gemäss §4.6a (PF-12-Negativliste-Verletzung). Belegt P-04 bzw. ist P-04-strukturanalog.

- **Mittel – Hinweis** = Export mit Warnung möglich (go_with_warning); zusätzlich Stilfeature-Verstoss der Mittel-Klasse gemäss §4.6a (Verletzung einer aktiven Stilregel ohne Vorranglogik- und ohne PF-12-Bezug). Belegt W-01 bzw. ist W-01-strukturanalog.

## **5. Gesperrte Aktionen (§6.2)**

Das Backend erzwingt die folgenden Sperrungen. UI-Prüfung allein genügt nicht.

<table>
<thead>
<tr>
<th style="text-align: center;"><blockquote>
<p><strong>Aktion</strong></p>
</blockquote></th>
<th style="text-align: center;"><blockquote>
<p><strong>Gesperrt wenn</strong></p>
</blockquote></th>
</tr>
<tr>
<th><blockquote>
<p>Übersetzungsstart</p>
</blockquote></th>
<th><blockquote>
<p>Freigabeschranke nicht auf übersetzungsreif oder übersetzbar_mit_warnung mit Bestätigung</p>
</blockquote></th>
</tr>
<tr>
<th><blockquote>
<p>Export</p>
</blockquote></th>
<th><blockquote>
<p>Preflight nicht auf exportierbar oder exportierbar_mit_warnungen mit Bestätigung</p>
</blockquote></th>
</tr>
<tr>
<th><blockquote>
<p>Export</p>
</blockquote></th>
<th><blockquote>
<p>Vier Pflichtfragen der Konfigurationsschicht (§2.2) nicht aktiv beantwortet</p>
</blockquote></th>
</tr>
<tr>
<th><blockquote>
<p>Automatische Segmentänderung</p>
</blockquote></th>
<th><blockquote>
<p>Segment hat aktives Sperrflag</p>
</blockquote></th>
</tr>
<tr>
<th><blockquote>
<p>Automatische Konfliktauflösung</p>
</blockquote></th>
<th><blockquote>
<p>Sperrflag-Konflikt erkannt</p>
</blockquote></th>
</tr>
<tr>
<th><blockquote>
<p>Promotion zu Stilregel</p>
</blockquote></th>
<th><blockquote>
<p>Ohne dreistufige Pipeline (§5.6 Kanon) und Nutzerbestätigung</p>
</blockquote></th>
</tr>
<tr>
<th><blockquote>
<p>Sperrflag-Aufhebung Sperrebene 2</p>
</blockquote></th>
<th><blockquote>
<p>Ohne Bestätigungs-Dialog mit Klartext-Warnung</p>
</blockquote></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

Zusätzlich aus Kanon:

- Export mit offenen H-2-Hadith-Stellen (§4.16): blockiert bis Auflösung über die sieben kanonisierten Handlungstypen.

- Export bei Guard-nahen Verstössen vor Preflight (§2.3): Preflight-Dialog wird gar nicht geöffnet.

## **6. Explizit zu quittierende Decision Gates (§6.3)**

Die folgenden Ereignisse dürfen nicht ohne aktive Nutzerquittierung weiterlaufen:

- Freigabeschranke (OCR-Review → Übersetzung).

- Vier Pflichtfragen vor Export als Konfigurationsschicht (§2.2). Formal keine P-Slot-Belegung, aber aktiv zu bestätigen.

- Jeder kritische Audit-Verstoss einzeln (C-01, D-03) – Gate P-03.

- Jeder Pflichthinweis (Hoch-Verstoss) einzeln – Gate P-04.

- Sperrflag-Konflikt (H-6).

- F-06-QR-Block ohne Auflösung (OCR-Qurʾān-Erkennungskonflikt, §4.9 E-1 harte Konflikte).

- Vokalisierungskonflikt V-2 gemäss §4.16 – ersetzt die frühere Kategorie „Konflikt F". Aktive Nutzerauflösung gemäss den sieben kanonisierten Handlungstypen; decision_source = conflict_resolution.

- Hadith-Stellenentscheidung gemäss §4.16 – ersetzt die frühere Kategorie „Hadith-Variantenstreit (Konflikt B, Fall 4)". Eigene benannte Preflight-Gruppe „Hadith-Verifikationsstatus"; H-2 blockiert, H-1 warnungsbasiert. Auflösung ausschliesslich über die sieben kanonisierten Handlungstypen.

- Promotion-Pipeline Stufe 3 (Musterkandidat → Stilregel) gemäss §5.6 Kanon.

- Export mit Warnungen (go_with_warning analog §4.9 E-1, doppelte Warnung für W-01/W-02/W-03 sowie für die H-1-Klasse der Hadith-Verifikationsstatus-Gruppe).

Zusätzlich aus Kanon:

- Qurʾān-Stellenbehandlung gemäss §4.15: manuelle Bestätigung bei Konfidenz unter Schwellenwert (decision_source = translation_pipeline), Korrektur oder Ablehnung (decision_source = conflict_resolution), ausdrückliche Aktualisierung einer bereits gespeicherten Qurʾān-Stelle (decision_source = translation_pipeline). Auto-Akzeptanz erzeugt kein decision_event.

- Stilprofil-Entscheidungen (decision_source = style_management, §4.10).

- Glossar-Einträge (decision_source = glossary_management).

- Konsistenz-Gruppen-Auflösung (decision_source = consistency_resolution).

## **7. Verknüpfung zum kanonischen decision_source-Enum**

Alle Decision-Event-UUIDs, die das PREFLIGHT-Modul aus Nutzerentscheidungen erzeugt, tragen eine decision_source aus dem kanonischen Enum mit zehn überschneidungsfreien Werten: ocr_review, lock_management, conflict_resolution, glossary_management, export_confirmation, preflight_confirmation, translation_pipeline, audit_resolution, consistency_resolution, style_management.

Die Abfrageregel für active_decision_event_uuids\[\] ist deterministisch in §4.11 Kanon festgelegt.

## **8. Abgrenzung zu anderen Baselines**

Diese Baseline definiert nicht:

- die harten Invarianten H-1 bis H-7,

- die Governable Rules G-1 bis G-4,

- die Kernobjekte und Identitäten,

- das Schutzmodell der Sperrebenen,

- das Revisionsmodell und die Promotion-Pipeline – diese liegen in der Core Architecture Baseline v1.0;

- die vollständigen P-/W-Gate-Definitionen und die werkweite Konsistenzprüfung K-01 bis K-07 – diese liegen in der Engineering Execution Baseline v1.0;

- die OCR-Export-Endfassung v1.3 (eigene konsolidierte Endfassung);

- die Formatvorlagen-Baseline v1.1;

- das Stilfeature-Detail (Dokument A v1.0, Dokument B v1.2, Dokument C v1.1).

## **9. Offene Punkte**

Die folgenden Bereiche sind in dieser Baseline nicht abschliessend spezifiziert und werden ausdrücklich offen geführt:

1.  **Originale Abschnitte §1 und §2** der Implementation Translation Baseline (Einleitung, Geltungsbereich, Glossar, Vorbemerkungen): inhaltlich nicht ausgeführt.

2.  **Originale Abschnitte §3.1 bis §3.6:** inhaltlich nicht ausgeführt; nur §3.7 (Export-Preflight) liegt vor und ist hier in §2 abgebildet.

3.  **Detailregeln der Audit-Modul-Implementierung** ausserhalb des Schichtenmodells (Ereignisbus, Logformate, Retry-Logik innerhalb der Engine): nicht ausgeführt.

4.  **Originaler Abschnitt §5:** inhaltlich nicht ausgeführt.

5.  **Originaler Abschnitt §6.1:** inhaltlich nicht ausgeführt; §6.2 (Gesperrte Aktionen) und §6.3 (Decision Gates) liegen vor und sind hier in §5 und §6 abgebildet.

6.  **Originaler Abschnitt §7:** inhaltlich nicht ausgeführt.

7.  **Vollständige Konflikt-Typologie:** Nur Konflikt F (Vokalisierung, mittlerweile durch §4.16 V-2-Eskalationskriterium ersetzt) und Konflikt B Fall 4 (Hadith-Variantenstreit, mittlerweile durch §4.16 Hadith-Verifikationsstatus ersetzt) sind hier punktuell aufgegriffen. Eine vollständige Konflikt-A bis Konflikt-F-Typologie mit allen Fällen ist in dieser Baseline nicht ausgeführt.

8.  **Vollständige P-/W-Slot-Spezifikation:** Hier sind P-01, P-03, P-04, P-06, W-01 und die Hadith-Verifikationsstatus-Gruppe operationalisiert. Eine vollständige Spezifikation aller P-01 bis P-06 / W-01 bis W-08-Slots ist nicht ausgeführt (siehe auch Engineering Execution Baseline §13).

9.  **Feinstruktur des REVISION-Moduls und des EVENTING-Moduls:** in dieser Baseline genannt, nicht spezifiziert.

10. **Detailflüsse des Invarianten-Guards** jenseits der Vier-Schichten-Grobstruktur: nicht ausgeführt.

Waraq Implementation Translation Baseline – Ende der Fassung

7.  
