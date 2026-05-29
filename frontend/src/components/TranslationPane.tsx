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
import { mergeAttributes, type Editor } from "@tiptap/core";
import Paragraph from "@tiptap/extension-paragraph";
import TextAlign from "@tiptap/extension-text-align";
import Underline from "@tiptap/extension-underline";
import { EditorContent, useEditor, type JSONContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlignCenter,
  AlignJustify,
  AlignLeft,
  Bold,
  Italic,
  Pilcrow,
  Save,
  Strikethrough,
  Underline as UnderlineIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import {
  defaultTranslationStyleKey,
  effectiveTranslationStyleTemplates,
  normalizeTranslationStyleKey,
  TRANSLATION_STYLE_DEFINITIONS,
  translationStyleCss,
  withUpdatedTranslationStyleTemplate,
  type TranslationStyleKey,
  type TranslationStyleTemplate,
} from "@/lib/translation-styles";
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
  styleKey: TranslationStyleKey;
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
          styleKey: normalizeTranslationStyleKey(
            segment.translation_style_key ??
              defaultTranslationStyleKey(segment.block_type, Boolean(getLatestProtectedReference(history))),
          ),
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
    <div className="h-full overflow-y-scroll bg-[#f4efe6] px-3 py-4">
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
                paragraphStyle={translationStyleCss(styleProfile, entry.styleKey)}
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
}: TranslationPageEditorProps): JSX.Element {
  const qc = useQueryClient();
  const editorContent = useMemo(() => entriesToTipTapDoc(entries), [entries]);
  const initialSignature = useMemo(() => JSON.stringify(editorContent), [editorContent]);
  const staleCount = entries.filter((entry) => entry.stale).length;
  const [error, setError] = useState<string | null>(null);
  const [currentStyleKey, setCurrentStyleKey] = useState<TranslationStyleKey>(
    entries[0]?.styleKey ?? "body_de",
  );
  const [dirty, setDirty] = useState(false);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({ paragraph: false }),
      StyledParagraph,
      Underline,
      TextAlign.configure({ types: ["paragraph"] }),
    ],
    content: editorContent,
    editorProps: {
      attributes: {
        class:
          "waraq-translation-editor min-h-[58vh] rounded-[1.25rem] border border-[#d8cdbb] bg-[#fffaf0] px-5 py-5 text-left text-[#252820] shadow-inner outline-none",
      },
    },
    onUpdate: () => {
      setDirty(true);
      setError(null);
    },
    onSelectionUpdate: ({ editor: activeEditor }) => {
      setCurrentStyleKey(activeParagraphStyleKey(activeEditor.getAttributes("paragraph")));
    },
  });

  useEffect(() => {
    if (!editor) return;
    editor.commands.setContent(editorContent);
    setCurrentStyleKey(entries[0]?.styleKey ?? "body_de");
    setDirty(false);
    setError(null);
  }, [editor, editorContent, entries, pageUuid]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!editor) return;
      const chunks = paragraphsFromTipTapDoc(editor.getJSON(), entries.length);
      await Promise.all(
        entries.map((entry, i) =>
          Promise.all([
            api.put<Segment>(`/segments/${entry.segment.satz_uuid}/translation-text`, {
              after_text: chunks[i]?.text ?? "",
            }),
            chunks[i]?.styleKey !== entry.styleKey
              ? api.put<Segment>(`/segments/${entry.segment.satz_uuid}/translation-style`, {
                  internal_style_key: chunks[i]?.styleKey ?? "body_de",
                })
              : Promise.resolve(),
          ]),
        ),
      );
    },
    onSuccess: async () => {
      setError(null);
      setDirty(false);
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
  const canSave = Boolean(editor) && dirty && !saveMutation.isPending;

  return (
    <div className="flex h-full min-h-0 flex-col bg-[#f4efe6]">
      <WordLikeTranslationToolbar
        editor={editor}
        projectUuid={projectUuid}
        profile={styleProfile}
        persistedProfile={persistedStyleProfile}
        currentStyleKey={currentStyleKey}
        dirty={dirty}
        saving={saveMutation.isPending}
        canSave={canSave}
        onProfileChange={onStyleProfileChange}
        onStyleKeyChange={(styleKey) => {
          editor?.chain().focus().updateAttributes("paragraph", { styleKey }).run();
          setCurrentStyleKey(styleKey);
          setDirty(true);
        }}
        onSave={() => saveMutation.mutate()}
        onReset={() => {
          editor?.commands.setContent(JSON.parse(initialSignature) as JSONContent);
          setDirty(false);
          setError(null);
        }}
      />
      <div className="min-h-0 flex-1 overflow-y-scroll px-3 py-4">
      <article
        className="mx-auto flex min-h-full flex-col border border-[#ddd4c4] bg-[#fffdf8] px-8 py-10 shadow-md sm:px-14 sm:py-14"
        style={{ width: "min(100%, 52rem)" }}
      >
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

        <div className="mt-5">
          <TranslationEditorStyleElement profile={styleProfile} />
          <EditorContent
            editor={editor}
            style={textStyle}
            aria-label={`Editable translation text for page ${pageIndex}`}
          />
        </div>

        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </article>
      </div>
    </div>
  );
}

function WordLikeTranslationToolbar({
  editor,
  projectUuid,
  profile,
  persistedProfile,
  currentStyleKey,
  dirty,
  saving,
  canSave,
  onProfileChange,
  onStyleKeyChange,
  onSave,
  onReset,
}: {
  editor: Editor | null;
  projectUuid: string;
  profile: ProjectStyleProfile;
  persistedProfile: ProjectStyleProfile;
  currentStyleKey: TranslationStyleKey;
  dirty: boolean;
  saving: boolean;
  canSave: boolean;
  onProfileChange: (profile: ProjectStyleProfile) => void;
  onStyleKeyChange: (styleKey: TranslationStyleKey) => void;
  onSave: () => void;
  onReset: () => void;
}): JSX.Element {
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const guardNearQ = useQuery({
    queryKey: ["projects", projectUuid, "preflight", "guard-near"],
    queryFn: () => api.get<GuardNearPreview>(`/projects/${projectUuid}/preflight/guard-near`),
    staleTime: 30_000,
  });
  const fontLibraryQ = useQuery({
    queryKey: ["projects", projectUuid, "style-profile", "fonts"],
    queryFn: () => api.get<FontLibraryResponse>(`/projects/${projectUuid}/style-profile/fonts`),
    staleTime: 60_000,
  });

  const styleSaveMutation = useMutation({
    mutationFn: (nextProfile: ProjectStyleProfile) =>
      api.put<ProjectStyleProfile>(`/projects/${projectUuid}/style-profile`, nextProfile),
    onSuccess: async (saved) => {
      onProfileChange(saved);
      setError(null);
      await qc.invalidateQueries({ queryKey: qk.projectStyleProfile(projectUuid) });
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Style save failed"),
  });

  const disabled = !editor || saving;
  const styleDirty = !shallowEqualProfile(profile, persistedProfile);
  const templates = effectiveTranslationStyleTemplates(profile);
  const selectedTemplate = templates[currentStyleKey];
  const missingFonts = guardNearQ.data?.evidence.critical_font_missing ?? [];
  const fontOptions = Array.from(
    new Set([
      selectedTemplate.font_family,
      ...(fontLibraryQ.data?.available_fonts.length
        ? fontLibraryQ.data.available_fonts
        : STYLE_FONT_OPTIONS),
    ]),
  ).filter(Boolean);
  const updateSelectedTemplate = (patch: Partial<TranslationStyleTemplate>) => {
    onProfileChange(withUpdatedTranslationStyleTemplate(profile, currentStyleKey, patch));
  };

  return (
    <div className="shrink-0 border-b border-[#ded6c7] bg-[#fbfaf6] px-3 py-2 shadow-sm">
      <div className="flex min-h-10 flex-wrap items-center gap-1.5">
        <ToolbarSelect
          label="Paragraph style"
          value={currentStyleKey}
          disabled={disabled}
          onChange={(value) => onStyleKeyChange(normalizeTranslationStyleKey(value))}
          className="w-40"
        >
          {TRANSLATION_STYLE_DEFINITIONS.map((style) => (
            <option key={style.key} value={style.key}>
              {templates[style.key].display_label || style.label}
            </option>
          ))}
        </ToolbarSelect>

        <ToolbarSelect
          label="Style font"
          value={selectedTemplate.font_family}
          disabled={styleSaveMutation.isPending}
          onChange={(value) => updateSelectedTemplate({ font_family: value })}
          className="w-36"
        >
          {fontOptions.map((font) => (
            <option key={font} value={font}>
              {font}
            </option>
          ))}
        </ToolbarSelect>

        <ToolbarSelect
          label="Text size"
          value={selectedTemplate.font_size_px}
          disabled={styleSaveMutation.isPending}
          onChange={(value) => {
            const size = Number(value);
            updateSelectedTemplate({
              font_size_px: size,
              docx_font_size_pt: pxToDocxPt(size, 6, 32),
            });
          }}
          className="w-16"
        >
          {[10, 11, 12, 13, 14, 15, 16, 18, 20, 22, 24, 26].map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </ToolbarSelect>

        <ToolbarDivider />

        <ToolbarIconButton
          label="Style bold"
          active={selectedTemplate.bold}
          disabled={styleSaveMutation.isPending}
          onClick={() => updateSelectedTemplate({ bold: !selectedTemplate.bold })}
        >
          <Bold className="h-4 w-4" />
        </ToolbarIconButton>
        <ToolbarIconButton
          label="Style italic"
          active={selectedTemplate.italic}
          disabled={styleSaveMutation.isPending}
          onClick={() => updateSelectedTemplate({ italic: !selectedTemplate.italic })}
        >
          <Italic className="h-4 w-4" />
        </ToolbarIconButton>
        <ToolbarIconButton
          label="Underline"
          active={editor?.isActive("underline")}
          disabled={disabled}
          onClick={() => editor?.chain().focus().toggleUnderline().run()}
        >
          <UnderlineIcon className="h-4 w-4" />
        </ToolbarIconButton>
        <ToolbarIconButton
          label="Strike"
          active={editor?.isActive("strike")}
          disabled={disabled}
          onClick={() => editor?.chain().focus().toggleStrike().run()}
        >
          <Strikethrough className="h-4 w-4" />
        </ToolbarIconButton>

        <ToolbarDivider />

        <ToolbarIconButton
          label="Align left"
          active={selectedTemplate.alignment === "left"}
          disabled={styleSaveMutation.isPending}
          onClick={() => updateSelectedTemplate({ alignment: "left" })}
        >
          <AlignLeft className="h-4 w-4" />
        </ToolbarIconButton>
        <ToolbarIconButton
          label="Align center"
          active={selectedTemplate.alignment === "center"}
          disabled={styleSaveMutation.isPending}
          onClick={() => updateSelectedTemplate({ alignment: "center" })}
        >
          <AlignCenter className="h-4 w-4" />
        </ToolbarIconButton>
        <ToolbarIconButton
          label="Justify"
          active={selectedTemplate.alignment === "justify"}
          disabled={styleSaveMutation.isPending}
          onClick={() => updateSelectedTemplate({ alignment: "justify" })}
        >
          <AlignJustify className="h-4 w-4" />
        </ToolbarIconButton>

        <ToolbarDivider />

        <ToolbarSelect
          label="Line height"
          value={selectedTemplate.line_height}
          disabled={styleSaveMutation.isPending}
          onChange={(value) => updateSelectedTemplate({ line_height: Number(value) })}
          className="w-20"
        >
          {[1, 1.15, 1.3, 1.5, 1.6, 1.8, 2].map((lineHeight) => (
            <option key={lineHeight} value={lineHeight}>
              {lineHeight}
            </option>
          ))}
        </ToolbarSelect>

        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-8 px-2 text-xs"
          disabled={disabled}
          onClick={() => onStyleKeyChange("footnote_text")}
          title="Apply footnote paragraph style"
        >
          <Pilcrow className="mr-1 h-3.5 w-3.5" />
          Footnote
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-8 px-2 text-xs"
          disabled={disabled}
          onClick={() =>
            editor &&
            applyStyleSequenceToAnchoredParagraphs(editor, ["quran_de", "quran_de", "source_note"])
          }
          title="Apply Quran block sequence to this and following anchored paragraphs"
        >
          Quran
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-8 px-2 text-xs"
          disabled={disabled}
          onClick={() =>
            editor &&
            applyStyleSequenceToAnchoredParagraphs(editor, ["hadith_de", "hadith_de", "source_note"])
          }
          title="Apply Hadith block sequence to this and following anchored paragraphs"
        >
          Hadith
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-8 px-2 text-xs"
          disabled={disabled}
          onClick={() =>
            editor &&
            applyStyleSequenceToAnchoredParagraphs(editor, ["quote_de", "quote_de", "source_note"])
          }
          title="Apply quote block sequence to this and following anchored paragraphs"
        >
          Quote
        </Button>

        <div className="ml-auto flex items-center gap-1.5">
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-8 px-2 text-xs"
            disabled={!dirty || saving}
            onClick={onReset}
          >
            Reset
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-8 px-2 text-xs"
            disabled={!styleDirty || styleSaveMutation.isPending}
            onClick={() => styleSaveMutation.mutate(profile)}
          >
            {styleSaveMutation.isPending ? "Saving style..." : "Save style"}
          </Button>
          <Button
            type="button"
            size="sm"
            className="h-8 px-2 text-xs"
            disabled={!canSave}
            onClick={onSave}
          >
            <Save className="mr-1 h-3.5 w-3.5" />
            {saving ? "Saving..." : "Save page"}
          </Button>
        </div>
      </div>
      <details className="mt-2 rounded border border-[#ded6c7] bg-white/60 px-2 py-1">
        <summary className="cursor-pointer select-none text-[11px] font-medium text-muted-foreground">
          Edit selected style template
        </summary>
        <div className="mt-2 grid gap-2 pb-1 text-xs sm:grid-cols-2 lg:grid-cols-6">
          <ToolbarTextInput
            label="Display label"
            value={selectedTemplate.display_label}
            disabled={styleSaveMutation.isPending}
            onChange={(value) => updateSelectedTemplate({ display_label: value })}
          />
          <ToolbarNumberInput
            label="Spacing"
            value={selectedTemplate.paragraph_spacing_px}
            min={0}
            max={72}
            disabled={styleSaveMutation.isPending}
            onChange={(value) => updateSelectedTemplate({ paragraph_spacing_px: value })}
          />
          <ToolbarNumberInput
            label="First indent"
            value={selectedTemplate.first_line_indent_px}
            min={-80}
            max={120}
            disabled={styleSaveMutation.isPending}
            onChange={(value) => updateSelectedTemplate({ first_line_indent_px: value })}
          />
          <ToolbarNumberInput
            label="Left indent"
            value={selectedTemplate.left_indent_px}
            min={0}
            max={160}
            disabled={styleSaveMutation.isPending}
            onChange={(value) => updateSelectedTemplate({ left_indent_px: value })}
          />
          <ToolbarNumberInput
            label="DOCX pt"
            value={selectedTemplate.docx_font_size_pt}
            min={6}
            max={32}
            disabled={styleSaveMutation.isPending}
            onChange={(value) => updateSelectedTemplate({ docx_font_size_pt: value })}
          />
          <label className="flex items-center justify-between gap-2 rounded border bg-background px-2 py-1">
            <span>Left rule</span>
            <input
              type="checkbox"
              checked={selectedTemplate.border_left}
              disabled={styleSaveMutation.isPending}
              onChange={(event) => updateSelectedTemplate({ border_left: event.target.checked })}
            />
          </label>
        </div>
      </details>
      {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
      {missingFonts.length > 0 && (
        <p className="mt-1 text-[11px] text-destructive">
          Missing critical export fonts: {missingFonts.join(", ")}. Install them before preflight/export.
        </p>
      )}
      {(dirty || styleDirty) && (
        <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-amber-800">
          {dirty && <span>Unsaved page edits</span>}
          {styleDirty && <span>Unsaved global style changes</span>}
        </div>
      )}
    </div>
  );
}

interface GuardNearPreview {
  passes: boolean;
  blockers: string[];
  advisories: string[];
  evidence: Record<string, string[]>;
}

interface FontLibraryResponse {
  available_fonts: string[];
  critical_fonts: string[];
  missing_critical_fonts: string[];
}

function ToolbarSelect({
  label,
  value,
  disabled,
  onChange,
  className,
  children,
}: {
  label: string;
  value: string | number;
  disabled?: boolean;
  onChange: (value: string) => void;
  className?: string;
  children: ReactNode;
}): JSX.Element {
  return (
    <select
      aria-label={label}
      title={label}
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      className={cn("h-8 rounded border bg-white px-2 text-xs shadow-sm disabled:opacity-50", className)}
    >
      {children}
    </select>
  );
}

function ToolbarIconButton({
  label,
  active,
  disabled,
  onClick,
  children,
}: {
  label: string;
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: ReactNode;
}): JSX.Element {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "grid h-8 w-8 place-items-center rounded border text-[#252820] shadow-sm disabled:opacity-50",
        active ? "border-[#0b4a36] bg-[#dfece7]" : "border-[#ded6c7] bg-white hover:bg-muted/70",
      )}
    >
      {children}
    </button>
  );
}

function ToolbarTextInput({
  label,
  value,
  disabled,
  onChange,
}: {
  label: string;
  value: string;
  disabled?: boolean;
  onChange: (value: string) => void;
}): JSX.Element {
  return (
    <label className="space-y-1">
      <span className="block text-[10px] text-muted-foreground">{label}</span>
      <input
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className="h-8 w-full rounded border bg-background px-2"
      />
    </label>
  );
}

function ToolbarNumberInput({
  label,
  value,
  min,
  max,
  disabled,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  disabled?: boolean;
  onChange: (value: number) => void;
}): JSX.Element {
  return (
    <label className="space-y-1">
      <span className="block text-[10px] text-muted-foreground">{label}</span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        disabled={disabled}
        onChange={(event) => onChange(Number(event.target.value))}
        className="h-8 w-full rounded border bg-background px-2"
      />
    </label>
  );
}

function ToolbarDivider(): JSX.Element {
  return <span className="mx-1 h-7 w-px bg-[#ded6c7]" />;
}

const StyledParagraph = Paragraph.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      satzUuid: {
        default: null,
        parseHTML: (element) => element.getAttribute("data-satz-uuid"),
        renderHTML: (attributes) =>
          attributes.satzUuid ? { "data-satz-uuid": attributes.satzUuid } : {},
      },
      styleKey: {
        default: "body_de",
        parseHTML: (element) => element.getAttribute("data-style-key") ?? "body_de",
        renderHTML: (attributes) => ({
          "data-style-key": normalizeTranslationStyleKey(String(attributes.styleKey ?? "body_de")),
        }),
      },
    };
  },

  renderHTML({ HTMLAttributes }) {
    return ["p", mergeAttributes(HTMLAttributes), 0];
  },
});

interface TipTapParagraphState {
  text: string;
  styleKey: TranslationStyleKey;
}

function entriesToTipTapDoc(entries: TranslationPageEntry[]): JSONContent {
  return {
    type: "doc",
    content: entries.map((entry) => ({
      type: "paragraph",
      attrs: {
        satzUuid: entry.segment.satz_uuid,
        styleKey: entry.styleKey,
      },
      content: textToTipTapNodes(entry.translation),
    })),
  };
}

function textToTipTapNodes(text: string): JSONContent[] | undefined {
  if (!text) return undefined;
  const nodes: JSONContent[] = [];
  text.split("\n").forEach((line, index) => {
    if (index > 0) nodes.push({ type: "hardBreak" });
    if (line) nodes.push({ type: "text", text: line });
  });
  return nodes.length > 0 ? nodes : undefined;
}

function paragraphsFromTipTapDoc(doc: JSONContent, expectedCount: number): TipTapParagraphState[] {
  const paragraphs = (doc.content ?? []).filter((node) => node.type === "paragraph");
  const anchored = paragraphs.filter((node) => typeof node.attrs?.satzUuid === "string");
  if (anchored.length !== expectedCount) {
    throw new Error(
      `This page has ${expectedCount} internal translation anchors. Keep the existing anchored paragraphs while editing, or reset changes before saving.`,
    );
  }
  return anchored.map((node) => ({
    text: textFromTipTapNodes(node.content ?? []),
    styleKey: normalizeTranslationStyleKey(String(node.attrs?.styleKey ?? "body_de")),
  }));
}

function textFromTipTapNodes(nodes: JSONContent[]): string {
  return nodes
    .map((node) => {
      if (node.type === "text") return node.text ?? "";
      if (node.type === "hardBreak") return "\n";
      return textFromTipTapNodes(node.content ?? []);
    })
    .join("");
}

function activeParagraphStyleKey(attrs: Record<string, unknown>): TranslationStyleKey {
  return normalizeTranslationStyleKey(String(attrs.styleKey ?? "body_de"));
}

function applyStyleSequenceToAnchoredParagraphs(
  editor: Editor,
  sequence: TranslationStyleKey[],
): void {
  const paragraphs: Array<{ pos: number; attrs: Record<string, unknown> }> = [];
  editor.state.doc.descendants((node, pos) => {
    if (node.type.name !== "paragraph" || typeof node.attrs.satzUuid !== "string") return;
    paragraphs.push({ pos, attrs: { ...node.attrs } });
  });
  const currentPos = editor.state.selection.$from.before(1);
  const currentIndex = Math.max(
    0,
    paragraphs.findIndex((paragraph) => paragraph.pos === currentPos),
  );
  const tr = editor.state.tr;
  sequence.forEach((styleKey, offset) => {
    const paragraph = paragraphs[currentIndex + offset];
    if (!paragraph) return;
    tr.setNodeMarkup(paragraph.pos, undefined, {
      ...paragraph.attrs,
      styleKey,
    });
  });
  editor.view.dispatch(tr);
  editor.commands.focus();
}

function TranslationEditorStyleElement({ profile }: { profile: ProjectStyleProfile }): JSX.Element {
  const templates = effectiveTranslationStyleTemplates(profile);
  const css = TRANSLATION_STYLE_DEFINITIONS.map((definition) => {
    const tpl = templates[definition.key];
    return `
      .waraq-translation-editor p[data-style-key="${definition.key}"] {
        border-left: ${tpl.border_left ? "3px solid #d7c39c" : "0"};
        font-family: "${tpl.font_family}", Calibri, sans-serif;
        font-size: ${tpl.font_size_px}px;
        font-style: ${tpl.italic ? "italic" : "normal"};
        font-weight: ${tpl.bold ? 700 : 400};
        line-height: ${tpl.line_height};
        margin: 0 0 ${tpl.paragraph_spacing_px}px;
        margin-left: ${tpl.left_indent_px}px;
        padding-left: ${tpl.border_left ? "1rem" : "0"};
        text-align: ${tpl.alignment};
        text-indent: ${tpl.first_line_indent_px}px;
      }
    `;
  }).join("\n");
  return <style>{css}</style>;
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
      {splitAlignedText(entry.translation).map((block, index) => (
        <p
          key={`${index}-${block.text.slice(0, 18)}`}
          className={cn(
            "whitespace-pre-line",
            entry.stale && "text-amber-950",
            canOpenProtectedReference &&
              "cursor-pointer underline decoration-dotted underline-offset-4",
          )}
          style={{
            ...paragraphStyle,
            textAlign: block.alignment,
          }}
          title={entry.protectedReference?.hoverText}
          onClick={() => {
            if (canOpenProtectedReference) setReferenceOpen(true);
          }}
        >
          {block.text}
        </p>
      ))}

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
  onApplyInlineAlignment?: (alignment: InlineAlignment) => void;
}

export function TranslationStyleControls({
  projectUuid,
  profile,
  persistedProfile,
  onProfileChange,
  onApplyInlineAlignment,
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
    <section className="sticky top-0 z-20 mb-4 rounded-2xl border border-[#e7decf] bg-[#fbf6ed]/95 p-2.5 shadow-sm backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-medium text-[#1d221d]">Project style profile</p>
          <p className="text-[11px] text-muted-foreground">
            Applies to workspace pages and the next DOCX/PDF export.
          </p>
        </div>
        {onApplyInlineAlignment && (
          <div className="flex flex-wrap gap-1 rounded-xl border border-[#e7decf] bg-white/70 p-1">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="h-7 px-2 text-[11px]"
              onClick={() => onApplyInlineAlignment("left")}
              title="Apply left alignment to selected translation text"
            >
              Left
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="h-7 px-2 text-[11px]"
              onClick={() => onApplyInlineAlignment("center")}
              title="Center selected translation text, useful for page numbers"
            >
              Center
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="h-7 px-2 text-[11px]"
              onClick={() => onApplyInlineAlignment("justify")}
              title="Justify selected translation text"
            >
              Justify
            </Button>
          </div>
        )}
        <Button
          size="sm"
          className="h-8 text-xs"
          onClick={() => saveMutation.mutate(profile)}
          disabled={saveMutation.isPending || shallowEqualProfile(profile, persistedProfile)}
        >
          {saveMutation.isPending ? "Saving…" : "Save style"}
        </Button>
      </div>

      <details className="mt-2">
        <summary className="cursor-pointer select-none text-[11px] font-medium text-muted-foreground">
          Advanced layout controls
        </summary>
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
      </details>
      {!shallowEqualProfile(profile, persistedProfile) && (
        <p className="mt-2 text-[11px] text-amber-800">
          Previewing unsaved style changes. Save style before running a new export.
        </p>
      )}
      {error && <p className="mt-2 text-xs text-destructive">{error}</p>}
    </section>
  );
}

type InlineAlignment = "left" | "center" | "justify";

interface AlignedTextBlock {
  text: string;
  alignment: CSSProperties["textAlign"];
}

const ALIGNMENT_MARKER_RE = /\[\[(left|center|justify)\]\]([\s\S]*?)\[\[\/\1\]\]/g;

export function splitAlignedText(text: string): AlignedTextBlock[] {
  const blocks: AlignedTextBlock[] = [];
  let last = 0;
  for (const match of text.matchAll(ALIGNMENT_MARKER_RE)) {
    const index = match.index ?? 0;
    if (index > last) {
      blocks.push({ text: text.slice(last, index), alignment: undefined });
    }
    blocks.push({
      text: match[2] ?? "",
      alignment: markerAlignmentToCss(match[1]),
    });
    last = index + match[0].length;
  }
  if (last < text.length) {
    blocks.push({ text: text.slice(last), alignment: undefined });
  }
  return blocks.filter((block) => block.text.length > 0);
}

function markerAlignmentToCss(value: string | undefined): CSSProperties["textAlign"] {
  if (value === "center") return "center";
  if (value === "justify") return "justify";
  if (value === "left") return "left";
  return undefined;
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

const TRANSLATION_FONT_OPTIONS = [
  "Iowan Old Style",
  "Source Serif 4",
  "Libre Baskerville",
  "Georgia",
  "Times New Roman",
] as const;

const STYLE_FONT_OPTIONS = [
  "Calibri",
  "Noto Sans Arabic",
  "Noto Naskh Arabic",
  "Traditional Naskh",
  "KFGQPC Uthmanic Script HAFS",
  "Times New Roman",
  "Georgia",
  "Liberation Serif",
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
