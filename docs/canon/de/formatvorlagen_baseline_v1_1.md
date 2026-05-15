<!-- Converted from "Formatvorlagen Baseline v1.1.docx" via pandoc 3.9.0.2 on 2026-05-02 -->
<!-- The .docx in this directory remains source-of-truth per docs/canon/README.md authority rule -->
<!-- Conversion is content-faithful (text, tables, identifiers, Swiss German ss, Arabic RTL spans, §-refs); Word-specific visual styling is dropped -->

# **Kanonische Formatvorlagen-Baseline v1.1**

**Diese Baseline deckt Formatvorlagen, OCR-Qualitätsstandards sowie Sicherheits- und Datenschutzanforderungen ab. Weitere Formatvorlagen- oder Layout-Inhalte sind nicht Gegenstand dieser Baseline.**

## **7.2 Formatvorlagen-Baseline v1.1 (vollständig kanonisch)**

**Seiteneinrichtung: 17 × 24 cm, Rand oben 2 cm, unten 2,6 cm, links 2,7 cm (Bundsteg), rechts 2 cm. Kopfzeilen-/Fusszeilen-Abstand je 1,2 cm. different_first_page = True in allen Abschnitten.**

### **Kopf- und Fusszeile**

- **Kopfzeile normal: STYLEREF-Feld (Ebene vom Nutzer beim Export gewählt) – muss beim Export durch System gesetzt werden**

- **Kopfzeile erste Kapitelseite: leer (via different_first_page)**

- **Fusszeile: Seitenzahl (PAGE-Feld), rechtsbündig**

### **Randstriche**

**Alle Block-Formatvorlagen (Quran/Hadith/Zitat AR+DE+Quelle): links, single, 0,75 pt, 6 pt Abstand, auto-Farbe. Body_DE und footnote text: kein Randstrich.**

### **RTL-Modell Übersetzungs-DOCX**

**Per Run. Paragraph-Ausrichtung „Rechts" und RTL-Flag sind unabhängige Eigenschaften.**

| **Texttyp** | **RTL-Behandlung** |
|----|----|
| **Arabischer Run** | **\<w:rtl/\> pro Run** |
| **Gemischter Paragraph (AR+DE)** | **RTL nur auf arabischen Runs** |
| **Rein deutscher Paragraph** | **Kein RTL-Flag** |
| **Paragraph-Ausrichtung Rechts** | **Via \<w:jc w:val="right"/\> – unabhängig vom RTL-Flag** |

### **Fussnoten**

**eachSect (Neustart an Section Breaks). Section Breaks durch Kapitelumbruch-Ebene aus Preflight-Frage 2 definiert. footnote text: zusammenhalten = True.**

### **IVZ**

**TOC \o "1-6" \u. Tab-Stop 325,5 pt rechts, Punkte als Führungszeichen. Einzüge: toc1 = 0 pt, toc2 = 11 pt, toc3 = 22 pt, toc4 = 33 pt, toc5 = 44 pt, toc6 = 55 pt. Abstand nach allen IVZ-Ebenen: 5 pt.**

### **Kerntabelle Formatvorlagen**

| **Formatvorlage** | **Schriftart** | **Grösse** | **Zeilenabstand** | **Abstand vor** | **Abstand nach** | **Erstzeilen-Einzug** | **Links-Einzug** |
|----|----|----|----|----|----|----|----|
| **Body_DE** | **Calibri** | **erbt** | **genau 15 pt** | **erbt** | **3 pt** | **14,2 pt** | **erbt** |
| **Body_DE_NoIndent** | **erbt** | **erbt** | **erbt** | **erbt** | **erbt** | **0 pt** | **erbt** |
| **Quran_AR** | **KFGQPC Uthmanic Script HAFS** | **15 pt** | **mehrfach 1,15** | **6 pt** | **2 pt** | **0 pt** | **17 pt** |
| **Quran_DE** | **erbt** | **erbt** | **erbt** | **erbt** | **6 pt** | **0 pt** | **17 pt** |
| **Quran_Quelle** | **erbt** | **erbt** | **erbt** | **0 pt** | **6 pt** | **0 pt** | **17 pt** |
| **Hadith_AR** | **Traditional Naskh** | **14 pt** | **mehrfach 1,15** | **6 pt** | **2 pt** | **0 pt** | **17 pt** |
| **Hadith_DE** | **erbt** | **erbt** | **erbt** | **erbt** | **6 pt** | **0 pt** | **17 pt** |
| **Hadith_Quelle** | **erbt** | **erbt** | **erbt** | **0 pt** | **6 pt** | **0 pt** | **17 pt** |
| **Zitat_AR** | **Traditional Naskh** | **14 pt** | **mehrfach 1,15** | **erbt** | **6 pt** | **0 pt** | **17 pt** |
| **Zitat_DE** | **erbt** | **erbt** | **erbt** | **erbt** | **6 pt** | **0 pt** | **17 pt** |
| **Zitat_Quelle** | **erbt** | **erbt** | **erbt** | **0 pt** | **6 pt** | **0 pt** | **17 pt** |
| **Heading 1** | **erbt** | **16 pt** | **einfach** | **18 pt** | **8 pt** | **–** | **–** |
| **Heading 2** | **erbt** | **14 pt** | **einfach** | **14 pt** | **6 pt** | **–** | **–** |
| **Heading 3** | **erbt** | **12 pt** | **einfach** | **10 pt** | **4 pt** | **–** | **–** |
| **Heading 4** | **erbt** | **12 pt** | **einfach** | **8 pt** | **3 pt** | **–** | **–** |
| **Heading 5** | **erbt** | **11 pt** | **einfach** | **8 pt** | **2 pt** | **–** | **–** |
| **Heading 6** | **erbt** | **11 pt** | **einfach** | **6 pt** | **2 pt** | **–** | **–** |
| **UeberschriftAR_1** | **Noto Sans Arabic** | **16 pt** | **einfach** | **18 pt** | **8 pt** | **0 pt** | **erbt** |
| **UeberschriftAR_2** | **Noto Sans Arabic** | **14 pt** | **einfach** | **14 pt** | **6 pt** | **−21,25 pt** | **42,5 pt** |
| **UeberschriftAR_3** | **Noto Sans Arabic** | **12 pt** | **einfach** | **10 pt** | **4 pt** | **0 pt** | **erbt** |
| **UeberschriftAR_4** | **Noto Sans Arabic** | **12 pt** | **genau 15 pt** | **8 pt** | **3 pt** | **0 pt** | **erbt** |
| **UeberschriftAR_5** | **Noto Sans Arabic** | **11 pt** | **genau 15 pt** | **8 pt** | **2 pt** | **−21,25 pt** | **85,05 pt** |
| **UeberschriftAR_6** | **Noto Sans Arabic** | **11 pt** | **genau 15 pt** | **6 pt** | **2 pt** | **0 pt** | **14,2 pt** |
| **Titel_AR** | **Traditional Naskh** | **26 pt** | **1,5-fach** | **85 pt** | **10 pt** | **0 pt** | **erbt** |
| **Titel_AR_Untertitel** | **Traditional Naskh** | **20 pt** | **mehrfach 1,33** | **10 pt** | **20 pt** | **0 pt** | **erbt** |
| **Titel_Trennlinie** | **erbt** | **erbt** | **erbt** | **10 pt** | **20 pt** | **0 pt** | **erbt** |
| **Titel_DE** | **Calibri** | **14 pt fett** | **genau 15 pt** | **20 pt** | **10 pt** | **0 pt** | **erbt** |
| **Titel_DE_Untertitel** | **Calibri** | **11 pt** | **genau 15 pt** | **5 pt** | **30 pt** | **0 pt** | **erbt** |
| **Titel_Verfasser** | **Calibri** | **11 pt** | **genau 15 pt** | **10 pt** | **6 pt** | **0 pt** | **erbt** |
| **Titel_Verlag** | **erbt** | **erbt** | **genau 15 pt** | **60 pt** | **3 pt** | **0 pt** | **erbt** |
| **footnote text** | **erbt** | **9 pt** | **genau 12 pt** | **erbt** | **erbt** | **–** | **–** |
| **toc 1–4** | **erbt** | **erbt** | **erbt** | **erbt** | **5 pt** | **–** | **0 / 11 / 22 / 33 pt** |

### **Gelehrtenzitate**

**Fallen unter Zitat_AR / Zitat_DE / Zitat_Quelle – keine eigene Formatvorlage.**

### **Blockreihenfolgen**

- **Quran: AR → DE → Quelle**

- **Hadith: AR → DE → Quelle**

- **Zitat: AR → DE → Quelle**

- **Titel: AR → AR_Untertitel → Trennlinie → DE → DE_Untertitel → Verfasser → Verlag**

### **Zeichenformate**

| **Format** | **Schriftart** | **Grösse** | **Fett** | **Kursiv** | **Farbe** |
|----|----|----|----|----|----|
| **Begriff_AR** | **Noto Sans Arabic** | **11 pt** | **False (explizit)** | **erbt** | **erbt** |
| **FussN_AR** | **Noto Sans Arabic** | **9 pt** | **erbt** | **erbt** | **erbt** |
| **FN_Uebersetzer** | **Calibri** | **9 pt** | **True** | **erbt** | **erbt** |
| **FN_Herausgeber** | **Calibri** | **9 pt** | **True** | **True** | **erbt** |
| **FN_Verlag** | **Calibri** | **9 pt** | **True** | **erbt** | **\#595959** |

### **Fussnoten-Kennzeichnungen**

- **Autor: ¹ (keine)**

- **Editor: ¹ \[Hrsg.\]**

- **Verlag: ¹ \[Verl.\]**

- **Übersetzer: ¹ \[Ü.\]**

### **Was in FINAL.docx noch nicht implementiert ist**

- **STYLEREF-Feld in Kopfzeile → muss beim Export durch System gesetzt werden**

- **Überschriftenebene für Kopfzeile und Kapitelumbruch → beim Export vom Nutzer gewählt (nie annehmen)**

## **7.3 OCR-Qualitätsstandards**

**OCR-Darstellung maximal simpel: Noto Sans Arabic, 14 pt; Überschriften nur fett + grösserer Abstand; Koranverse/Hadithe nur Einrückung + Randstrich; Fussnoten 11 pt + Trennlinie.**

## **7.4 Sicherheit und Datenschutz**

- **SSL + at-rest encryption**

- **Passwort-Hashing (bcrypt / Argon2), 2FA optional**

- **Kein Timeout bei aktivem Hintergrundprozess, sonst 2 h**

- **Papierkorb: 10 Tage**
