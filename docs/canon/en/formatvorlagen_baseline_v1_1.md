<!-- Source: Google Drive doc 1XRdRbdIXPflwlzYgdYUZ1QO11p6lyiYZz5vA30DExCg (Formatvorlagen Baseline v1.1) -->
<!-- Pulled: 2026-05-01. Place at /docs/canon/formatvorlagen_baseline_v1_1.md -->
<!-- Section numbering (§7.2 / §7.3 / §7.4) preserved from source — these anchors are referenced from other canon documents. -->

# Canonical Formatvorlagen Baseline v1.1

This baseline covers document style templates, OCR quality standards, and security and data-protection requirements. Further document-style or layout content is not the subject of this baseline.

## §7.2 Formatvorlagen-Baseline v1.1 (fully canonical)

Page setup: 17 × 24 cm, top margin 2 cm, bottom 2.6 cm, left 2.7 cm (gutter), right 2 cm. Header / footer distance 1.2 cm each. `different_first_page = True` in all sections.

### Header and footer

- Header normal: STYLEREF field (level chosen by user on export) — must be set by the system on export
- Header first chapter page: empty (via `different_first_page`)
- Footer: page number (PAGE field), right-aligned

### Marginal lines

All block document-styles (Quran / Hadith / Zitat AR + DE + source): left, single, 0.75 pt, 6 pt distance, auto color. `Body_DE` and `footnote text`: no marginal line.

### RTL model translation DOCX

Per run. Paragraph alignment "right" and the RTL flag are independent properties.

| Text type | RTL handling |
|---|---|
| Arabic run | `<w:rtl/>` per run |
| Mixed paragraph (AR + DE) | RTL only on Arabic runs |
| Pure German paragraph | No RTL flag |
| Paragraph alignment right | Via `<w:jc w:val="right"/>` — independent of the RTL flag |

### Footnotes

`eachSect` (restart at section breaks). Section breaks defined by the chapter-break level from preflight question 2. `footnote text`: keep-with-next = True.

### TOC

`TOC \o "1-6" \u`. Tab stop 325.5 pt right, dots as leader characters. Indents: `toc1 = 0 pt`, `toc2 = 11 pt`, `toc3 = 22 pt`, `toc4 = 33 pt`, `toc5 = 44 pt`, `toc6 = 55 pt`. Spacing after, all TOC levels: 5 pt.

### Core table of document styles

| Style | Font | Size | Line spacing | Space before | Space after | First-line indent | Left indent |
|---|---|---|---|---|---|---|---|
| Body_DE | Calibri | inherit | exact 15 pt | inherit | 3 pt | 14.2 pt | inherit |
| Body_DE_NoIndent | inherit | inherit | inherit | inherit | inherit | 0 pt | inherit |
| Quran_AR | KFGQPC Uthmanic Script HAFS | 15 pt | multiple 1.15 | 6 pt | 2 pt | 0 pt | 17 pt |
| Quran_DE | inherit | inherit | inherit | inherit | 6 pt | 0 pt | 17 pt |
| Quran_Quelle | inherit | inherit | inherit | 0 pt | 6 pt | 0 pt | 17 pt |
| Hadith_AR | Traditional Naskh | 14 pt | multiple 1.15 | 6 pt | 2 pt | 0 pt | 17 pt |
| Hadith_DE | inherit | inherit | inherit | inherit | 6 pt | 0 pt | 17 pt |
| Hadith_Quelle | inherit | inherit | inherit | 0 pt | 6 pt | 0 pt | 17 pt |
| Zitat_AR | Traditional Naskh | 14 pt | multiple 1.15 | inherit | 6 pt | 0 pt | 17 pt |
| Zitat_DE | inherit | inherit | inherit | inherit | 6 pt | 0 pt | 17 pt |
| Zitat_Quelle | inherit | inherit | inherit | 0 pt | 6 pt | 0 pt | 17 pt |
| Heading 1 | inherit | 16 pt | single | 18 pt | 8 pt | – | – |
| Heading 2 | inherit | 14 pt | single | 14 pt | 6 pt | – | – |
| Heading 3 | inherit | 12 pt | single | 10 pt | 4 pt | – | – |
| Heading 4 | inherit | 12 pt | single | 8 pt | 3 pt | – | – |
| Heading 5 | inherit | 11 pt | single | 8 pt | 2 pt | – | – |
| Heading 6 | inherit | 11 pt | single | 6 pt | 2 pt | – | – |
| UeberschriftAR_1 | Noto Sans Arabic | 16 pt | single | 18 pt | 8 pt | 0 pt | inherit |
| UeberschriftAR_2 | Noto Sans Arabic | 14 pt | single | 14 pt | 6 pt | −21.25 pt | 42.5 pt |
| UeberschriftAR_3 | Noto Sans Arabic | 12 pt | single | 10 pt | 4 pt | 0 pt | inherit |
| UeberschriftAR_4 | Noto Sans Arabic | 12 pt | exact 15 pt | 8 pt | 3 pt | 0 pt | inherit |
| UeberschriftAR_5 | Noto Sans Arabic | 11 pt | exact 15 pt | 8 pt | 2 pt | −21.25 pt | 85.05 pt |
| UeberschriftAR_6 | Noto Sans Arabic | 11 pt | exact 15 pt | 6 pt | 2 pt | 0 pt | 14.2 pt |
| Titel_AR | Traditional Naskh | 26 pt | 1.5x | 85 pt | 10 pt | 0 pt | inherit |
| Titel_AR_Untertitel | Traditional Naskh | 20 pt | multiple 1.33 | 10 pt | 20 pt | 0 pt | inherit |
| Titel_Trennlinie | inherit | inherit | inherit | 10 pt | 20 pt | 0 pt | inherit |
| Titel_DE | Calibri | 14 pt bold | exact 15 pt | 20 pt | 10 pt | 0 pt | inherit |
| Titel_DE_Untertitel | Calibri | 11 pt | exact 15 pt | 5 pt | 30 pt | 0 pt | inherit |
| Titel_Verfasser | Calibri | 11 pt | exact 15 pt | 10 pt | 6 pt | 0 pt | inherit |
| Titel_Verlag | inherit | inherit | exact 15 pt | 60 pt | 3 pt | 0 pt | inherit |
| footnote text | inherit | 9 pt | exact 12 pt | inherit | inherit | – | – |
| toc 1–4 | inherit | inherit | inherit | inherit | 5 pt | – | 0 / 11 / 22 / 33 pt |

### Scholar citations

Fall under `Zitat_AR` / `Zitat_DE` / `Zitat_Quelle` — no separate document style.

### Block orderings

- Quran: AR → DE → source
- Hadith: AR → DE → source
- Zitat: AR → DE → source
- Titel: AR → AR_Untertitel → Trennlinie → DE → DE_Untertitel → Verfasser → Verlag

### Character formats

| Format | Font | Size | Bold | Italic | Color |
|---|---|---|---|---|---|
| Begriff_AR | Noto Sans Arabic | 11 pt | False (explicit) | inherit | inherit |
| FussN_AR | Noto Sans Arabic | 9 pt | inherit | inherit | inherit |
| FN_Uebersetzer | Calibri | 9 pt | True | inherit | inherit |
| FN_Herausgeber | Calibri | 9 pt | True | True | inherit |
| FN_Verlag | Calibri | 9 pt | True | inherit | #595959 |

### Footnote markings

- Author: ¹ (none)
- Editor: ¹ [Hrsg.]
- Publisher: ¹ [Verl.]
- Translator: ¹ [Ü.]

### What is not yet implemented in `FINAL.docx`

- STYLEREF field in header → must be set by the system on export
- Heading level for header and chapter break → chosen by user on export (never assumed)

## §7.3 OCR quality standards

OCR presentation maximally simple: Noto Sans Arabic, 14 pt; headings only bold + larger spacing; Qurʾān verses / hadiths only indent + marginal line; footnotes 11 pt + separator line.

## §7.4 Security and data protection

- SSL + at-rest encryption
- Password hashing (bcrypt / Argon2), 2FA optional
- No timeout while a background process is active, otherwise 2 h
- Recycle bin: 10 days