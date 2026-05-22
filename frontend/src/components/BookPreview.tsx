/**
 * Project-level book preview using the active style profile.
 *
 * This is intentionally lightweight: it previews OCR source + translation
 * page-by-page so style profile changes have a clear validation surface
 * before running DOCX/PDF export.
 */

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";

import {
  DEFAULT_STYLE_PROFILE,
  TranslationStyleControls,
  styleKindForBlock,
  translationParagraphStyle,
  translationTextStyle,
} from "@/components/TranslationPane";
import { queries, type SegmentHistoryDto } from "@/lib/queries";
import {
  getLatestProtectedReference,
  getLatestSourceRevision,
  getLatestTranslationRevision,
  isTranslationStale,
} from "@/lib/segment-history";
import type { Page, ProjectStyleProfile, Segment } from "@/lib/types";

export interface BookPreviewProps {
  projectUuid: string;
  projectName: string;
}

interface PreviewSegment {
  page: Page;
  segment: Segment;
  history: SegmentHistoryDto | undefined;
}

export function BookPreview({
  projectUuid,
  projectName,
}: BookPreviewProps): JSX.Element {
  const pagesQ = useQuery(queries.projectPages(projectUuid));
  const styleQ = useQuery(queries.projectStyleProfile(projectUuid));
  const persistedStyle = styleQ.data ?? DEFAULT_STYLE_PROFILE;
  const [styleDraft, setStyleDraft] = useState<ProjectStyleProfile>(persistedStyle);

  useEffect(() => {
    setStyleDraft(persistedStyle);
  }, [persistedStyle]);

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

  return (
    <div className="h-full overflow-auto bg-[#efe7d8] px-3 py-4">
      <div className="mx-auto max-w-[72rem] space-y-5">
        <TranslationStyleControls
          projectUuid={projectUuid}
          profile={styleDraft}
          persistedProfile={persistedStyle}
          onProfileChange={setStyleDraft}
        />
        <header className="rounded-[1.75rem] border border-[#e0d5c4] bg-[#fffdf8] px-6 py-6 shadow-sm">
          <p className="text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            Book preview
          </p>
          <h2 className="mt-1 text-3xl font-semibold text-[#1d221d]">{projectName}</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Previewing {pages.length} page{pages.length === 1 ? "" : "s"} with the current
            project style profile. Save style before running a new export.
          </p>
        </header>

        {pages.map((page) => (
          <PreviewPage
            key={page.page_uuid}
            page={page}
            entries={entries.filter((entry) => entry.page.page_uuid === page.page_uuid)}
            styleProfile={styleDraft}
            translationStyle={textStyle}
            arabicStyle={arabicStyle}
          />
        ))}
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
}

function PreviewPage({
  page,
  entries,
  styleProfile,
  translationStyle,
  arabicStyle,
}: PreviewPageProps): JSX.Element {
  return (
    <article
      className="mx-auto rounded-[1.75rem] border border-[#e0d5c4] bg-[#fffdf8] px-6 py-8 shadow-sm sm:px-10"
      style={{ maxWidth: `${styleProfile.page_max_width_rem}rem` }}
    >
      <div className="mb-6 flex items-center justify-between border-b border-[#eee5d6] pb-3">
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
            const protectedReference = getLatestProtectedReference(entry.history);
            return (
              <section key={entry.segment.satz_uuid} className="space-y-3">
                {source && (
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
                    paragraphStyle={translationParagraphStyle(
                      styleProfile,
                      entry.segment.block_type,
                      Boolean(protectedReference),
                    )}
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
  paragraphStyle,
}: {
  text: string;
  stale: boolean;
  translationStyle: CSSProperties;
  paragraphStyle: CSSProperties;
}): JSX.Element {
  const paragraphs = splitPreviewParagraphs(text);

  return (
    <div
      className={stale ? "text-amber-950" : "text-[#252820]"}
      style={translationStyle}
    >
      {paragraphs.map((paragraph, index) => (
        <p
          key={`${index}-${paragraph.slice(0, 18)}`}
          className="whitespace-pre-line"
          style={{
            ...paragraphStyle,
            marginBottom:
              index === paragraphs.length - 1 ? 0 : paragraphStyle.marginBottom,
          }}
        >
          {paragraph}
        </p>
      ))}
    </div>
  );
}

function splitPreviewParagraphs(text: string): string[] {
  const normalized = text.replace(/\r\n/g, "\n").trim();
  if (!normalized) return [];
  return normalized
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
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
