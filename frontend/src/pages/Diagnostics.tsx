/**
 * Diagnostics — single-page test surface for verifying Phase 1–4 wiring.
 *
 * Each section calls one backend `/diagnostics/*` endpoint (or a
 * production endpoint like `/segments/{u}/hadith/verify`) and shows
 * the raw JSON response. NOT a polished UI — meant to be the
 * "everything visible in one click" verification surface before we
 * build the proper Phase-5 UI.
 *
 * Sections:
 *   1. Environment — which API keys / data are loaded
 *   2. Tanzil-Hafs Qurʾān verse lookup
 *   3. quranenc translation lookup (German + English Rwwad)
 *   4. CAMeL morphology analysis (per-word)
 *   5. Shamela search (skeleton / keyword, Bukhari ingest verified)
 *   6. OCR-PO inspector (paste a satz_uuid, see Stage-2/3/4/5 payload)
 *   7. Hadith verification (POST /segments/{u}/hadith/verify)
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api, ApiError, apiPath } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface EnvDiag {
  openai_key_present: boolean;
  google_ai_key_present: boolean;
  google_application_credentials_set: boolean;
  sunnah_com_api_key_present: boolean;
  morphology_db_available: boolean;
  kraken_available: boolean;
}

function Pill({ ok, label }: { ok: boolean; label: string }): JSX.Element {
  return (
    <span
      className={`inline-block rounded-full px-3 py-0.5 text-xs font-medium mr-2 mb-1 ${
        ok ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
      }`}
    >
      {ok ? "✓ " : "✗ "}
      {label}
    </span>
  );
}

function JsonBlock({ data }: { data: unknown }): JSX.Element {
  return (
    <pre
      className="bg-muted text-xs overflow-auto rounded p-3 mt-2 max-h-96"
      style={{ direction: "ltr" }}
    >
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

function ErrorBlock({ error }: { error: unknown }): JSX.Element {
  if (error instanceof ApiError) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-800 text-sm rounded p-3 mt-2">
        <div className="font-medium">HTTP {error.status}</div>
        <div className="mt-1">{String(error.detail)}</div>
      </div>
    );
  }
  return (
    <div className="bg-red-50 border border-red-200 text-red-800 text-sm rounded p-3 mt-2">
      {error instanceof Error ? error.message : String(error)}
    </div>
  );
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}): JSX.Element {
  return (
    <section className="border rounded-lg p-4 mb-4 bg-card">
      <h2 className="text-lg font-semibold mb-1">{title}</h2>
      {description && (
        <p className="text-sm text-muted-foreground mb-3">{description}</p>
      )}
      {children}
    </section>
  );
}

// 1. Environment ---------------------------------------------------------

function EnvironmentSection(): JSX.Element {
  const { data, error, isFetching } = useQuery<EnvDiag>({
    queryKey: ["diagnostics", "environment"],
    queryFn: () => api.get<EnvDiag>("/diagnostics/environment"),
  });
  return (
    <Section
      title="1. Environment status"
      description="Which API keys / data installs are live on this host. Drives every downstream section."
    >
      {isFetching && <div className="text-sm text-muted-foreground">Loading…</div>}
      {error ? <ErrorBlock error={error} /> : null}
      {data && (
        <div>
          <Pill ok={data.openai_key_present} label="OPENAI_API_KEY" />
          <Pill ok={data.google_ai_key_present} label="GOOGLE_AI_API_KEY" />
          <Pill
            ok={data.google_application_credentials_set}
            label="GOOGLE_APPLICATION_CREDENTIALS (Cloud Vision)"
          />
          <Pill
            ok={data.sunnah_com_api_key_present}
            label="SUNNAH_COM_API_KEY (P-1 hadith)"
          />
          <Pill
            ok={data.morphology_db_available}
            label="CAMeL morphology DB"
          />
          <Pill
            ok={data.kraken_available}
            label="kraken (manuscript OCR)"
          />
        </div>
      )}
    </Section>
  );
}

// 2. Tanzil-Hafs Quran verse --------------------------------------------

interface QuranVerseResp {
  sura: number;
  aya: number;
  text_arabic: string | null;
  source_name: string | null;
  source_version: string | null;
  found: boolean;
}

function QuranVerseSection(): JSX.Element {
  const [sura, setSura] = useState("1");
  const [aya, setAya] = useState("1");
  const [data, setData] = useState<QuranVerseResp | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const onLookup = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const resp = await api.get<QuranVerseResp>(
        `/diagnostics/quran/verse?sura=${sura}&aya=${aya}`,
      );
      setData(resp);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }, [sura, aya]);

  return (
    <Section
      title="2. Tanzil-Hafs Qurʾān verse lookup (operator step 1)"
      description="Verifies the AR-Referenzbestand ingest. 6 236 verses live under tanzil-hafs-uthmani."
    >
      <div className="flex items-end gap-2">
        <div>
          <Label htmlFor="sura">Sura</Label>
          <Input
            id="sura"
            type="number"
            min="1"
            max="114"
            value={sura}
            onChange={(e) => setSura(e.target.value)}
            className="w-24"
          />
        </div>
        <div>
          <Label htmlFor="aya">Āya</Label>
          <Input
            id="aya"
            type="number"
            min="1"
            value={aya}
            onChange={(e) => setAya(e.target.value)}
            className="w-24"
          />
        </div>
        <Button onClick={onLookup} disabled={busy}>
          {busy ? "Looking up…" : "Lookup"}
        </Button>
      </div>
      {error ? <ErrorBlock error={error} /> : null}
      {data && data.found && (
        <div className="mt-3 text-right" dir="rtl" lang="ar">
          <div className="text-2xl leading-relaxed">{data.text_arabic}</div>
          <div className="text-xs text-muted-foreground mt-1" dir="ltr">
            {data.source_name}@{data.source_version}
          </div>
        </div>
      )}
      {data && !data.found && (
        <div className="text-sm text-amber-700 mt-2">
          No verse at ({data.sura}:{data.aya}) — check ingest.
        </div>
      )}
    </Section>
  );
}

// 3. quranenc translation -----------------------------------------------

interface QuranTransResp {
  sura: number;
  aya: number;
  translation_key: string;
  translation: string | null;
  source_version: string | null;
  found: boolean;
}

function QuranTranslationSection(): JSX.Element {
  const [sura, setSura] = useState("1");
  const [aya, setAya] = useState("1");
  const [key, setKey] = useState("german_rwwad");
  const [data, setData] = useState<QuranTransResp | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const onLookup = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const resp = await api.get<QuranTransResp>(
        `/diagnostics/quran/translation?sura=${sura}&aya=${aya}&key=${key}`,
      );
      setData(resp);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }, [sura, aya, key]);

  return (
    <Section
      title="3. quranenc translation lookup (operator step 2)"
      description="Local fallback (no live API call). 12 472 verses cached: German + English Rwwad."
    >
      <div className="flex items-end gap-2 flex-wrap">
        <div>
          <Label htmlFor="trans-sura">Sura</Label>
          <Input
            id="trans-sura"
            type="number"
            min="1"
            max="114"
            value={sura}
            onChange={(e) => setSura(e.target.value)}
            className="w-24"
          />
        </div>
        <div>
          <Label htmlFor="trans-aya">Āya</Label>
          <Input
            id="trans-aya"
            type="number"
            min="1"
            value={aya}
            onChange={(e) => setAya(e.target.value)}
            className="w-24"
          />
        </div>
        <div>
          <Label htmlFor="trans-key">Key</Label>
          <select
            id="trans-key"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            className="border rounded h-10 px-2"
          >
            <option value="german_rwwad">german_rwwad</option>
            <option value="english_rwwad">english_rwwad</option>
          </select>
        </div>
        <Button onClick={onLookup} disabled={busy}>
          {busy ? "Looking up…" : "Lookup"}
        </Button>
      </div>
      {error ? <ErrorBlock error={error} /> : null}
      {data && data.found && (
        <div className="mt-3">
          <div className="text-base">{data.translation}</div>
          <div className="text-xs text-muted-foreground mt-1">
            {data.translation_key}@{data.source_version}
          </div>
        </div>
      )}
      {data && !data.found && (
        <div className="text-sm text-amber-700 mt-2">
          No translation cached — sync the language first via{" "}
          <code>scripts/sync_quranenc.py</code>.
        </div>
      )}
    </Section>
  );
}

// 4. CAMeL morphology ---------------------------------------------------

interface MorphAnalysis {
  diac: string;
  lex: string;
  root: string;
  pos: string;
  gloss: string | null;
  gen: string | null;
  num: string | null;
  per: string | null;
}

interface MorphResp {
  word: string;
  available: boolean;
  analyses: MorphAnalysis[];
  error: string | null;
}

function MorphologySection(): JSX.Element {
  const [word, setWord] = useState("بِسْمِ");
  const [data, setData] = useState<MorphResp | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const onAnalyze = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const resp = await api.get<MorphResp>(
        `/diagnostics/morphology/analyze?word=${encodeURIComponent(word)}`,
      );
      setData(resp);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }, [word]);

  return (
    <Section
      title="4. CAMeL Tools morphology analysis (operator step 3)"
      description="MSA morphology DB — drives the V-1/V-2 morphology refiner + CAMeL homoglyph corrector."
    >
      <div className="flex items-end gap-2">
        <div>
          <Label htmlFor="morph-word">Arabic word</Label>
          <Input
            id="morph-word"
            value={word}
            onChange={(e) => setWord(e.target.value)}
            className="w-48"
            dir="rtl"
            lang="ar"
          />
        </div>
        <Button onClick={onAnalyze} disabled={busy}>
          {busy ? "Analyzing…" : "Analyze"}
        </Button>
      </div>
      {error ? <ErrorBlock error={error} /> : null}
      {data && (
        <div className="mt-3">
          {!data.available && (
            <div className="text-sm text-amber-700">
              {data.error || "Morphology DB unavailable."}
            </div>
          )}
          {data.available && data.analyses.length === 0 && (
            <div className="text-sm text-amber-700">No analyses found.</div>
          )}
          {data.available && data.analyses.length > 0 && (
            <div className="text-sm">
              <div className="text-muted-foreground mb-1">
                {data.analyses.length} analyses:
              </div>
              <div className="space-y-1 max-h-64 overflow-auto">
                {data.analyses.slice(0, 8).map((a, i) => (
                  <div key={i} className="border rounded px-2 py-1 text-xs">
                    <span dir="rtl" lang="ar">
                      {a.diac}
                    </span>{" "}
                    | lex: {a.lex} | root: {a.root} | pos: {a.pos}
                    {a.gloss && ` | ${a.gloss}`}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Section>
  );
}

// 5. Shamela search -----------------------------------------------------

interface ShamelaHit {
  text_slug: string;
  title: string;
  is_kutub_as_sitta: boolean;
  text_type: string;
  section_index: number;
  section_path: string;
  matn_excerpt: string;
}

interface ShamelaResp {
  mode: "skeleton" | "keyword";
  query: string;
  only_kutub_as_sitta: boolean;
  hit_count: number;
  hits: ShamelaHit[];
}

function ShamelaSection(): JSX.Element {
  const [query, setQuery] = useState("إنما الأعمال بالنيات");
  const [mode, setMode] = useState<"skeleton" | "keyword">("skeleton");
  const [kutubOnly, setKutubOnly] = useState(true);
  const [data, setData] = useState<ShamelaResp | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const onSearch = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const resp = await api.get<ShamelaResp>(
        `/diagnostics/shamela/search?query=${encodeURIComponent(
          query,
        )}&mode=${mode}&only_kutub_as_sitta=${kutubOnly}`,
      );
      setData(resp);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }, [query, mode, kutubOnly]);

  return (
    <Section
      title="5. Shamela / OpenITI search"
      description="Sahih al-Bukhari (8 007 sections) is live. Skeleton mode = OCR-stage Mode A; Keyword = Mode B."
    >
      <div className="space-y-2">
        <div>
          <Label htmlFor="sham-query">Query</Label>
          <Input
            id="sham-query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            dir="rtl"
            lang="ar"
          />
        </div>
        <div className="flex items-center gap-3">
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as "skeleton" | "keyword")}
            className="border rounded h-9 px-2 text-sm"
          >
            <option value="skeleton">Mode A — skeleton</option>
            <option value="keyword">Mode B — keyword</option>
          </select>
          <label className="flex items-center text-sm">
            <input
              type="checkbox"
              className="mr-2"
              checked={kutubOnly}
              onChange={(e) => setKutubOnly(e.target.checked)}
            />
            Kutub-as-Sitta only
          </label>
          <Button onClick={onSearch} disabled={busy}>
            {busy ? "Searching…" : "Search"}
          </Button>
        </div>
      </div>
      {error ? <ErrorBlock error={error} /> : null}
      {data && (
        <div className="mt-3 text-sm">
          <div className="text-muted-foreground">
            {data.hit_count} hits ({data.mode})
          </div>
          <div className="space-y-1 mt-2 max-h-72 overflow-auto">
            {data.hits.slice(0, 10).map((h, i) => (
              <div key={i} className="border rounded px-2 py-1 text-xs">
                <div className="font-medium">
                  {h.title}{" "}
                  {h.is_kutub_as_sitta && (
                    <span className="text-green-700">[Kutub]</span>
                  )}
                </div>
                <div className="text-muted-foreground">
                  §{h.section_index} · {h.section_path}
                </div>
                <div dir="rtl" lang="ar" className="mt-1">
                  {h.matn_excerpt}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </Section>
  );
}

// 6. OCR-PO inspector ---------------------------------------------------

interface OcrPoResp {
  satz_uuid: string;
  po_uuid: string | null;
  payload: Record<string, unknown> | null;
}

function OcrPoSection(): JSX.Element {
  const [satzUuid, setSatzUuid] = useState("");
  const [data, setData] = useState<OcrPoResp | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const onLookup = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const resp = await api.get<OcrPoResp>(
        `/diagnostics/segments/${satzUuid}/ocr-po`,
      );
      setData(resp);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }, [satzUuid]);

  return (
    <Section
      title="6. OCR-PO inspector — Stage 2/3/4/5 in one place"
      description="Paste a satz_uuid (find one via Workspace → page → segment URL). Payload shows multi-engine consensus, Stage-3 three-track aggregator output, quality + homoglyph + confidence."
    >
      <div className="flex gap-2 items-end">
        <div className="flex-1">
          <Label htmlFor="po-satz">Segment UUID</Label>
          <Input
            id="po-satz"
            value={satzUuid}
            onChange={(e) => setSatzUuid(e.target.value)}
            placeholder="paste a satz_uuid"
          />
        </div>
        <Button onClick={onLookup} disabled={busy || !satzUuid.trim()}>
          {busy ? "Loading…" : "Inspect"}
        </Button>
      </div>
      {error ? <ErrorBlock error={error} /> : null}
      {data && data.payload === null && (
        <div className="mt-2 text-sm text-amber-700">
          No OCR-PO yet for this segment — run OCR first.
        </div>
      )}
      {data && data.payload && (
        <div className="mt-3">
          <div className="text-xs text-muted-foreground">
            po_uuid: {data.po_uuid}
          </div>
          <JsonBlock data={data.payload} />
        </div>
      )}
    </Section>
  );
}

// 7. Hadith verification ------------------------------------------------

interface HadithVerifyResp {
  satz_uuid: string;
  extended_set_triggered: boolean;
  extended_trigger_reason: string | null;
  extended_sources_invoked: string[];
  mandatory_count: number;
  extended_count: number;
  sources_skipped: string[];
  citations: { source_name: string; quellen_rolle: string; matn_excerpt: string }[];
  run: {
    aggregate_uuid: string;
    single_source_uuids: string[];
    superseded_aggregate_uuid: string | null;
  } | null;
}

function HadithVerifySection(): JSX.Element {
  const [satzUuid, setSatzUuid] = useState("");
  const [manualExtended, setManualExtended] = useState(false);
  const [data, setData] = useState<HadithVerifyResp | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const onVerify = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const resp = await api.post<HadithVerifyResp>(
        `/segments/${satzUuid}/hadith/verify`,
        { manually_trigger_extended: manualExtended },
      );
      setData(resp);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }, [satzUuid, manualExtended]);

  return (
    <Section
      title="7. Hadith verification (P-1 + P-2 + P-3 → consensus + Level-2/3 persistence)"
      description="Paste a segment UUID containing Arabic Hadith text. The endpoint runs Shamela skeleton lookup against Bukhari + tries sunnah.com (if SUNNAH_COM_API_KEY is set) + dorar.net API."
    >
      <div className="space-y-2">
        <div>
          <Label htmlFor="hadith-satz">Segment UUID</Label>
          <Input
            id="hadith-satz"
            value={satzUuid}
            onChange={(e) => setSatzUuid(e.target.value)}
            placeholder="paste a satz_uuid (with Arabic Hadith text)"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm flex items-center">
            <input
              type="checkbox"
              checked={manualExtended}
              onChange={(e) => setManualExtended(e.target.checked)}
              className="mr-2"
            />
            Manually trigger extended set (E-1..E-5)
          </label>
          <Button
            onClick={onVerify}
            disabled={busy || !satzUuid.trim()}
            className="ml-auto"
          >
            {busy ? "Verifying…" : "Verify"}
          </Button>
        </div>
      </div>
      {error ? <ErrorBlock error={error} /> : null}
      {data && (
        <div className="mt-3 text-sm">
          <div>
            <span className="font-medium">Mandatory hits:</span>{" "}
            {data.mandatory_count} ·{" "}
            <span className="font-medium">Extended hits:</span> {data.extended_count}
          </div>
          {data.sources_skipped.length > 0 && (
            <div className="text-xs text-amber-700 mt-1">
              Skipped: {data.sources_skipped.join(", ")}
            </div>
          )}
          {data.run && (
            <div className="mt-1 text-xs text-muted-foreground">
              Persisted aggregate {data.run.aggregate_uuid} ·{" "}
              {data.run.single_source_uuids.length} single-source rows
            </div>
          )}
          {data.citations.length > 0 && (
            <div className="space-y-1 mt-2 max-h-72 overflow-auto">
              {data.citations.map((c, i) => (
                <div key={i} className="border rounded px-2 py-1 text-xs">
                  <span className="font-medium">{c.source_name}</span>{" "}
                  <span className="text-muted-foreground">
                    [{c.quellen_rolle}]
                  </span>
                  <div dir="rtl" lang="ar" className="mt-1">
                    {c.matn_excerpt}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Section>
  );
}

// 8. kraken manuscript OCR ----------------------------------------------

interface KrakenRecognizeResp {
  available: boolean;
  text: string;
  text_chars: number;
  confidence: number | null;
  model_path: string;
  error: string | null;
}

function KrakenSection(): JSX.Element {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [data, setData] = useState<KrakenRecognizeResp | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const onRecognize = useCallback(async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setData(null);
    try {
      const fd = new FormData();
      fd.append("image", file, file.name);
      const token = useAuthStore.getState().token;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const resp = await fetch(apiPath("/diagnostics/kraken/recognize"), {
        method: "POST",
        headers,
        body: fd,
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new ApiError(resp.status, text || resp.statusText, text);
      }
      setData((await resp.json()) as KrakenRecognizeResp);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }, [file]);

  return (
    <Section
      title="8. kraken manuscript OCR (Phase 4 — §3.3 third engine)"
      description="Project-flag-gated in the §3.4 pipeline; here we run kraken directly on an uploaded image. Use a handwritten/calligraphic Arabic scan — Gemini + Cloud Vision are stronger on printed editions."
    >
      <div className="flex items-end gap-2 flex-wrap">
        <div>
          <Label htmlFor="kraken-file">Image (PNG / JPEG / TIFF)</Label>
          <input
            ref={fileRef}
            id="kraken-file"
            type="file"
            accept="image/png,image/jpeg,image/tiff,image/webp"
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null;
              setFile(f);
              setData(null);
              setError(null);
            }}
            className="text-sm file:mr-3 file:rounded file:border file:bg-background file:px-3 file:py-1.5 file:text-sm hover:file:bg-accent block mt-1"
          />
        </div>
        <Button onClick={onRecognize} disabled={busy || !file}>
          {busy ? "Recognising…" : "Recognise"}
        </Button>
      </div>
      {file && (
        <p className="text-xs text-muted-foreground mt-2">
          {file.name} — {(file.size / 1024).toFixed(1)} KB
        </p>
      )}
      {error ? <ErrorBlock error={error} /> : null}
      {data && (
        <div className="mt-3 text-sm">
          <div className="text-xs text-muted-foreground">
            model: <code>{data.model_path}</code> · available:{" "}
            <span className={data.available ? "text-green-700" : "text-red-700"}>
              {data.available ? "yes" : "no"}
            </span>
            {data.confidence !== null && (
              <>
                {" "}· confidence: {data.confidence.toFixed(3)}
              </>
            )}
          </div>
          {data.error && (
            <div className="bg-amber-50 border border-amber-200 text-amber-900 text-xs rounded p-3 mt-2 whitespace-pre-wrap">
              {data.error}
            </div>
          )}
          {data.text && (
            <div className="mt-3">
              <div className="text-xs text-muted-foreground mb-1">
                {data.text_chars} chars
              </div>
              <div
                dir="rtl"
                lang="ar"
                className="text-base leading-relaxed border rounded p-3 bg-card whitespace-pre-wrap max-h-80 overflow-auto"
              >
                {data.text}
              </div>
            </div>
          )}
        </div>
      )}
    </Section>
  );
}

// Page ------------------------------------------------------------------

export function DiagnosticsPage(): JSX.Element {
  // Fetch environment once on mount so the Pills are populated immediately.
  useEffect(() => {
    /* triggers EnvironmentSection's useQuery */
  }, []);

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-semibold mb-2">Phase 1–4 Diagnostics</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Lean test surface for confirming every Phase 1–4 backend feature is
        wired and reachable. Each section calls one HTTP endpoint and shows
        the raw response. NOT production UI.
      </p>
      <EnvironmentSection />
      <QuranVerseSection />
      <QuranTranslationSection />
      <MorphologySection />
      <ShamelaSection />
      <OcrPoSection />
      <HadithVerifySection />
      <KrakenSection />
    </div>
  );
}
