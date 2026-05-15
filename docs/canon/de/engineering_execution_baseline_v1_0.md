<!-- Converted from "Engineering Execution Baseline v1.0.docx" via pandoc 3.9.0.2 on 2026-05-02 -->
<!-- The .docx in this directory remains source-of-truth per docs/canon/README.md authority rule -->
<!-- Conversion is content-faithful (text, tables, identifiers, Swiss German ss, Arabic RTL spans, §-refs); Word-specific visual styling is dropped -->

# **WARAQ ENGINEERING EXECUTION BASELINE v1.0**

## **1. Zweck und Geltungsbereich**

Die Waraq Engineering Execution Baseline v1.0 beschreibt in Waraq die technische Ausgestaltung der Export-Preflight-Logik, der Gate-Prüfungen, der werkweiten Konsistenzprüfung und der Guard-nahen Integritätssicherung. Sie ist in Dokument 1 §3.2 als eingefrorene Baseline geführt. Dokument 1 §4.7 und §4.8 verweisen explizit auf sie als massgebliche Quelle für die vollständigen Definitionen der Export-Preflight-Gates P-01 bis P-06 / W-01 bis W-08 sowie der werkweiten Konsistenzprüfung K-01 bis K-07.

Diese Baseline deckt ab:

- das Preflight-Schichtenmodell,

- die Guard-nahen Vorprüfungen vor dem Preflight-Dialog,

- die Belegung der P- und W-Slots innerhalb der Gate-Prüfungsschicht,

- die Verortung der Hadith-Verifikationsstatus-Gruppe,

- die strukturelle Verortung der Konsistenzregeln K-01 bis K-07,

- das Zusammenspiel mit §4.6 (Übersetzungs-Audit), §4.7 (Export-Preflight), §4.8 (Konsistenzprüfung) und §4.16 (Hadith-Behandlung),

- die Verbindung zum decision_source-Enum und zur Abfrageregel active_decision_event_uuids\[\].

Nicht Teil dieser Baseline und in §15 als offene Punkte geführt:

- die inhaltlichen Einzelregeln von K-01 bis K-07,

- die inhaltlichen Einzeldefinitionen von P-01 bis P-06 / W-01 bis W-08 über die hier belegten Belegungen hinaus,

- die Audit-Regeln A-01 bis D-03 (liegen in der Implementation Translation Baseline),

- die harten Invarianten H-1 bis H-7 und die Governable Rules G-1 bis G-4 (liegen in der Core Architecture Baseline).

## **2. Preflight-Schichtenmodell**

Der Export-Preflight-Dialog enthält zwei konzeptionell eigenständige Schichten. Dieses Schichtenmodell ist in Dokument 1 §4.7 kanonisch bestätigt.

### **2.1 Schicht 1 – Konfigurationspflichten**

Die vier Pflichtfragen bilden eine eigenständige Konfigurationsschicht im Preflight-Dialog. Sie fordern notwendige Exportparameter und prüfen keinen Befund im Dokument. Sie belegen keinen P-Slot automatisch.

Die vier Pflichtfragen lauten:

1.  Welche Überschriftenebene soll in der Kopfzeile angezeigt werden?

2.  Welche Überschriftenebene markiert Kapitelumbrüche?

3.  Position des Inhaltsverzeichnisses (vorne / hinten)?

4.  Arabische Kapitelüberschriften im Text anzeigen (ja / nein)?

Zusätzlich beim PDF-Export: Wahl zwischen digital (RGB) und Druck (PDF/X-1a, CMYK, 3 mm Beschnitt).

Der Export darf nicht ohne aktive Bestätigung aller vier Pflichtfragen weiterlaufen. Die Bestätigung belegt formal keinen P-Slot.

### **2.2 Schicht 2 – Gate-Prüfungen**

Blockierende P-Gates und warnungsbasierte W-Gates prüfen Sachverhalte im Dokument oder im Exportzustand gegen definierte Bedingungen. Die konkret belegten Gates stehen in §4.

### **2.3 Abgrenzung der beiden Schichten**

Die Konfigurationsschicht bezieht sich ausschliesslich auf Parameter, die der Nutzer vor dem Export festlegt. Sie ersetzt keine Gate-Prüfung und wird nicht durch eine Gate-Prüfung ersetzt. Die Gate-Prüfungsschicht bezieht sich ausschliesslich auf Befunde im Dokument oder auf den Exportzustand selbst.

## **3. Guard-nahe Vorprüfungen vor dem Preflight-Dialog**

Vor Öffnung des Preflight-Dialogs führt das System Guard-nahe Blockaden durch. Diese sind blockierend und operieren ausserhalb der Preflight-Gate-Logik. Keine dieser Blockaden belegt einen P-Slot. Grundlage: Dokument 1 §4.7.

### **3.1 Ziffernstandard**

Westliche Ziffern sind überall zu verwenden, nie arabische Ziffern. Verstösse gegen den Ziffernstandard werden Guard-nah behandelt und sind blockierend. Kein Audit-Fall, kein Nutzerurteil – direkter Systemmechanismus. Die Prüfung erfolgt vor dem Preflight-Dialog.

### **3.2 Kritische RTL-Encoding- / RTL-Anwendungsfehler**

Kritische Fehler in der RTL-Encodierung oder RTL-Anwendung werden als Integritätsverstoss Guard-nah behandelt und sind blockierend. Die Prüfung erfolgt vor dem Preflight-Dialog.

### **3.3 Formatvorlagen-Integritätsverstösse**

Integritätsverstösse der Formatvorlagen werden Guard-nah behandelt und sind blockierend. Die Prüfung erfolgt unmittelbar vor Öffnung des Preflight-Dialogs. Liegt ein Verstoss vor, wird der Preflight-Dialog nicht geöffnet. Die Auflösung setzt die technische Beseitigung des Verstosses voraus. Eine blosse Nutzerbestätigung genügt nicht.

### **3.4 Kritische Schriftart-Verfügbarkeit**

Kritisch sind die vier in der Formatvorlagen-Baseline v1.1 benannten Schriftarten:

- KFGQPC Uthmanic Script HAFS (Quran_AR)

- Traditional Naskh (Hadith_AR, Zitat_AR, Titel_AR, Titel_AR_Untertitel)

- Noto Sans Arabic (UeberschriftAR_1–6, Begriff_AR, FussN_AR)

- Calibri (Body_DE, Titel_DE, Heading 1–6, FN_Uebersetzer, FN_Herausgeber, FN_Verlag)

Fehlt eine dieser vier Schriftarten, wird der Preflight-Dialog nicht geöffnet. Die Auflösung setzt die technische Wiederherstellung der Schriftart voraus; eine blosse Nutzerbestätigung genügt nicht. Kein stiller Fallback auf eine Ersatzschriftart. Kein P-Slot wird belegt.

### **3.5 Nicht Guard-nah, sondern warnungsbasiert**

Graduelle Formatvorlagen-Abweichungen sind nicht Guard-nah, sondern warnungsbasiert. Sie erreichen den Preflight-Dialog und belegen W-03 (siehe §4.5).

## **4. Belegte und offene P-/W-Slots**

Grundlage: Dokument 1 §4.7.

### **4.1 P-03 – Kritische Audit-Verstösse**

P-03 ist ein eigenständiges blockierendes Gate in der Gate-Prüfungsschicht, strukturell gleichrangig neben P-04. P-03 belegt die Auflösung kritischer Audit-Verstösse im Sinne von §4.6:

- C-01 – Terminologieeintrag verletzt (Verletzung G-2).

- D-03 – Religiöse Formel nicht nach Verzeichnis (Verletzung G-3).

Die Stelle bleibt blockiert, bis sie aufgelöst ist. Ignorieren ist nicht möglich.

### **4.2 P-04 – Hoch-Audit-Befunde**

P-04 belegt die Auflösung der Hoch-Audit-Verstösse (Pflichthinweise) im Sinne von §4.6:

- A-01 – <span dir="rtl">إِنَّ / أَن</span>َّ nicht übertragen.

- A-04 – <span dir="rtl">أَمَّا...ف</span>َ-Konstruktion nicht vollständig übertragen.

- B-01 – Idāfa zu frei aufgelöst.

- B-02 – Dual nicht sichtbar.

- C-02 – Islamischer Fachbegriff ohne Erstauftreten-Behandlung.

- C-03 – Translatorische Ergänzung nicht markiert.

Jede betroffene Stelle muss vor Export aktiv entschieden werden. Ein Ignorieren wird als decision_event mit decision_source = audit_resolution protokolliert.

### **4.3 W-01 – Mittel-Audit-Befunde**

W-01 belegt die Mittel-Audit-Hinweise im Sinne von §4.6:

- A-02 – <span dir="rtl">ل</span>َ (Betonung) nicht als Emphase übertragen.

- A-03 – <span dir="rtl">ف</span>َ nicht kontextsensitiv übertragen.

- B-03 – Genusunterschied nicht übertragen.

- B-04 – Konditionalsatz nicht textnah.

- D-01 – Metapher oder Redewendung nicht wörtlich mit Fussnote.

- D-02 – Sajʿ ohne Hinweis in Fussnote.

Export mit Warnung möglich (go_with_warning analog §4.9 E-1, doppelte Warnung). Protokollierung erfolgt.

### **4.4 W-02 – Konsistenzwarnungen K-01 bis K-07**

W-02 belegt die werkweiten Konsistenzwarnungen K-01 bis K-07 aus §4.8. Diese sind nicht export-blockierend. Sie erzeugen Warnungen. Export mit Warnung möglich.

Ausnahme: Wenn ein K-Verstoss gleichzeitig eine Kritisch-Klasse im Sinne von §4.6 verletzt, gilt das Audit-Gate (P-03), nicht W-02.

Die inhaltlichen Einzeldefinitionen von K-01 bis K-07 sind in §15 als offener Punkt geführt.

### **4.5 W-03 – Graduelle Formatvorlagen-Abweichungen**

W-03 belegt die graduellen Formatvorlagen-Abweichungen. Nicht zu verwechseln mit Formatvorlagen-Integritätsverstössen, die Guard-nah und blockierend sind (§3.3). Graduelle Abweichungen erreichen den Preflight-Dialog und sind warnungsbasiert.

### **4.6 Hadith-Verifikationsstatus – eigene benannte Gruppe**

Der Hadith-Verifikationsstatus bildet eine eigene benannte Gruppe innerhalb der Gate-Prüfungsschicht gemäss §4.7 und §4.16. Die Gruppe ist keine neue Schicht. Sie belegt keinen der offenen P- oder W-Slots. Sie trägt zwei Zustandsklassen:

- **H-2 blockierend:** Stelle nicht exportierbar, solange H-2 bleibt. Auflösung ausschliesslich über die in §4.16 kanonisierten sieben Handlungstypen.

- **H-1 warnungsbasiert:** Stelle exportierbar mit go_with_warning-Bestätigung, konsistent mit §4.9 E-1. decision_source = preflight_confirmation gemäss §4.10.

H-0-Stellen erzeugen keinen Gruppen-Eintrag.

Die Gate-Wirkung der Gruppe ist slot-unabhängig geführt. Eine spätere formale Belegung offener P-/W-Slots bleibt möglich, ohne dass dieser Kanon still geändert wird.

Das Verhältnis zu §4.16 (Stellentypen N-1 bis N-10, Verifikationsklassen H-0 / H-1 / H-2, Vokalisierungsklassen V-0 / V-1 / V-2) ist in §6 vertieft.

### **4.7 Offene P-Slots**

P-01, P-02, P-05, P-06 sind offen. Im bestehenden Kanon des Publikationsexports sind derzeit keine sauberen Kandidaten identifizierbar. Die Slots bleiben vorerst offen.

Die Belegungslogik: Freie P-Slots werden ausschliesslich mit blockierenden Zuständen belegt, die im bestehenden Kanon bereits angelegt sind. Der Hadith-Verifikationsstatus belegt diese Slots nicht, auch wenn H-2 blockierend ist (siehe §4.6).

### **4.8 Offene W-Slots**

W-04 bis W-08 sind offen. Im bestehenden Kanon des Publikationsexports sind derzeit keine weiteren sauberen Kandidaten identifizierbar. Keine Richtungsbindung wird vorweggenommen. Keine neuen warnungsbasierten Zustände sind eingeführt.

## **5. Verhältnis zu §4.6, §4.7, §4.8, §4.16**

### **5.1 §4.6 – Übersetzungs-Audit**

Die Audit-Regeln A-01 bis D-03 sind in drei Klassen eingeteilt: Kritisch, Hoch, Mittel. Die Klassen speisen die Preflight-Gates:

- Kritisch → P-03 (blockierend, Ignorieren nicht möglich).

- Hoch → P-04 (Pflichthinweis, aktive Entscheidung pro Stelle).

- Mittel → W-01 (Hinweis, Export mit Warnung möglich).

Audit-Befunde stoppen den Übersetzungsflow nicht. Sie werden persistiert und in die Preflight-Logik weitergeführt.

Verstösse gegen Formatvorlagen, RTL-Encoding / RTL-Anwendung und den Ziffernstandard sind kein Teil des Audit-Strangs. Sie werden Guard-nah behandelt (§3). Das Stilfeature ist strikt getrennt.

### **5.2 §4.7 – Export-Preflight**

§4.7 ist die kanonische Quelle für das Preflight-Schichtenmodell (§2), die Guard-nahen Vorprüfungen (§3) und die Gate-Belegung (§4). Die Gate-Prüfungsschicht enthält die belegten P- und W-Gates sowie die benannte Hadith-Verifikationsstatus-Gruppe.

### **5.3 §4.8 – Werkweite Konsistenzprüfung**

K-01 bis K-07 sind nicht export-blockierend. Sie erzeugen Warnungen und sind als W-02 verortet. Ausnahme: wenn ein K-Verstoss gleichzeitig eine Kritisch-Klasse im Sinne von §4.6 verletzt, gilt das Audit-Gate (P-03). Graduelle Formatvorlagen-Abweichungen sind W-03, nicht Teil von §4.8.

### **5.4 §4.16 – Hadith-Behandlung**

§4.16 definiert die Stellentypen N-1 bis N-10, die Verifikationsklassen H-0 / H-1 / H-2, die Vokalisierungsklassen V-0 / V-1 / V-2 und die sieben kanonisierten Handlungstypen. Die Abbildung dieser Zustände in den Preflight erfolgt über die benannte Gruppe „Hadith-Verifikationsstatus" gemäss §4.7 und §4.6 dieses Dokuments. Der Hadith-Verifikationsstatus ist kein Audit-Fall im Sinne von §4.6. Er ist ein eigener Zustand mit eigener Gate-Wirkung.

## **6. Hadith-Verifikationsstatus – Detailverortung**

### **6.1 Stellentypen N-1 bis N-10**

Jede Hadith-Stelle erhält nach Abschluss der Mehrquellen-Verifikation und nach jeder nachfolgenden Nutzerinteraktion einen Stellentyp:

- N-1: vollständig verifiziert und automatisch akzeptiert.

- N-2: verifiziert mit protokollpflichtigem Restbefund.

- N-3: verifiziert mit aktiver Nutzerentscheidung.

- N-4: unaufgelöst, vom Nutzer aktiv „für spätere Klärung markiert".

- N-5: Gesamt-Verifikationsausfall ohne Nutzerentscheidung.

- N-6: Autor-Quellenkonflikt unaufgelöst.

- N-7: kein Treffer, kein Entscheid.

- N-8: V-2-Vokalisierungskonflikt unaufgelöst.

- N-9: „nicht als Hadith" behandelt.

- N-10: „ohne Verifikation fortfahren" explizit gewählt.

### **6.2 Abbildung auf Verifikationsklassen**

- **H-0** (review-intern tolerierbar, nicht export-blockierend): N-1, N-3, N-9.

- **H-1** (protokollpflichtig, nicht export-blockierend, warnungsfähig): N-2, N-10.

- **H-2** (export-blockierend bis Auflösung): N-4, N-5, N-6, N-7, N-8.

### **6.3 Auflösung von H-2**

Die Auflösung von H-2 erfolgt ausschliesslich über die sieben in §4.16 kanonisierten Handlungstypen:

1.  Verifizierte Fassung statt Autorwortlaut übernehmen → translation_pipeline.

2.  Volltext statt Kurzfassung wählen → translation_pipeline.

3.  Autorwortlaut trotz Konflikt beibehalten → conflict_resolution.

4.  Quellenangabe ändern / bewusst nicht ändern → conflict_resolution.

5.  Ohne belastbare externe Verifikation fortfahren → conflict_resolution.

6.  Stelle nicht als Hadith behandeln → conflict_resolution.

7.  Vokalisierungskonflikt manuell entscheiden → conflict_resolution.

Die Markierung „für spätere Klärung" ist kein decision_event und hebt H-2 nicht auf.

### **6.4 Vokalisierungs-Eskalationskriterium**

- V-0 ist automatisch tolerierbar und belegt keinen Stellen-Log-Eintrag.

- V-1 ist protokollpflichtig, löst aber keine Eskalation aus.

- V-2 ist eskalationspflichtig, keine automatische Übernahme, aktive Nutzerauflösung gemäss den sieben kanonisierten Handlungstypen mit decision_source = conflict_resolution.

Aggregationsregel: Bei mehreren Abweichungen in einer Stelle gilt die höchste auftretende Klasse (V-0 \< V-1 \< V-2). Rückfallregel: bei Unklarheit wird die höhere Klasse angewendet.

Das Feld vokalisierungs_konflikt ist strikt binär (nein / ja). Die Klassen-Differenzierung läuft ausschliesslich über die abgeleitete vokalisierungsklasse.

## **7. Konsistenzregeln K-01 bis K-07 – strukturelle Verortung**

### **7.1 Verortung**

K-01 bis K-07 sind in Dokument 1 §4.8 als werkweite Konsistenzprüfungen angelegt. Sie sind nicht export-blockierend und erzeugen Warnungen. Ihre Preflight-Verortung ist W-02 (§4.4).

### **7.2 Ausnahme**

Wenn ein K-Verstoss gleichzeitig eine Kritisch-Klasse im Sinne von §4.6 verletzt, gilt das Audit-Gate P-03, nicht W-02. Diese Ausnahme folgt direkt aus der Gleichrangigkeit von P-03 als eigenständigem blockierendem Gate.

### **7.3 Inhalt der K-Regeln**

Die inhaltlichen Einzeldefinitionen von K-01 bis K-07 sind in §15 als offener Punkt geführt.

## **8. Verbindung zum decision_source-Enum und zur Abfrageregel**

### **8.1 decision_source**

Die Preflight-Logik erzeugt Decision-Event-UUIDs nach Nutzerentscheidungen. Die decision_source-Werte werden aus dem in Dokument 1 §4.10 kanonisierten Enum mit zehn überschneidungsfreien Werten gewählt: ocr_review, lock_management, conflict_resolution, glossary_management, export_confirmation, preflight_confirmation, translation_pipeline, audit_resolution, consistency_resolution, style_management.

Für die Preflight-/Gate-Operationalisierung sind besonders relevant:

- **export_confirmation** – nur für OCR-Export-Pflichtfragen.

- **preflight_confirmation** – nur für den finalen Publikationsexport. Trägt insbesondere die H-1-Bestätigungen der Hadith-Verifikationsstatus-Gruppe gemäss §4.16.

- **audit_resolution** – für Audit-Befund-Auflösungen (Klassen Kritisch / Hoch / Mittel).

- **consistency_resolution** – für Konsistenz-Gruppen-Auflösung.

- **conflict_resolution** – für Konflikt-Auflösung, insbesondere für die Handlungstypen 3 bis 7 der Hadith-Stelle und für V-2-Vokalisierungskonflikte.

### **8.2 active_decision_event_uuids\[\]**

Die Abfrageregel active_decision_event_uuids\[\] ist in Dokument 1 §4.11 deterministisch festgelegt und ist für das Preflight-Modul verbindlich. Sie steuert, welche Decision-Events beim Export als aktiv gelten und welche durch spätere Entscheidungen superseded sind.

## **9. Zusammenspiel mit Export-Zuständen**

Die Preflight-Zustände bewegen sich zwischen nicht_gestartet, läuft, exportierbar, exportierbar_mit_warnungen und blockiert. Für die Operationalisierung gilt:

- **exportierbar:** Alle P-Gates aufgelöst, alle Guard-nahen Blockaden sauber, keine aktive H-2-Stelle in der Hadith-Gruppe. Konfigurationsschicht vollständig bestätigt.

- **exportierbar_mit_warnungen:** Zustand erreicht, wenn W-Gates offene Warnungen tragen (W-01 / W-02 / W-03) oder H-1-Stellen vorhanden sind. Export nur nach aktiver go_with_warning-Bestätigung.

- **blockiert:** Mindestens ein P-Gate ungelöst oder mindestens eine H-2-Stelle aktiv oder mindestens eine Guard-nahe Blockade aktiv.

Der Preflight-Dialog öffnet sich erst, wenn die Guard-nahen Blockaden (§3) sauber sind. Die Konfigurationsschicht ist auf aktive Bestätigung angewiesen und ersetzt keine Gate-Prüfung.

## **10. Konsolidierte Übersichtstabelle**

| **Prüfstufe** | **Typ** | **Wirkung** |
|----|----|----|
| Ziffernstandard | Guard-nah | blockierend, Systemmechanismus |
| RTL-Encoding / -Anwendung kritisch | Guard-nah | blockierend, Integritätsverstoss |
| Formatvorlagen-Integrität | Guard-nah | blockierend, Preflight-Dialog öffnet nicht |
| Kritische Schriftart-Verfügbarkeit | Guard-nah | blockierend, Preflight-Dialog öffnet nicht |
| 4 Pflichtfragen | Konfigurationsschicht | keine Gate-Belegung, aktive Bestätigung nötig |
| P-01, P-02, P-05, P-06 | P-Gate | offen |
| P-03 | P-Gate | blockierend, C-01 / D-03 |
| P-04 | P-Gate | blockierend, Hoch-Audit (A-01, A-04, B-01, B-02, C-02, C-03) |
| W-01 | W-Gate | warnungsbasiert, Mittel-Audit (A-02, A-03, B-03, B-04, D-01, D-02) |
| W-02 | W-Gate | warnungsbasiert, K-01 bis K-07 |
| W-03 | W-Gate | warnungsbasiert, graduelle Formatvorlagen-Abweichungen |
| W-04 bis W-08 | W-Gate | offen |
| Hadith-Verifikationsstatus | eigene Gruppe | H-2 blockierend, H-1 warnungsbasiert, keine Slot-Belegung |

## **11. Stilfeature-Schichten (CR-2)**

Verankerung der Stilfeature-Audit-/Konflikt-/Anzeige-/Lern-Schichten gemäss CR-2 entlang der in Dokument 1 §4.12, §4.13, §4.14, §5.3 und §5.6 kanonisierten Konzepte sowie der in Dokument 2 §8 dokumentierten Marker-/Tooltip-Anforderungen.

Die zugehörigen Audit-Verstoss-Klassen für das Stilfeature (Kritisch, Hoch, Mittel) sind in der Implementation Translation Baseline v1.0 (CR-2 / A.1, A.2, A.3) verankert; ihre P-03- bzw. P-04- bzw. W-01-strukturanaloge Wirkung gemäss Dokument 1 §4.7 ist dort beschrieben. Dieser Abschnitt verankert die ergänzenden Schichten, die ausschliesslich der EEB v1.0 zugeordnet sind.

### **11.1 Konflikt-Erkennungs-Schicht (Vorab-Filter)**

Verankerung eines Vorab-Filters innerhalb der Audit-/Gate-Schichten der EEB v1.0 (Schichten gemäss §2 und §4). Der Vorab-Filter prüft beim Anwenden einer Stilregel, ob eine Systemregel gemäss Dokument 1 §4.12 verletzt würde. Bei Treffer wird die Statuswirkung unterdrückt_durch_systemregel gemäss Dokument 1 §4.14 ausgelöst. An dieser Stelle wird kein Persistenzhinweis verankert.

### **11.2 Markiert offene Modellfrage B.2 – Schema-Modell der Konflikttypen**

Das Schema-Modell der Konflikttypen ist ausdrücklich offen. Zwei Modellvarianten sind im Spielraum, in dieser Baseline aber nicht entschieden:

- Modell 1: Erweiterung von conflict_instance aus T-5.1.2.

- Modell 2: eigenes Objekt stil_konflikt.

Bis zur Modellentscheidung wird in der EEB v1.0 keine der beiden Varianten als verankert geführt. Der Vorab-Filter aus §11.1 läuft logisch unabhängig vom späteren Schema-Modell. Die Modellentscheidung ist Teil einer späteren Baseline-Folgearbeit und wird dort getroffen.

### **11.3 Vorranglogik §4.12 als Audit-Bedingung**

Verankerung der Vorranglogik gemäss Dokument 1 §4.12 (Rang 1 Systemregeln \> Rang 2 Nutzerstil \> Rang 3 Referenzsätze) als Audit-Bedingung der Kritisch-Klasse-Stilfeature-Verstösse aus der Implementation Translation Baseline v1.0 (CR-2 / A.1). Die nachträgliche Audit-Wirkung ergänzt den Vorab-Filter aus §11.1 und greift bei Verstoss gegen die Vorranghierarchie auf der Audit-Ebene.

### **11.4 Anzeigeschicht – Stilprofil-Marker**

Verankerung von Stilprofil-Markern am Übersetzungs-Output-Segment: dezente Unterstreichung Blauton, Hover-Tooltip mit PF-XX-Kennung. Verbindung zur stil_regel_uuid-Provenienz (Schema-Bezug nach CR-1 / 1.1). Anzeigeeinstellung als Account-Setting (deaktivierbar gemäss Dokument 1 §4.14, Account-Scope nach CR-1 / 1.3). Geteilte Anzeigeschicht mit den Audit-Verstoss-Markern der Stilfeature-Verstösse aus der Implementation Translation Baseline v1.0 (CR-2 / A.1, A.2, A.3).

### **11.5 Anzeigeschicht – Stilregel-Provenienz im Tooltip**

Verankerung der Provenienz-Anzeige im Hover-Tooltip aus §11.4: die Quellklasse aus Dokument 1 §4.13 (welche Quellklasse hat zur Regel geführt) wird als Vertrauenswert-Signal sichtbar. Nutzt das erstellt_aus-Feld an stil_regel (Schema-Bezug nach CR-1 / 1.5).

### **11.6 Promotion-Pipeline-Logik §5.6**

Verankerung der fünf §5.6-Übergänge als Logik-Schicht:

- kandidat → tendenz;

- tendenz → präferenz;

- präferenz ↔ invariant (nur durch explizite Nutzerhandlung \[KANON\]);

- invariant → präferenz (nur durch explizite Nutzerhandlung \[KANON\]);

- jeder Typ → vom_nutzer_gesperrt.

Verhaltensseitiger Bezug auf das regeltyp-Feld (Schema-Bezug nach CR-1 / 1.7) und das status-Feld (Schema-Bezug nach CR-1 / 1.6). An dieser Stelle wird keine Schemaänderung verankert.

### **11.7 Lernlogik-Schicht – Lernquellen-Asymmetrie §4.13**

Verankerung der Lernquellen-Asymmetrie gemäss Dokument 1 §4.13 als Eingangsbedingung der Promotion-Übergänge aus §11.6:

- bestätigte Referenzsätze und manuelle Nutzerregeln als Hochstufungssignal;

- akzeptierte KI-Vorschläge als schwaches Verstärkungssignal;

- korrigierte KI-Vorschläge als Gegensignal (keine Verstärkung, keine Hochstufung);

- ignorierte KI-Vorschläge als Nullsignal.

Die Lernlogik-Schicht speist die Übergänge aus §11.6.

### **11.8 Test-Familien-Definition (DoD-Anker)**

Materielle Definition von fünf Stilfeature-Test-Familien:

- Korrektursignal-Tests: prüfen das Gegensignal-Verhalten korrigierter KI-Vorschläge gemäss Dokument 1 §4.13 und §11.7.

- Hochstufungs-Tests: prüfen die §5.6-Übergänge aus §11.6.

- Konflikt-Tests gegen Vorranglogik §4.12: prüfen §11.1 und §11.3.

- PF-12-Tests: prüfen die Hoch-Klasse-Stilfeature-Verstösse aus der Implementation Translation Baseline v1.0 (CR-2 / A.2).

- Status-Übergangs-Tests: prüfen die Wirkungen des Konflikt-Mechanismus aus §11.1 auf das status-Feld.

Bindung der Test-Familien an die jeweiligen Architekturschichten als Audit-/Lern-Verifikation.

## **12. Abgrenzung – was operationalisiert ist und was nicht**

**Operationalisiert und belegt:**

- Preflight-Schichtenmodell (Konfigurationspflichten + Gate-Prüfungen).

- Vier Pflichtfragen als Konfigurationsschicht.

- Guard-nahe Vorprüfungen für Ziffernstandard, RTL, Formatvorlagen-Integrität, kritische Schriftart-Verfügbarkeit.

- Belegung P-03 / P-04.

- Belegung W-01 / W-02 / W-03.

- Hadith-Verifikationsstatus-Gruppe als eigene benannte Gruppe mit H-0 / H-1 / H-2.

- Abbildung der Audit-Klassen auf P-03 / P-04 / W-01.

- Ausnahme: K-Verstoss mit Kritisch-Klasse greift das Audit-Gate P-03.

- Belegungslogik für freie P-Slots (nur blockierende, im Kanon angelegte Zustände).

- decision_source-Zuordnung für Preflight- und Audit-Entscheidungen.

- Abfrageregel active_decision_event_uuids\[\] als verbindlicher Bestandteil der Preflight-Logik.

- Konflikt-Erkennungs-Schicht (Vorab-Filter) für Stilregeln (§11.1).

- Vorranglogik §4.12 als Audit-Bedingung (§11.3).

- Anzeige-/Provenance-Schicht für Stilprofil – Marker und Stilregel-Provenienz im Tooltip (§11.4 / §11.5).

- Promotion-Pipeline-Logik §5.6 (§11.6).

- Lernlogik-Schicht – Lernquellen-Asymmetrie §4.13 (§11.7).

- Test-Familien-Definition (DoD-Anker) für das Stilfeature (§11.8).

**Nicht operationalisiert, weiterhin offen:**

- Inhaltliche Belegung der Slots P-01, P-02, P-05, P-06.

- Inhaltliche Belegung der Slots W-04 bis W-08.

- Inhaltliche Einzeldefinitionen von K-01 bis K-07.

- Schema-Modell der Konflikttypen (Modellfrage B.2, in §11.2 markiert offen).

- Persistenzentscheidung für den Vorab-Filter aus §11.1.

## **13. Offene Punkte**

Die folgenden Punkte sind in dieser Baseline nicht abschliessend spezifiziert und werden ausdrücklich offen geführt:

1.  **Inhaltliche Einzeldefinitionen K-01 bis K-07** der werkweiten Konsistenzprüfung. Bekannt ist nur: sieben Regeln, nicht export-blockierend, Verortung W-02, Ausnahme bei Kritisch-Klasse. Die konkreten Prüfbedingungen jeder einzelnen K-Regel sind in dieser Baseline nicht ausformuliert.

2.  **Inhaltliche Belegung der offenen P-Slots P-01, P-02, P-05, P-06.** Die Belegungslogik ist verankert (nur blockierende, im Kanon angelegte Zustände). Kandidaten sind derzeit nicht identifizierbar. Jede Belegung ausserhalb dieser Logik wäre spekulativ.

3.  **Inhaltliche Belegung der offenen W-Slots W-04 bis W-08.** Kandidaten sind derzeit nicht identifizierbar. Keine Richtungsbindung ist vorweggenommen.

4.  **Strukturelles Verhältnis** zwischen Engineering Execution Baseline v1.0 und Implementation Translation Baseline v1.0 im Hinblick auf die Preflight-Zuständigkeit. Dokument 1 §4.7 verweist auf die Engineering Execution Baseline, während Teile der Preflight-Gate-Semantik auch in der Implementation Translation Baseline zu finden sind. Eine saubere Trennlinie ist nicht abschliessend geführt.

5.  **Interne Detailflüsse** des PREFLIGHT-Moduls, des REVISION-Moduls und des EVENTING-Moduls jenseits der bekannten Schichtenstruktur aus der Implementation Translation Baseline.

6.  **Schema-Modell der Konflikttypen** im Stilfeature (Modellfrage B.2 gemäss §11.2): Modell 1 (Erweiterung von conflict_instance aus T-5.1.2) versus Modell 2 (eigenes Objekt stil_konflikt). Modellentscheidung steht aus.

7.  **Persistenzentscheidung** für den Vorab-Filter aus §11.1.

Waraq Engineering Execution Baseline – Ende der Fassung
