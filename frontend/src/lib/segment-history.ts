import type { SegmentHistoryDto } from "@/lib/queries";

export interface HistoryRevisionSummary {
  text: string;
  createdAt: string;
}

export interface ProtectedReferenceSummary {
  kind: "quran" | "hadith";
  badgeLabel: string;
  title: string;
  subtitle: string | null;
  sources: string[];
  hoverText: string;
  inlineOnly: boolean;
}

export function getLatestSourceRevision(
  history: SegmentHistoryDto | undefined,
): HistoryRevisionSummary | null {
  if (!history) return null;
  const revision = [...history.revisions]
    .filter((r) => r.change_source !== "re_translate")
    .at(-1);
  if (!revision) return null;
  return { text: revision.after_text, createdAt: revision.created_at };
}

export function getLatestTranslationRevision(
  history: SegmentHistoryDto | undefined,
): HistoryRevisionSummary | null {
  if (!history) return null;
  const revision = history.revisions
    .filter((r) => r.change_source === "re_translate")
    .at(-1);
  if (!revision) return null;
  return { text: revision.after_text, createdAt: revision.created_at };
}

export function isTranslationStale(
  history: SegmentHistoryDto | undefined,
): boolean {
  const source = getLatestSourceRevision(history);
  const target = getLatestTranslationRevision(history);
  if (!source || !target) return false;
  return source.createdAt > target.createdAt;
}

export function getLatestProtectedReference(
  history: SegmentHistoryDto | undefined,
): ProtectedReferenceSummary | null {
  if (!history) return null;
  const raw = getLatestProtectedReferencePayload(history);
  if (raw === null) return getQuranProtectedReferenceFallback(history);
  const kind = raw?.kind;
  if (kind !== "quran" && kind !== "hadith") return null;

  const title =
    asNonEmptyString(raw.title) ??
    (kind === "quran" ? "Qur'an reference" : "Verified hadith sources");
  const subtitle = asNonEmptyString(raw.subtitle);
  const sources = Array.isArray(raw.sources)
    ? raw.sources.filter((entry): entry is string => typeof entry === "string" && entry.trim().length > 0)
    : [];
  const inlineOnly = kind === "quran" && Array.isArray(raw.inline_passages);
  const hoverParts = [title, subtitle, ...sources.slice(0, 3)].filter(
    (entry): entry is string => typeof entry === "string" && entry.trim().length > 0,
  );

  return {
    kind,
    badgeLabel: kind === "quran" ? "Qur'an source" : "Verified sources",
    title,
    subtitle,
    sources,
    hoverText: hoverParts.join(" | "),
    inlineOnly,
  };
}

function getLatestProtectedReferencePayload(
  history: SegmentHistoryDto,
): Record<string, unknown> | null {
  const provenance = [...history.provenance_objects]
    .filter((entry) => asRecord(entry)?.po_type === "translation")
    .reverse()
    .find((entry) => {
      const payload = asRecord(entry)?.payload;
      return asRecord(payload)?.protected_reference !== undefined;
    });
  return asRecord(asRecord(asRecord(provenance)?.payload)?.protected_reference);
}

function getQuranProtectedReferenceFallback(
  history: SegmentHistoryDto,
): ProtectedReferenceSummary | null {
  const passage = asRecord(history.quran_passage);
  if (passage === null) return null;

  const suraIndex = asNumericString(passage.sura_index);
  const ayaStart = asNumericString(passage.aya_index_start);
  const ayaEnd = asNumericString(passage.aya_index_end);
  const translationKey = asNonEmptyString(passage.translation_key) ?? "german_rwwad";
  const translationVersion = asNonEmptyString(passage.translation_source_version);
  const arabicSourceName = asNonEmptyString(passage.ar_source_name) ?? "arabic reference";
  const arabicSourceVersion = asNonEmptyString(passage.ar_source_version);
  const state = asNonEmptyString(passage.state);

  const subtitle = suraIndex && ayaStart
    ? ayaEnd && ayaEnd !== ayaStart
      ? `Surah ${suraIndex}, ayahs ${ayaStart}-${ayaEnd}`
      : `Surah ${suraIndex}, ayah ${ayaStart}`
    : state;

  const sources = [
    formatSourceLine("Arabic source", arabicSourceName, arabicSourceVersion),
    formatSourceLine("Translation source", translationKey, translationVersion),
  ];

  const hoverParts = ["Qur'an reference", subtitle, ...sources].filter(
    (entry): entry is string => typeof entry === "string" && entry.trim().length > 0,
  );

  return {
    kind: "quran",
    badgeLabel: "Qur'an source",
    title: "Qur'an reference",
    subtitle,
    sources,
    hoverText: hoverParts.join(" | "),
    inlineOnly: false,
  };
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (typeof value !== "object" || value === null) return null;
  return value as Record<string, unknown>;
}

function asNonEmptyString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function asNumericString(value: unknown): string | null {
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return asNonEmptyString(value);
}

function formatSourceLine(label: string, sourceName: string, sourceVersion: string | null): string {
  if (sourceVersion) return `${label}: ${sourceName} (${sourceVersion})`;
  return `${label}: ${sourceName}`;
}
