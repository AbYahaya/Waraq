/**
 * Click-an-Arabic-word morphology popover (CAMeL Tools).
 *
 * `WordSpan` wraps a single token in a clickable span. Clicking opens a
 * Dialog that issues `POST /morphology/analyze` and renders the result.
 * If the server returns 503 (CAMeL not installed / DB missing) the
 * dialog shows the diagnostic message — no crash, no popover spam.
 *
 * `splitArabicWords` is a coarse tokenizer for the Arabic block. It
 * preserves whitespace + non-Arabic characters as plain text so RTL
 * rendering remains stable.
 */

import { useEffect, useState, type ReactNode } from "react";
import { useMutation } from "@tanstack/react-query";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ApiError, api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface AnalysisOut {
  diac: string;
  lex: string;
  root: string;
  pos: string;
  gloss: string | null;
  gen: string | null;
  num: string | null;
  per: string | null;
}

interface MorphologyResponse {
  word: string;
  analyses: AnalysisOut[];
}

const ARABIC_WORD_RE = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]+/g;

/** Split a string into [arabic-word | non-word run] alternations. */
export function splitArabicTokens(text: string): Array<{ word: boolean; text: string }> {
  if (!text) return [];
  const out: Array<{ word: boolean; text: string }> = [];
  let last = 0;
  for (const m of text.matchAll(ARABIC_WORD_RE)) {
    if (m.index !== undefined && m.index > last) {
      out.push({ word: false, text: text.slice(last, m.index) });
    }
    out.push({ word: true, text: m[0] });
    last = (m.index ?? 0) + m[0].length;
  }
  if (last < text.length) {
    out.push({ word: false, text: text.slice(last) });
  }
  return out;
}

export interface ClickableArabicProps {
  text: string | null | undefined;
  className?: string;
  emptyText?: ReactNode;
}

export function ClickableArabic({
  text,
  className,
  emptyText = <em className="text-muted-foreground">(empty)</em>,
}: ClickableArabicProps): JSX.Element {
  const [activeWord, setActiveWord] = useState<string | null>(null);
  if (!text) return <span className={className}>{emptyText}</span>;
  const tokens = splitArabicTokens(text);
  const wordStats = buildWordStats(tokens);
  return (
    <>
      <span className={className}>
        {tokens.map((t, i) =>
          t.word ? (
            <button
              key={i}
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setActiveWord(t.text);
              }}
              className="hover:bg-amber-100 rounded px-0.5 transition-colors"
            >
              {t.text}
            </button>
          ) : (
            <span key={i}>{t.text}</span>
          ),
        )}
      </span>
      <MorphologyDialog
        word={activeWord}
        wordStats={wordStats}
        onClose={() => setActiveWord(null)}
      />
    </>
  );
}

interface MorphologyDialogProps {
  word: string | null;
  wordStats: WordStats;
  onClose: () => void;
}

interface WordStats {
  totalWords: number;
  frequencies: Map<string, number>;
  topForms: Array<{ word: string; count: number }>;
}

function MorphologyDialog({
  word,
  wordStats,
  onClose,
}: MorphologyDialogProps): JSX.Element {
  const mutation = useMutation({
    mutationFn: (w: string) =>
      api.post<MorphologyResponse>("/morphology/analyze", { word: w }),
  });
  const activeFrequency = word ? wordStats.frequencies.get(normalizeArabicWord(word)) ?? 0 : 0;

  useEffect(() => {
    if (word === null) return;
    mutation.mutate(word);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [word]);

  return (
    <Dialog
      open={word !== null}
      onOpenChange={(open) => {
        if (!open) {
          mutation.reset();
          onClose();
        }
      }}
    >
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>
            <span dir="rtl" className="font-arabic text-xl">
              {word}
            </span>
          </DialogTitle>
          <DialogDescription>
            Morphological side panel with CAMeL Tools analysis and local word-form frequency.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3 rounded-2xl border bg-muted/30 p-3 text-sm sm:grid-cols-[1fr_1.2fr]">
          <div>
            <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
              Frequency in this text
            </div>
            <div className="mt-1 text-lg font-semibold">
              {activeFrequency} / {wordStats.totalWords || 0}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
              Common forms
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {wordStats.topForms.slice(0, 6).map((item) => (
                <span
                  key={item.word}
                  dir="rtl"
                  className="rounded-full border bg-background px-2.5 py-1 font-arabic text-sm"
                >
                  {item.word} <span dir="ltr" className="text-muted-foreground">×{item.count}</span>
                </span>
              ))}
              {wordStats.topForms.length === 0 && (
                <span className="text-xs text-muted-foreground">No Arabic forms detected.</span>
              )}
            </div>
          </div>
        </div>

        {mutation.isPending && (
          <p className="text-sm text-muted-foreground">Analyzing…</p>
        )}

        {mutation.isError && (
          <div className="rounded border border-amber-300 bg-amber-50 p-3 text-sm">
            <p className="font-medium text-amber-800">Morphology not configured</p>
            <p className="text-amber-700 mt-1">
              {mutation.error instanceof ApiError
                ? mutation.error.detail
                : "Failed to call /morphology/analyze."}
            </p>
          </div>
        )}

        {mutation.data && mutation.data.analyses.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No analyses returned (out-of-vocab or non-Arabic input).
          </p>
        )}

        {mutation.data && mutation.data.analyses.length > 0 && (
          <ol className="space-y-2 max-h-80 overflow-y-auto pr-1">
            {mutation.data.analyses.map((a, i) => (
              <li
                key={i}
                className={cn(
                  "rounded border p-3 text-sm",
                  i === 0 && "border-foreground/40 bg-accent/40",
                )}
              >
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <span dir="rtl" className="font-arabic text-base">
                    {a.diac || "—"}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    root <code className="text-foreground">{a.root || "—"}</code>
                  </span>
                  <span className="text-xs text-muted-foreground">
                    pos <code className="text-foreground">{a.pos || "—"}</code>
                  </span>
                </div>
                {a.gloss && <p className="mt-1">{a.gloss}</p>}
                <p className="text-xs text-muted-foreground mt-1">
                  {a.gen && `gen: ${a.gen}`}
                  {a.gen && (a.num || a.per) && " · "}
                  {a.num && `num: ${a.num}`}
                  {a.num && a.per && " · "}
                  {a.per && `per: ${a.per}`}
                </p>
              </li>
            ))}
          </ol>
        )}
      </DialogContent>
    </Dialog>
  );
}

function buildWordStats(tokens: Array<{ word: boolean; text: string }>): WordStats {
  const frequencies = new Map<string, number>();
  for (const token of tokens) {
    if (!token.word) continue;
    const normalized = normalizeArabicWord(token.text);
    if (!normalized) continue;
    frequencies.set(normalized, (frequencies.get(normalized) ?? 0) + 1);
  }
  const topForms = [...frequencies.entries()]
    .map(([word, count]) => ({ word, count }))
    .sort((a, b) => b.count - a.count || a.word.localeCompare(b.word));
  const totalWords = [...frequencies.values()].reduce((sum, count) => sum + count, 0);
  return { totalWords, frequencies, topForms };
}

function normalizeArabicWord(word: string): string {
  return word
    .replace(/[ًٌٍَُِّْـ]/g, "")
    .trim();
}
