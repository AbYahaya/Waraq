/**
 * Project-level book preview using the active style profile.
 *
 * This is intentionally lightweight: it previews OCR source + translation
 * page-by-page so style profile changes have a clear validation surface
 * before running DOCX/PDF export.
 */

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { Columns2, Download, Languages } from "lucide-react";

import {
  DEFAULT_STYLE_PROFILE,
  InlineMarkedText,
  WordLikeTranslationToolbar,
  splitAlignedText,
  styleKindForBlock,
  styledParagraphsFromStoredText,
  translationTextStyle,
} from "@/components/TranslationPane";
import { Button } from "@/components/ui/button";
import { queries, type SegmentHistoryDto } from "@/lib/queries";
import {
  getLatestProtectedReference,
  getLatestSourceRevision,
  getLatestTranslationRevision,
  isTranslationStale,
} from "@/lib/segment-history";
import {
  defaultTranslationStyleKey,
  normalizeTranslationStyleKey,
  translationStyleCss,
  type TranslationStyleKey,
} from "@/lib/translation-styles";
import type { Page, ProjectStyleProfile, Segment } from "@/lib/types";

export interface BookPreviewProps {
  projectUuid: string;
  projectName: string;
}

interface PreviewSegment {
  page: Page;
  segment: Segment;
  history: SegmentHistoryDto | undefined;
  styleKey?: TranslationStyleKey;
}

type PreviewMode = "translation" | "bilingual";

function parsePreviewMode(value: string | null): PreviewMode {
  return value === "bilingual" ? "bilingual" : "translation";
}

export function BookPreview({
  projectUuid,
  projectName,
}: BookPreviewProps): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const pagesQ = useQuery(queries.projectPages(projectUuid));
  const styleQ = useQuery(queries.projectStyleProfile(projectUuid));
  const persistedStyle = styleQ.data ?? DEFAULT_STYLE_PROFILE;
  const [styleDraft, setStyleDraft] = useState<ProjectStyleProfile>(persistedStyle);
  const [selectedStyleKey, setSelectedStyleKey] = useState<TranslationStyleKey>(() =>
    normalizeTranslationStyleKey(searchParams.get("preview_style") ?? "body_de"),
  );
  const [previewMode, setPreviewMode] = useState<PreviewMode>(() =>
    parsePreviewMode(searchParams.get("preview")),
  );

  useEffect(() => {
    setStyleDraft(persistedStyle);
  }, [persistedStyle]);

  useEffect(() => {
    setSelectedStyleKey(normalizeTranslationStyleKey(searchParams.get("preview_style") ?? "body_de"));
    setPreviewMode(parsePreviewMode(searchParams.get("preview")));
  }, [searchParams]);

  useEffect(() => {
    const next = new URLSearchParams(searchParams);
    if (previewMode === "translation") {
      next.delete("preview");
    } else {
      next.set("preview", previewMode);
    }
    if (selectedStyleKey === "body_de") {
      next.delete("preview_style");
    } else {
      next.set("preview_style", selectedStyleKey);
    }
    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true });
    }
  }, [previewMode, searchParams, selectedStyleKey, setSearchParams]);

  const pages = pagesQ.data ?? [];
  const segmentQueries = useQueries({
    queries: pages.map((page) => queries.pageSegments(page.page_uuid)),
  });
  const previewSegments = useMemo<PreviewSegment[]>(
    () =>
      pages.flatMap((page, pagePosition) =>
        (segmentQueries[pagePosition]?.data ?? []).map((segment) => ({
          page,
          segment,
          history: undefined,
        })),
      ),
    [pages, segmentQueries],
  );
  const historyQueries = useQueries({
    queries: previewSegments.map((entry) => queries.segmentHistory(entry.segment.satz_uuid)),
  });
  const entries = useMemo<PreviewSegment[]>(
    () =>
      previewSegments.map((entry, index) => ({
        ...entry,
        history: historyQueries[index]?.data,
        styleKey: normalizeTranslationStyleKey(
          entry.segment.translation_style_key ??
            defaultTranslationStyleKey(
              entry.segment.block_type,
              Boolean(getLatestProtectedReference(historyQueries[index]?.data)),
            ),
        ),
      })),
    [historyQueries, previewSegments],
  );

  if (pagesQ.isLoading) {
    return <p className="p-4 text-sm text-muted-foreground">Loading book preview…</p>;
  }
  if (pagesQ.isError) {
    return <p className="p-4 text-sm text-destructive">Failed to load book preview.</p>;
  }
  if (pages.length === 0) {
    return (
      <p className="p-4 text-sm text-muted-foreground">
        Upload pages and run OCR to preview the book.
      </p>
    );
  }

  const textStyle = translationTextStyle(styleDraft);
  const arabicStyle = arabicTextStyle(styleDraft);
  const translatedCount = entries.filter((entry) =>
    Boolean(getLatestTranslationRevision(entry.history)?.text),
  ).length;
  const staleCount = entries.filter((entry) => isTranslationStale(entry.history)).length;
  const printPreview = (mode: PreviewMode) => {
    setPreviewMode(mode);
    window.setTimeout(() => window.print(), 80);
  };

  return (
    <div className="h-full overflow-auto bg-[#efe7d8] px-3 py-4">
      <BookPreviewPrintStyles />
      <div className="mx-auto max-w-[72rem] space-y-5">
        <WordLikeTranslationToolbar
          editor={null}
          projectUuid={projectUuid}
          profile={styleDraft}
          persistedProfile={persistedStyle}
          currentStyleKey={selectedStyleKey}
          dirty={false}
          saving={false}
          canSave={false}
          onProfileChange={setStyleDraft}
          onStyleKeyChange={setSelectedStyleKey}
          onSave={() => undefined}
          onReset={() => setStyleDraft(persistedStyle)}
          styleOnly
        />
        <div className="book-preview-toolbar flex flex-col gap-3 rounded-[1.25rem] border border-[#e0d5c4] bg-[#fffdf8] px-4 py-3 shadow-sm lg:flex-row lg:items-center lg:justify-between">
          <div className="inline-flex w-full rounded-lg border border-[#d8cbb8] bg-[#f8f3ea] p-1 sm:w-auto">
            <Button
              type="button"
              size="sm"
              variant={previewMode === "translation" ? "default" : "ghost"}
              className="min-w-0 flex-1 gap-2 sm:flex-none"
              onClick={() => setPreviewMode("translation")}
            >
              <Languages className="h-4 w-4 shrink-0" />
              <span className="truncate">Translation only</span>
            </Button>
            <Button
              type="button"
              size="sm"
              variant={previewMode === "bilingual" ? "default" : "ghost"}
              className="min-w-0 flex-1 gap-2 sm:flex-none"
              onClick={() => setPreviewMode("bilingual")}
            >
              <Columns2 className="h-4 w-4 shrink-0" />
              <span className="truncate">OCR + translation</span>
            </Button>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => printPreview("translation")}
            >
              <Download className="h-4 w-4 shrink-0" />
              <span>Translated PDF</span>
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => printPreview("bilingual")}
            >
              <Download className="h-4 w-4 shrink-0" />
              <span>OCR + translation PDF</span>
            </Button>
          </div>
        </div>
        <header className="book-preview-header rounded-[1.75rem] border border-[#e0d5c4] bg-[#fffdf8] px-6 py-6 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                Live book preview
              </p>
              <h2 className="mt-1 text-3xl font-semibold text-[#1d221d]">{projectName}</h2>
              <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
                Previewing saved style, translation paragraphs, headings, quotes,
                protected passages, and stale translation state before export.
              </p>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center">
              <PreviewStat label="Pages" value={pages.length} />
              <PreviewStat label="Translated" value={translatedCount} />
              <PreviewStat label="Stale" value={staleCount} tone={staleCount > 0 ? "warn" : "ok"} />
            </div>
          </div>
        </header>

        <div className="space-y-5" data-book-preview-print>
          {pages.map((page) => (
            <PreviewPage
              key={page.page_uuid}
              page={page}
              entries={entries.filter((entry) => entry.page.page_uuid === page.page_uuid)}
              styleProfile={styleDraft}
              translationStyle={textStyle}
              arabicStyle={arabicStyle}
              previewMode={previewMode}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function PreviewStat({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number;
  tone?: "neutral" | "ok" | "warn";
}): JSX.Element {
  return (
    <div className="min-w-24 rounded-2xl border border-[#eee5d6] bg-[#fcfaf5] px-4 py-3">
      <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </div>
      <div
        className={
          tone === "warn"
            ? "mt-1 text-2xl font-semibold text-amber-700"
            : tone === "ok"
              ? "mt-1 text-2xl font-semibold text-green-700"
              : "mt-1 text-2xl font-semibold text-[#1d221d]"
        }
      >
        {value}
      </div>
    </div>
  );
}

interface PreviewPageProps {
  page: Page;
  entries: PreviewSegment[];
  styleProfile: ProjectStyleProfile;
  translationStyle: CSSProperties;
  arabicStyle: CSSProperties;
  previewMode: PreviewMode;
}

function PreviewPage({
  page,
  entries,
  styleProfile,
  translationStyle,
  arabicStyle,
  previewMode,
}: PreviewPageProps): JSX.Element {
  return (
    <article
      className="book-preview-page mx-auto rounded-[1.75rem] border border-[#e0d5c4] bg-[#fffdf8] px-6 py-8 shadow-sm sm:px-10"
      style={{ maxWidth: `${styleProfile.page_max_width_rem}rem` }}
    >
      <div className="book-preview-page-meta mb-6 flex items-center justify-between border-b border-[#eee5d6] pb-3">
        <h3 className="text-lg font-semibold text-[#1d221d]">Page {page.page_index}</h3>
        <span className="text-[11px] text-muted-foreground">{entries.length} anchor(s)</span>
      </div>
      {entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">No OCR/translation text on this page yet.</p>
      ) : (
        <div className="space-y-7">
          {entries.map((entry) => {
            const source = getLatestSourceRevision(entry.history)?.text ?? entry.segment.text_content ?? "";
            const translation = getLatestTranslationRevision(entry.history)?.text ?? "";
            const stale = isTranslationStale(entry.history);
            return (
              <section key={entry.segment.satz_uuid} className="space-y-3">
                {previewMode === "bilingual" && source && (
                  <p
                    dir="rtl"
                    className="whitespace-pre-wrap text-right text-[#1d221d]"
                    style={{
                      ...arabicStyle,
                      ...arabicBlockTextStyle(styleProfile, entry.segment.block_type),
                    }}
                  >
                    {source}
                  </p>
                )}
                {translation ? (
                  <StyledTranslationPreview
                    text={translation}
                    stale={stale}
                    translationStyle={translationStyle}
                    styleProfile={styleProfile}
                    fallbackStyleKey={
                      entry.styleKey ?? defaultTranslationStyleKey(entry.segment.block_type, false)
                    }
                  />
                ) : (
                  <p className="text-sm italic text-muted-foreground">No translation yet.</p>
                )}
              </section>
            );
          })}
        </div>
      )}
    </article>
  );
}

function StyledTranslationPreview({
  text,
  stale,
  translationStyle,
  styleProfile,
  fallbackStyleKey,
}: {
  text: string;
  stale: boolean;
  translationStyle: CSSProperties;
  styleProfile: ProjectStyleProfile;
  fallbackStyleKey: TranslationStyleKey;
}): JSX.Element {
  const blocks = styledParagraphsFromStoredText(text, fallbackStyleKey).flatMap((paragraph) =>
    splitAlignedText(paragraph.text).map((block) => ({
      ...block,
      styleKey: paragraph.styleKey,
    })),
  );

  return (
    <div
      className={stale ? "text-amber-950" : "text-[#252820]"}
      style={translationStyle}
    >
      {blocks.map((block, index) => (
        <p
          key={`${index}-${block.text.slice(0, 18)}`}
          className="whitespace-pre-line"
          style={{
            ...translationStyleCss(styleProfile, block.styleKey),
            textAlign: block.alignment,
            marginBottom:
              index === blocks.length - 1
                ? 0
                : translationStyleCss(styleProfile, block.styleKey).marginBottom,
          }}
        >
          <InlineMarkedText text={block.text} />
        </p>
      ))}
    </div>
  );
}

function arabicTextStyle(profile: ProjectStyleProfile): CSSProperties {
  return {
    fontFamily: `"${profile.arabic_font_family}", "Noto Naskh Arabic", serif`,
    fontSize: `${profile.arabic_font_size_px}px`,
    lineHeight: profile.arabic_line_height,
  };
}

function arabicBlockTextStyle(
  profile: ProjectStyleProfile,
  blockType?: string | null,
): CSSProperties {
  const kind = styleKindForBlock(blockType);
  if (kind === "heading") {
    return {
      fontSize: `${Math.max(profile.arabic_font_size_px, profile.heading_font_size_px)}px`,
      fontWeight: 700,
      lineHeight: profile.heading_line_height,
    };
  }
  if (kind === "quote") {
    return {
      fontSize: `${profile.quote_font_size_px}px`,
      lineHeight: profile.quote_line_height,
    };
  }
  if (kind === "footnote") {
    return {
      fontSize: `${profile.footnote_font_size_px}px`,
      lineHeight: profile.footnote_line_height,
    };
  }
  if (kind === "protected") {
    return {
      fontSize: `${profile.protected_font_size_px}px`,
      lineHeight: profile.protected_line_height,
    };
  }
  return {};
}

function BookPreviewPrintStyles(): JSX.Element {
  return (
    <style>
      {`
        @media print {
          @page {
            size: A4;
            margin: 18mm;
          }

          body * {
            visibility: hidden !important;
          }

          [data-book-preview-print],
          [data-book-preview-print] * {
            visibility: visible !important;
          }

          [data-book-preview-print] {
            position: absolute !important;
            inset: 0 !important;
            width: 100% !important;
            max-width: none !important;
            background: #ffffff !important;
          }

          .book-preview-toolbar,
          .book-preview-header,
          .book-preview-page-meta {
            display: none !important;
          }

          .book-preview-page {
            max-width: none !important;
            min-height: auto !important;
            break-after: page;
            page-break-after: always;
            border: 0 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            padding: 0 !important;
            background: #ffffff !important;
          }

          .book-preview-page:last-child {
            break-after: auto;
            page-break-after: auto;
          }
        }
      `}
    </style>
  );
}
