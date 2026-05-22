/**
 * Translation pane — page-style target text with protected source popups.
 *
 * The visible workspace is document-like, while the underlying segment
 * UUIDs stay attached as quiet anchors for history, stale-source checks,
 * protected Quran/Hadith provenance, and cross-pane synchronization.
 */

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import { queries, qk, type SegmentHistoryDto } from "@/lib/queries";
import {
  emitSentenceJump,
  formatSentenceId,
  onSentenceJump,
} from "@/lib/sentence-id";
import {
  getLatestProtectedReference,
  getLatestSourceRevision,
  getLatestTranslationRevision,
  isTranslationStale,
  type ProtectedReferenceSummary,
} from "@/lib/segment-history";
import type { ProjectStyleProfile, Segment } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface TranslationPaneProps {
  pageUuid: string;
  pageIndex: number;
  projectUuid: string;
  editable?: boolean;
  styleControlsEnabled?: boolean;
}

interface TranslationPageEntry {
  segment: Segment;
  history: SegmentHistoryDto | undefined;
  translation: string;
  sourceAvailable: boolean;
  stale: boolean;
  protectedReference: ProtectedReferenceSummary | null;
  sentenceIndexInPage: number;
}

const ORIGIN = "translation";

export function TranslationPane({
  pageUuid,
  pageIndex,
  projectUuid,
  editable = false,
  styleControlsEnabled = false,
}: TranslationPaneProps): JSX.Element {
  const segmentsQ = useQuery(queries.pageSegments(pageUuid));
  const styleQ = useQuery(queries.projectStyleProfile(projectUuid));
  const persistedStyle = styleQ.data ?? DEFAULT_STYLE_PROFILE;
  const [styleDraft, setStyleDraft] = useState<ProjectStyleProfile>(persistedStyle);
  const histories = useQueries({
    queries: (segmentsQ.data ?? []).map((s) => ({
      ...queries.segmentHistory(s.satz_uuid),
    })),
  });

  const entries = useMemo<TranslationPageEntry[]>(
    () =>
      (segmentsQ.data ?? []).map((segment, i) => {
        const history = histories[i]?.data;
        const translationRevision = getLatestTranslationRevision(history);
        return {
          segment,
          history,
          translation: translationRevision?.text ?? "",
          sourceAvailable: Boolean(getLatestSourceRevision(history)),
          stale: isTranslationStale(history),
          protectedReference: getLatestProtectedReference(history),
          sentenceIndexInPage: i + 1,
        };
      }),
    [histories, segmentsQ.data],
  );

  useEffect(() => {
    setStyleDraft(persistedStyle);
  }, [persistedStyle]);

  const effectiveStyle = styleControlsEnabled ? styleDraft : persistedStyle;

  if (segmentsQ.isLoading) {
    return <p className="text-sm text-muted-foreground p-3">Loading translation page…</p>;
  }
  if (segmentsQ.isError) {
    return <p className="text-sm text-destructive p-3">Failed to load translation.</p>;
  }
  if (!segmentsQ.data || segmentsQ.data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground p-3">
        No OCR anchors yet on this page. Run OCR before translating.
      </p>
    );
  }

  if (editable) {
    return (
      <TranslationPageEditor
        pageUuid={pageUuid}
        pageIndex={pageIndex}
        projectUuid={projectUuid}
        entries={entries}
        styleProfile={effectiveStyle}
        persistedStyleProfile={persistedStyle}
        onStyleProfileChange={setStyleDraft}
        styleControlsEnabled={styleControlsEnabled}
      />
    );
  }

  return (
    <TranslationPageReadView
      pageIndex={pageIndex}
      projectUuid={projectUuid}
      entries={entries}
      styleProfile={effectiveStyle}
      persistedStyleProfile={persistedStyle}
      onStyleProfileChange={setStyleDraft}
      styleControlsEnabled={styleControlsEnabled}
    />
  );
}

interface TranslationPageViewProps {
  pageIndex: number;
  projectUuid: string;
  entries: TranslationPageEntry[];
  styleProfile: ProjectStyleProfile;
  persistedStyleProfile: ProjectStyleProfile;
  onStyleProfileChange: (profile: ProjectStyleProfile) => void;
  styleControlsEnabled: boolean;
}

function TranslationPageReadView({
  pageIndex,
  projectUuid,
  entries,
  styleProfile,
  persistedStyleProfile,
  onStyleProfileChange,
  styleControlsEnabled,
}: TranslationPageViewProps): JSX.Element {
  const staleCount = entries.filter((entry) => entry.stale).length;
  const textStyle = translationTextStyle(styleProfile);

  return (
    <div className="h-full overflow-auto bg-[#f4efe6] px-3 py-4">
      <article
        className="mx-auto min-h-full rounded-[1.75rem] border border-[#e7decf] bg-[#fffdf8] px-6 py-8 shadow-sm sm:px-10 sm:py-12"
        style={{ maxWidth: `${styleProfile.page_max_width_rem}rem` }}
      >
        {styleControlsEnabled && (
          <TranslationStyleControls
            projectUuid={projectUuid}
            profile={styleProfile}
            persistedProfile={persistedStyleProfile}
            onProfileChange={onStyleProfileChange}
          />
        )}
        <TranslationPageHeader
          pageIndex={pageIndex}
          entries={entries}
          staleCount={staleCount}
          mode="read"
        />

        <div
          className="mt-8 whitespace-pre-wrap text-left text-[#252820]"
          style={textStyle}
        >
          {entries.map((entry) => (
            <TranslationPageAnchor
              key={entry.segment.satz_uuid}
              entry={entry}
              pageIndex={pageIndex}
            >
              <TranslationText
                entry={entry}
                paragraphStyle={translationParagraphStyle(
                  styleProfile,
                  entry.segment.block_type,
                  Boolean(entry.protectedReference),
                )}
              />
            </TranslationPageAnchor>
          ))}
        </div>
      </article>
    </div>
  );
}

interface TranslationPageEditorProps {
  pageUuid: string;
  pageIndex: number;
  projectUuid: string;
  entries: TranslationPageEntry[];
  styleProfile: ProjectStyleProfile;
  persistedStyleProfile: ProjectStyleProfile;
  onStyleProfileChange: (profile: ProjectStyleProfile) => void;
  styleControlsEnabled: boolean;
}

function TranslationPageEditor({
  pageUuid,
  pageIndex,
  projectUuid,
  entries,
  styleProfile,
  persistedStyleProfile,
  onStyleProfileChange,
  styleControlsEnabled,
}: TranslationPageEditorProps): JSX.Element {
  const qc = useQueryClient();
  const pageText = useMemo(
    () => entries.map((entry) => entry.translation).join("\n\n"),
    [entries],
  );
  const staleCount = entries.filter((entry) => entry.stale).length;
  const [draft, setDraft] = useState(pageText);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDraft(pageText);
    setError(null);
  }, [pageText, pageUuid]);

  const saveMutation = useMutation({
    mutationFn: async (nextText: string) => {
      const chunks = splitDraftForSegments(nextText, entries.length);
      await Promise.all(
        entries.map((entry, i) =>
          api.put<Segment>(`/segments/${entry.segment.satz_uuid}/translation-text`, {
            after_text: chunks[i] ?? "",
          }),
        ),
      );
    },
    onSuccess: async () => {
      setError(null);
      await Promise.all([
        qc.invalidateQueries({ queryKey: qk.pageSegments(pageUuid) }),
        ...entries.map((entry) =>
          qc.invalidateQueries({
            queryKey: ["segments", entry.segment.satz_uuid, "history"],
          }),
        ),
      ]);
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : "Save failed");
      if (err instanceof ApiError) setError(err.detail);
    },
  });

  const isLegacyMultiSegment = entries.length > 1;
  const textStyle = translationTextStyle(styleProfile);

  return (
    <div className="h-full overflow-auto bg-[#f4efe6] px-3 py-4">
      <article
        className="mx-auto flex min-h-full flex-col rounded-[1.75rem] border border-[#e7decf] bg-[#fffdf8] px-4 py-5 shadow-sm sm:px-8 sm:py-8"
        style={{ maxWidth: `${styleProfile.page_max_width_rem}rem` }}
      >
        {styleControlsEnabled && (
          <TranslationStyleControls
            projectUuid={projectUuid}
            profile={styleProfile}
            persistedProfile={persistedStyleProfile}
            onProfileChange={onStyleProfileChange}
          />
        )}
        <TranslationPageHeader
          pageIndex={pageIndex}
          entries={entries}
          staleCount={staleCount}
          mode="edit"
        />

        {isLegacyMultiSegment && (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-900">
            This older page still has {entries.length} internal translation anchors. Keep one
            blank line between those text blocks when saving so Waraq can preserve history links.
          </div>
        )}

        <Textarea
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            setError(null);
          }}
          spellCheck
          className="mt-5 min-h-[58vh] flex-1 resize-y rounded-[1.25rem] border-[#d8cdbb] bg-[#fffaf0] px-5 py-5 text-left text-[#252820] shadow-inner"
          style={textStyle}
          aria-label={`Editable translation text for page ${pageIndex}`}
        />

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            onClick={() => saveMutation.mutate(draft)}
            disabled={saveMutation.isPending || draft === pageText}
          >
            {saveMutation.isPending ? "Saving…" : "Save translation page"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setDraft(pageText);
              setError(null);
            }}
            disabled={saveMutation.isPending || draft === pageText}
          >
            Reset changes
          </Button>
          <span className="text-xs text-muted-foreground">
            Protected Quran/Hadith source badges remain visible in read mode after saving.
          </span>
        </div>

        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </article>
    </div>
  );
}

interface TranslationPageHeaderProps {
  pageIndex: number;
  entries: TranslationPageEntry[];
  staleCount: number;
  mode: "read" | "edit";
}

function TranslationPageHeader({
  pageIndex,
  entries,
  staleCount,
  mode,
}: TranslationPageHeaderProps): JSX.Element {
  const translatedCount = entries.filter((entry) => entry.translation.trim()).length;
  const protectedCount = entries.filter(
    (entry) => entry.translation.trim() && entry.protectedReference,
  ).length;

  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[#eee5d6] pb-4">
      <div>
        <p className="text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          Translation
        </p>
        <h3 className="mt-1 text-xl font-semibold text-[#1d221d]">Page {pageIndex}</h3>
      </div>
      <div className="flex flex-wrap justify-end gap-2 text-[11px]">
        <span className="rounded-full bg-muted px-2.5 py-1 text-muted-foreground">
          {translatedCount}/{entries.length} translated
        </span>
        {protectedCount > 0 && (
          <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-emerald-800">
            {protectedCount} protected source{protectedCount === 1 ? "" : "s"}
          </span>
        )}
        {staleCount > 0 && (
          <span className="rounded-full bg-amber-100 px-2.5 py-1 text-amber-900">
            {staleCount} outdated translation{staleCount === 1 ? "" : "s"}
          </span>
        )}
        <span className="rounded-full bg-[#113f2b] px-2.5 py-1 text-white">
          {mode === "edit" ? "Page edit" : "Page view"}
        </span>
      </div>
    </header>
  );
}

interface TranslationPageAnchorProps {
  entry: TranslationPageEntry;
  pageIndex: number;
  children: ReactNode;
}

function TranslationPageAnchor({
  entry,
  pageIndex,
  children,
}: TranslationPageAnchorProps): JSX.Element {
  const localRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const unsubscribe = onSentenceJump((detail) => {
      if (detail.origin === ORIGIN) return;
      if (detail.satzUuid !== entry.segment.satz_uuid) return;
      localRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    return unsubscribe;
  }, [entry.segment.satz_uuid]);

  return (
    <section
      ref={localRef}
      data-satz-uuid={entry.segment.satz_uuid}
      className={cn(
        "group relative rounded-xl px-2 py-1 transition-colors hover:bg-emerald-50/50",
        entry.stale && "bg-amber-50/60",
      )}
    >
      <button
        type="button"
        onClick={() => emitSentenceJump({ satzUuid: entry.segment.satz_uuid, origin: ORIGIN })}
        className="absolute -left-1 top-1 rounded-full bg-[#fffaf0] px-2 py-0.5 font-mono text-[9px] uppercase tracking-wide text-muted-foreground opacity-0 shadow-sm transition-opacity hover:text-primary group-hover:opacity-100"
        title="Click to sync all panes to this translation anchor"
      >
        {formatSentenceId(pageIndex, entry.sentenceIndexInPage)}
      </button>
      {children}
    </section>
  );
}

function TranslationText({
  entry,
  paragraphStyle,
}: {
  entry: TranslationPageEntry;
  paragraphStyle: CSSProperties;
}): JSX.Element {
  const [referenceOpen, setReferenceOpen] = useState(false);
  const canOpenProtectedReference = Boolean(entry.protectedReference && entry.translation);

  if (!entry.translation) {
    return (
      <p className="text-sm italic text-muted-foreground">
        No translation yet.
      </p>
    );
  }

  return (
    <>
      <p
        className={cn(
          entry.stale && "text-amber-950",
          canOpenProtectedReference &&
            "cursor-pointer underline decoration-dotted underline-offset-4",
        )}
        style={paragraphStyle}
        title={entry.protectedReference?.hoverText}
        onClick={() => {
          if (canOpenProtectedReference) setReferenceOpen(true);
        }}
      >
        {entry.translation}
      </p>

      <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px]">
        {entry.protectedReference && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => setReferenceOpen(true)}
            title={entry.protectedReference.hoverText}
          >
            {entry.protectedReference.badgeLabel}
          </Button>
        )}
        {entry.sourceAvailable && (
          <span className="rounded-full bg-muted px-2 py-0.5 text-muted-foreground">
            Source available
          </span>
        )}
        {entry.stale && (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-800">
            OCR changed after translation
          </span>
        )}
      </div>

      {entry.protectedReference && (
        <ProtectedReferenceDialog
          reference={entry.protectedReference}
          open={referenceOpen}
          onOpenChange={setReferenceOpen}
        />
      )}
    </>
  );
}

interface ProtectedReferenceDialogProps {
  reference: ProtectedReferenceSummary;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function ProtectedReferenceDialog({
  reference,
  open,
  onOpenChange,
}: ProtectedReferenceDialogProps): JSX.Element {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{reference.title}</DialogTitle>
          <DialogDescription>
            {reference.subtitle ?? "Attached from the latest translation provenance."}
          </DialogDescription>
        </DialogHeader>
        {reference.sources.length > 0 ? (
          <ul className="space-y-2 text-sm leading-relaxed text-foreground">
            {reference.sources.map((sourceLine) => (
              <li key={sourceLine} className="rounded-md border bg-muted/30 px-3 py-2">
                {sourceLine}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">
            No protected reference sources were recorded on this translation.
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
}

export interface TranslationStyleControlsProps {
  projectUuid: string;
  profile: ProjectStyleProfile;
  persistedProfile: ProjectStyleProfile;
  onProfileChange: (profile: ProjectStyleProfile) => void;
}

export function TranslationStyleControls({
  projectUuid,
  profile,
  persistedProfile,
  onProfileChange,
}: TranslationStyleControlsProps): JSX.Element {
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const saveMutation = useMutation({
    mutationFn: (nextProfile: ProjectStyleProfile) =>
      api.put<ProjectStyleProfile>(`/projects/${projectUuid}/style-profile`, nextProfile),
    onSuccess: async (saved) => {
      onProfileChange(saved);
      setError(null);
      await qc.invalidateQueries({ queryKey: qk.projectStyleProfile(projectUuid) });
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Style save failed"),
  });

  return (
    <section className="mb-5 rounded-2xl border border-[#e7decf] bg-[#fbf6ed] p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-medium text-[#1d221d]">Project style profile</p>
          <p className="text-[11px] text-muted-foreground">
            Applies to workspace pages and the next DOCX/PDF export.
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => saveMutation.mutate(profile)}
          disabled={saveMutation.isPending || shallowEqualProfile(profile, persistedProfile)}
        >
          {saveMutation.isPending ? "Saving…" : "Save style"}
        </Button>
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StyleField label="Translation font">
          <select
            value={profile.translation_font_family}
            onChange={(e) =>
              onProfileChange({
                ...profile,
                translation_font_family: e.target.value,
                docx_translation_font_family: e.target.value,
              })
            }
            className="h-8 w-full rounded border bg-background px-2 text-xs"
          >
            {TRANSLATION_FONT_OPTIONS.map((font) => (
              <option key={font} value={font}>
                {font}
              </option>
            ))}
          </select>
        </StyleField>
        <StyleNumberField
          label="Text size"
          value={profile.translation_font_size_px}
          min={13}
          max={26}
          suffix="px"
          onChange={(value) =>
            onProfileChange({
              ...profile,
              translation_font_size_px: value,
              docx_translation_font_size_pt: pxToDocxPt(value, 9, 16),
            })
          }
        />
        <StyleNumberField
          label="Line height"
          value={profile.translation_line_height}
          min={1.25}
          max={2.6}
          step={0.05}
          onChange={(value) =>
            onProfileChange({
              ...profile,
              translation_line_height: value,
              docx_line_spacing: clampNumber(value, 1, 2),
            })
          }
        />
        <StyleNumberField
          label="Paragraph gap"
          value={profile.translation_paragraph_spacing_px}
          min={8}
          max={40}
          suffix="px"
          onChange={(value) =>
            onProfileChange({
              ...profile,
              translation_paragraph_spacing_px: value,
              docx_paragraph_spacing_pt: clampNumber(Math.round(value * 0.35), 0, 18),
            })
          }
        />
        <StyleNumberField
          label="Heading size"
          value={profile.heading_font_size_px}
          min={16}
          max={38}
          suffix="px"
          onChange={(value) =>
            onProfileChange({
              ...profile,
              heading_font_size_px: value,
              docx_heading_font_size_pt: pxToDocxPt(value, 11, 24),
            })
          }
        />
        <StyleNumberField
          label="Heading gap"
          value={profile.heading_paragraph_spacing_px}
          min={8}
          max={52}
          suffix="px"
          onChange={(value) =>
            onProfileChange({
              ...profile,
              heading_paragraph_spacing_px: value,
            })
          }
        />
        <StyleNumberField
          label="Quote size"
          value={profile.quote_font_size_px}
          min={12}
          max={24}
          suffix="px"
          onChange={(value) =>
            onProfileChange({
              ...profile,
              quote_font_size_px: value,
              docx_quote_font_size_pt: pxToDocxPt(value, 8, 14),
            })
          }
        />
        <StyleNumberField
          label="Quote line"
          value={profile.quote_line_height}
          min={1.2}
          max={2.4}
          step={0.05}
          onChange={(value) => onProfileChange({ ...profile, quote_line_height: value })}
        />
        <StyleNumberField
          label="Footnote size"
          value={profile.footnote_font_size_px}
          min={10}
          max={20}
          suffix="px"
          onChange={(value) =>
            onProfileChange({
              ...profile,
              footnote_font_size_px: value,
              docx_footnote_font_size_pt: pxToDocxPt(value, 7, 12),
            })
          }
        />
        <StyleNumberField
          label="Quran/Hadith"
          value={profile.protected_font_size_px}
          min={12}
          max={24}
          suffix="px"
          onChange={(value) =>
            onProfileChange({
              ...profile,
              protected_font_size_px: value,
              docx_protected_font_size_pt: pxToDocxPt(value, 8, 14),
            })
          }
        />
        <StyleNumberField
          label="Arabic size"
          value={profile.arabic_font_size_px}
          min={16}
          max={34}
          suffix="px"
          onChange={(value) =>
            onProfileChange({
              ...profile,
              arabic_font_size_px: value,
              docx_arabic_font_size_pt: pxToDocxPt(value, 10, 22),
            })
          }
        />
        <StyleField label="Arabic font">
          <select
            value={profile.arabic_font_family}
            onChange={(e) =>
              onProfileChange({
                ...profile,
                arabic_font_family: e.target.value,
                docx_arabic_font_family: e.target.value,
              })
            }
            className="h-8 w-full rounded border bg-background px-2 text-xs"
          >
            {ARABIC_FONT_OPTIONS.map((font) => (
              <option key={font} value={font}>
                {font}
              </option>
            ))}
          </select>
        </StyleField>
        <StyleNumberField
          label="Arabic line"
          value={profile.arabic_line_height}
          min={1.6}
          max={3}
          step={0.05}
          onChange={(value) =>
            onProfileChange({
              ...profile,
              arabic_line_height: value,
              docx_line_spacing: clampNumber(value, 1, 2),
            })
          }
        />
        <StyleNumberField
          label="Page width"
          value={profile.page_max_width_rem}
          min={38}
          max={72}
          suffix="rem"
          onChange={(value) => onProfileChange({ ...profile, page_max_width_rem: value })}
        />
        <StyleNumberField
          label="DOCX text"
          value={profile.docx_translation_font_size_pt}
          min={9}
          max={16}
          suffix="pt"
          onChange={(value) =>
            onProfileChange({ ...profile, docx_translation_font_size_pt: value })
          }
        />
        <StyleNumberField
          label="DOCX Arabic"
          value={profile.docx_arabic_font_size_pt}
          min={10}
          max={22}
          suffix="pt"
          onChange={(value) =>
            onProfileChange({ ...profile, docx_arabic_font_size_pt: value })
          }
        />
        <StyleNumberField
          label="DOCX header"
          value={profile.docx_header_font_size_pt}
          min={7}
          max={14}
          suffix="pt"
          onChange={(value) =>
            onProfileChange({ ...profile, docx_header_font_size_pt: value })
          }
        />
      </div>
      {!shallowEqualProfile(profile, persistedProfile) && (
        <p className="mt-2 text-[11px] text-amber-800">
          Previewing unsaved style changes. Save style before running a new export.
        </p>
      )}
      {error && <p className="mt-2 text-xs text-destructive">{error}</p>}
    </section>
  );
}

function StyleField({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}): JSX.Element {
  return (
    <label className="space-y-1">
      <span className="block text-[11px] text-muted-foreground">{label}</span>
      {children}
    </label>
  );
}

function StyleNumberField({
  label,
  value,
  min,
  max,
  step = 1,
  suffix,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  suffix?: string;
  onChange: (value: number) => void;
}): JSX.Element {
  return (
    <StyleField label={label}>
      <div className="flex items-center gap-2">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="min-w-0 flex-1"
        />
        <span className="w-12 text-right text-[11px] text-muted-foreground">
          {value}
          {suffix}
        </span>
      </div>
    </StyleField>
  );
}

function splitDraftForSegments(draft: string, expectedCount: number): string[] {
  if (expectedCount <= 1) return [draft];
  const chunks = draft.split(/\n\s*\n/g);
  if (chunks.length !== expectedCount) {
    throw new Error(
      `This page has ${expectedCount} internal translation anchors. Keep exactly one blank line between each block before saving, or rerun OCR/translation so the page becomes one full-page translation block.`,
    );
  }
  return chunks;
}

const TRANSLATION_FONT_OPTIONS = [
  "Iowan Old Style",
  "Source Serif 4",
  "Libre Baskerville",
  "Georgia",
  "Times New Roman",
] as const;

const ARABIC_FONT_OPTIONS = [
  "Noto Naskh Arabic",
  "Amiri",
  "Scheherazade New",
  "Traditional Arabic",
] as const;

export const DEFAULT_STYLE_PROFILE: ProjectStyleProfile = {
  translation_font_family: "Iowan Old Style",
  translation_font_size_px: 17,
  translation_line_height: 1.95,
  translation_paragraph_spacing_px: 20,
  heading_font_size_px: 25,
  heading_line_height: 1.35,
  heading_paragraph_spacing_px: 24,
  quote_font_size_px: 16,
  quote_line_height: 1.85,
  quote_paragraph_spacing_px: 18,
  footnote_font_size_px: 14,
  footnote_line_height: 1.65,
  footnote_paragraph_spacing_px: 10,
  protected_font_size_px: 16,
  protected_line_height: 1.9,
  protected_paragraph_spacing_px: 16,
  arabic_font_family: "Noto Naskh Arabic",
  arabic_font_size_px: 22,
  arabic_line_height: 2.35,
  page_max_width_rem: 54,
  docx_translation_font_family: "Times New Roman",
  docx_translation_font_size_pt: 11,
  docx_arabic_font_family: "Noto Naskh Arabic",
  docx_arabic_font_size_pt: 14,
  docx_line_spacing: 1.25,
  docx_paragraph_spacing_pt: 6,
  docx_heading_font_size_pt: 16,
  docx_quote_font_size_pt: 10,
  docx_footnote_font_size_pt: 9,
  docx_protected_font_size_pt: 11,
  docx_header_font_size_pt: 9,
};

export function translationTextStyle(profile: ProjectStyleProfile): CSSProperties {
  return {
    fontFamily: `"${profile.translation_font_family}", Georgia, serif`,
    fontSize: `${profile.translation_font_size_px}px`,
    lineHeight: profile.translation_line_height,
  };
}

export function translationParagraphStyle(
  profile: ProjectStyleProfile,
  blockType?: string | null,
  protectedReference = false,
): CSSProperties {
  const kind = styleKindForBlock(blockType, protectedReference);
  if (kind === "heading") {
    return {
      fontSize: `${profile.heading_font_size_px}px`,
      fontWeight: 700,
      letterSpacing: "-0.01em",
      lineHeight: profile.heading_line_height,
      marginBottom: `${profile.heading_paragraph_spacing_px}px`,
    };
  }
  if (kind === "quote") {
    return {
      borderLeft: "3px solid #d7c39c",
      fontSize: `${profile.quote_font_size_px}px`,
      fontStyle: "italic",
      lineHeight: profile.quote_line_height,
      marginBottom: `${profile.quote_paragraph_spacing_px}px`,
      paddingLeft: "1rem",
    };
  }
  if (kind === "footnote") {
    return {
      fontSize: `${profile.footnote_font_size_px}px`,
      lineHeight: profile.footnote_line_height,
      marginBottom: `${profile.footnote_paragraph_spacing_px}px`,
    };
  }
  if (kind === "protected") {
    return {
      backgroundColor: "#f5efe1",
      borderRadius: "1rem",
      fontSize: `${profile.protected_font_size_px}px`,
      lineHeight: profile.protected_line_height,
      marginBottom: `${profile.protected_paragraph_spacing_px}px`,
      padding: "0.85rem 1rem",
    };
  }
  return {
    marginBottom: `${profile.translation_paragraph_spacing_px}px`,
  };
}

export function styleKindForBlock(
  blockType?: string | null,
  protectedReference = false,
): "body" | "heading" | "quote" | "footnote" | "protected" {
  if (protectedReference) return "protected";
  const normalized = (blockType ?? "").trim().toLowerCase();
  if (["ue", "hd", "heading"].includes(normalized)) return "heading";
  if (["fn", "footnote"].includes(normalized)) return "footnote";
  if (["quran", "hadith"].includes(normalized)) return "protected";
  if (["qr", "quote", "marginalia", "rn", "caption"].includes(normalized)) {
    return "quote";
  }
  return "body";
}

function shallowEqualProfile(a: ProjectStyleProfile, b: ProjectStyleProfile): boolean {
  return Object.keys(DEFAULT_STYLE_PROFILE).every(
    (key) => a[key as keyof ProjectStyleProfile] === b[key as keyof ProjectStyleProfile],
  );
}

function pxToDocxPt(px: number, min: number, max: number): number {
  return clampNumber(Math.round(px * 0.65), min, max);
}

function clampNumber(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, Number(value.toFixed(2))));
}
