import type { CSSProperties } from "react";

import type { ProjectStyleProfile } from "@/lib/types";

export type TranslationStyleKey =
  | "body_de"
  | "body_de_no_indent"
  | "heading_1"
  | "heading_2"
  | "heading_3"
  | "heading_4"
  | "heading_5"
  | "heading_6"
  | "quran_de"
  | "hadith_de"
  | "quote_de"
  | "source_note"
  | "footnote_text";

export interface TranslationStyleDefinition {
  key: TranslationStyleKey;
  label: string;
  group: "Body" | "Headings" | "Protected" | "Notes";
}

export interface TranslationStyleTemplate {
  display_label: string;
  font_family: string;
  font_size_px: number;
  line_height: number;
  paragraph_spacing_px: number;
  docx_font_size_pt: number;
  alignment: "left" | "center" | "right" | "justify";
  first_line_indent_px: number;
  left_indent_px: number;
  border_left: boolean;
  italic: boolean;
  bold: boolean;
}

export const TRANSLATION_STYLE_DEFINITIONS: TranslationStyleDefinition[] = [
  { key: "body_de", label: "Body", group: "Body" },
  { key: "body_de_no_indent", label: "Body, no indent", group: "Body" },
  { key: "heading_1", label: "Heading 1", group: "Headings" },
  { key: "heading_2", label: "Heading 2", group: "Headings" },
  { key: "heading_3", label: "Heading 3", group: "Headings" },
  { key: "heading_4", label: "Heading 4", group: "Headings" },
  { key: "heading_5", label: "Heading 5", group: "Headings" },
  { key: "heading_6", label: "Heading 6", group: "Headings" },
  { key: "quran_de", label: "Quran translation", group: "Protected" },
  { key: "hadith_de", label: "Hadith translation", group: "Protected" },
  { key: "quote_de", label: "Quote", group: "Protected" },
  { key: "source_note", label: "Source note", group: "Notes" },
  { key: "footnote_text", label: "Footnote", group: "Notes" },
];

const STYLE_KEY_SET = new Set(TRANSLATION_STYLE_DEFINITIONS.map((item) => item.key));

export const DEFAULT_TRANSLATION_STYLE_TEMPLATES: Record<
  TranslationStyleKey,
  TranslationStyleTemplate
> = {
  body_de: template("Body", "Calibri", 17, 1.65, 8, 11, { firstLine: 19 }),
  body_de_no_indent: template("Body, no indent", "Calibri", 17, 1.65, 8, 11),
  heading_1: template("Heading 1", "Calibri", 24, 1.25, 16, 16, { bold: true }),
  heading_2: template("Heading 2", "Calibri", 21, 1.25, 12, 14, { bold: true }),
  heading_3: template("Heading 3", "Calibri", 18, 1.25, 10, 12, { bold: true }),
  heading_4: template("Heading 4", "Calibri", 17, 1.25, 8, 12, { bold: true }),
  heading_5: template("Heading 5", "Calibri", 16, 1.25, 8, 11, { bold: true }),
  heading_6: template("Heading 6", "Calibri", 16, 1.25, 6, 11, { bold: true }),
  quran_de: template("Quran translation", "Calibri", 17, 1.5, 12, 11, { left: 23, border: true }),
  hadith_de: template("Hadith translation", "Calibri", 17, 1.5, 12, 11, { left: 23, border: true }),
  quote_de: template("Quote", "Calibri", 16, 1.45, 12, 10, {
    left: 23,
    border: true,
    italic: true,
  }),
  source_note: template("Source note", "Calibri", 14, 1.35, 10, 9, { left: 23 }),
  footnote_text: template("Footnote", "Calibri", 14, 1.25, 6, 9),
};

function template(
  displayLabel: string,
  fontFamily: string,
  fontSize: number,
  lineHeight: number,
  spacing: number,
  docxSize: number,
  options: Partial<Pick<TranslationStyleTemplate, "alignment" | "first_line_indent_px" | "left_indent_px" | "border_left" | "italic" | "bold">> & {
    firstLine?: number;
    left?: number;
    border?: boolean;
  } = {},
): TranslationStyleTemplate {
  return {
    display_label: displayLabel,
    font_family: fontFamily,
    font_size_px: fontSize,
    line_height: lineHeight,
    paragraph_spacing_px: spacing,
    docx_font_size_pt: docxSize,
    alignment: options.alignment ?? "left",
    first_line_indent_px: options.firstLine ?? options.first_line_indent_px ?? 0,
    left_indent_px: options.left ?? options.left_indent_px ?? 0,
    border_left: options.border ?? options.border_left ?? false,
    italic: options.italic ?? false,
    bold: options.bold ?? false,
  };
}

export function normalizeTranslationStyleKey(value: string | null | undefined): TranslationStyleKey {
  return STYLE_KEY_SET.has(value as TranslationStyleKey) ? (value as TranslationStyleKey) : "body_de";
}

export function effectiveTranslationStyleTemplates(
  profile: ProjectStyleProfile,
): Record<TranslationStyleKey, TranslationStyleTemplate> {
  const raw = profile.translation_style_templates ?? {};
  return TRANSLATION_STYLE_DEFINITIONS.reduce(
    (acc, definition) => {
      const base = DEFAULT_TRANSLATION_STYLE_TEMPLATES[definition.key];
      const override = raw[definition.key];
      acc[definition.key] = normalizeTemplate({ ...base, ...(override ?? {}) }, base);
      return acc;
    },
    {} as Record<TranslationStyleKey, TranslationStyleTemplate>,
  );
}

export function withUpdatedTranslationStyleTemplate(
  profile: ProjectStyleProfile,
  styleKey: TranslationStyleKey,
  patch: Partial<TranslationStyleTemplate>,
): ProjectStyleProfile {
  const templates = effectiveTranslationStyleTemplates(profile);
  return {
    ...profile,
    translation_style_templates: {
      ...templates,
      [styleKey]: normalizeTemplate({ ...templates[styleKey], ...patch }, templates[styleKey]),
    },
  };
}

function normalizeTemplate(
  value: Partial<TranslationStyleTemplate>,
  fallback: TranslationStyleTemplate,
): TranslationStyleTemplate {
  return {
    display_label: String(value.display_label || fallback.display_label).slice(0, 80),
    font_family: String(value.font_family || fallback.font_family).slice(0, 80),
    font_size_px: clampNumber(value.font_size_px, 8, 48, fallback.font_size_px),
    line_height: clampNumber(value.line_height, 1, 3, fallback.line_height),
    paragraph_spacing_px: clampNumber(
      value.paragraph_spacing_px,
      0,
      72,
      fallback.paragraph_spacing_px,
    ),
    docx_font_size_pt: clampNumber(value.docx_font_size_pt, 6, 32, fallback.docx_font_size_pt),
    alignment: isAlignment(value.alignment) ? value.alignment : fallback.alignment,
    first_line_indent_px: clampNumber(
      value.first_line_indent_px,
      -80,
      120,
      fallback.first_line_indent_px,
    ),
    left_indent_px: clampNumber(value.left_indent_px, 0, 160, fallback.left_indent_px),
    border_left: Boolean(value.border_left),
    italic: Boolean(value.italic),
    bold: Boolean(value.bold),
  };
}

function clampNumber(value: unknown, min: number, max: number, fallback: number): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(min, Math.min(max, parsed));
}

function isAlignment(value: unknown): value is TranslationStyleTemplate["alignment"] {
  return value === "left" || value === "center" || value === "right" || value === "justify";
}

export function defaultTranslationStyleKey(
  blockType?: string | null,
  protectedReference = false,
): TranslationStyleKey {
  if (protectedReference) return "quran_de";
  const normalized = (blockType ?? "").trim().toLowerCase();
  if (normalized === "ue") return "heading_1";
  if (normalized === "hd" || normalized === "heading") return "heading_2";
  if (normalized === "fn" || normalized === "footnote") return "footnote_text";
  if (normalized === "quran") return "quran_de";
  if (normalized === "hadith") return "hadith_de";
  if (["qr", "quote", "marginalia", "rn", "caption"].includes(normalized)) return "quote_de";
  return "body_de";
}

export function translationStyleCss(
  profile: ProjectStyleProfile,
  styleKey: TranslationStyleKey,
): CSSProperties {
  const tpl = effectiveTranslationStyleTemplates(profile)[styleKey];
  return {
    borderLeft: tpl.border_left ? "3px solid #d7c39c" : undefined,
    fontFamily: `"${tpl.font_family}", ${styleKey.includes("_de") ? "Calibri, sans-serif" : "serif"}`,
    fontSize: `${tpl.font_size_px}px`,
    fontStyle: tpl.italic ? "italic" : undefined,
    fontWeight: tpl.bold ? 700 : undefined,
    lineHeight: tpl.line_height,
    marginBottom: `${tpl.paragraph_spacing_px}px`,
    paddingLeft: tpl.border_left ? "1rem" : undefined,
    textAlign: tpl.alignment,
    textIndent: `${tpl.first_line_indent_px}px`,
    marginLeft: `${tpl.left_indent_px}px`,
  };
}
