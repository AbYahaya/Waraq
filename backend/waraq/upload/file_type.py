"""§2.1 Phase 5 K-1 + K-2 + K-3 + K-4 — Upload file-type detection.

The upload pipeline's chunk-receive logic is format-agnostic — it just
writes bytes to disk. What IS format-specific is four things:

  1. **Page-count materialization at finalize time** — a PDF has N
     pages decided by `pypdf`; a single-image upload is one page; a
     multi-page TIFF is N pages decided by `PIL.Image.n_frames`; a
     direct-text document (DOCX/ODT/TXT/XML/HTML/EPUB/MOBI/AZW/AZW3)
     is one page (the paragraphs become Segments within a single
     Block); a DjVu has N pages decided by `djvused`; an archive
     produces 1+ Pages decided by recursing per-entry through the
     same format-specific finalize logic.
  2. **OCR-time rasterization** — PDFs go through `pdftoppm` to get a
     PNG per page; DjVu goes through `ddjvu`; images skip that step
     entirely (they ARE the page); direct-text formats raise at OCR
     time because text was already extracted at finalize.
  3. **Direct-text extraction at finalize time** — DOCX/ODT/TXT/XML/
     HTML (K-2) plus EPUB/MOBI/AZW/AZW3 (K-3) have their text pulled
     out and written to Segments directly, bypassing the OCR pipeline.
     `is_direct_text_format()` is the branch predicate.
  4. **Archive recursion at finalize time** (K-4) — ZIP/RAR/CBZ/CBR
     are extracted, sorted by filename per canon §2.1, and each
     supported inner entry is processed via the existing per-format
     finalize logic. Nested archives are NOT recursed (canon stops at
     one level: "recurse into supported formats"; archive-of-archive
     is silent).

This module is the small declarative layer that all call sites read.
Add a new format here, branch the call sites, ship a test — that's
the canonical sub-batch-K-shape extension pattern.

K-1 (shipped): JPG / JPEG / PNG / TIFF / TIF / HEIC / WEBP image group.
K-2 (shipped): DOCX / ODT / TXT / XML / HTML direct-text document group.
K-3 (shipped): EPUB / MOBI / AZW / AZW3 e-book direct-text; DjVu
               "special path" treated as a raster format (like PDF).
K-4 (shipped): ZIP / RAR / CBZ / CBR archive group; extract +
               filename-sort + recurse into supported inner entries.
PDF stays the canonical default.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

# ---------------------------------------------------------------------
# Format identifiers — wire-stable. Persisted on SCAN-PO `format` field.
# ---------------------------------------------------------------------


class UploadFormat(StrEnum):
    """Canonical upload format. The string value is what lands on
    SCAN-PO payload's `format` field. Renaming is wire-shaped.

    Image group (K-1, single-page unless noted):
      - JPEG  — `.jpg`, `.jpeg`
      - PNG   — `.png`
      - TIFF  — `.tif`, `.tiff` (may be multi-page; per-frame counted)
      - HEIC  — `.heic`, `.heif` (Apple's High Efficiency format)
      - WEBP  — `.webp`

    Document group (canonical PDF + K-2 direct-text formats):
      - PDF   — `.pdf` (canonical default, multi-page, OCR pipeline)
      - DOCX  — `.docx` (python-docx paragraph extraction)
      - ODT   — `.odt` (odfpy paragraph extraction)
      - TXT   — `.txt` (split by `\\n\\n`)
      - XML   — `.xml` (stripped + paragraph-split)
      - HTML  — `.html`, `.htm` (stripped + paragraph-split)
    """

    PDF = "pdf"
    JPEG = "jpeg"
    PNG = "png"
    TIFF = "tiff"
    HEIC = "heic"
    WEBP = "webp"
    DOCX = "docx"
    ODT = "odt"
    TXT = "txt"
    XML = "xml"
    HTML = "html"
    EPUB = "epub"
    MOBI = "mobi"
    AZW = "azw"
    AZW3 = "azw3"
    DJVU = "djvu"
    ZIP = "zip"
    RAR = "rar"
    CBZ = "cbz"
    CBR = "cbr"


# Suffix → format. Lowercase, leading dot stripped at lookup time.
_SUFFIX_MAP: dict[str, UploadFormat] = {
    "pdf": UploadFormat.PDF,
    "jpg": UploadFormat.JPEG,
    "jpeg": UploadFormat.JPEG,
    "png": UploadFormat.PNG,
    "tif": UploadFormat.TIFF,
    "tiff": UploadFormat.TIFF,
    "heic": UploadFormat.HEIC,
    "heif": UploadFormat.HEIC,
    "webp": UploadFormat.WEBP,
    "docx": UploadFormat.DOCX,
    "odt": UploadFormat.ODT,
    "txt": UploadFormat.TXT,
    "xml": UploadFormat.XML,
    "html": UploadFormat.HTML,
    "htm": UploadFormat.HTML,
    "epub": UploadFormat.EPUB,
    "mobi": UploadFormat.MOBI,
    "azw": UploadFormat.AZW,
    "azw3": UploadFormat.AZW3,
    "djvu": UploadFormat.DJVU,
    "djv": UploadFormat.DJVU,
    "zip": UploadFormat.ZIP,
    "rar": UploadFormat.RAR,
    "cbz": UploadFormat.CBZ,
    "cbr": UploadFormat.CBR,
}


# Magic-byte signatures — used as a second-line check so a renamed file
# (e.g. `scan.pdf` that's actually a JPEG) doesn't sneak through. The
# match is the FIRST format whose magic prefix matches; ordering matters
# only for ambiguous prefixes (none in this set).
#
# K-2 doc-format note: DOCX + ODT both share the ZIP `PK\\x03\\x04`
# prefix because they're ZIP-based containers. We don't try to
# disambiguate them by magic (would require unzipping and inspecting
# the inner `mimetype` / `[Content_Types].xml`); suffix is authoritative
# for both. TXT has no usable magic. XML / HTML have weak signatures
# (`<?xml`, `<!DOCTYPE`, `<html`) — surfaced in `_detect_text_magic`
# but suffix wins when both are present, opposite of K-1's binary-format
# rule.
_MAGIC_SIGNATURES: tuple[tuple[bytes, UploadFormat], ...] = (
    (b"%PDF-", UploadFormat.PDF),
    (b"\xff\xd8\xff", UploadFormat.JPEG),
    (b"\x89PNG\r\n\x1a\n", UploadFormat.PNG),
    (b"II*\x00", UploadFormat.TIFF),  # little-endian TIFF
    (b"MM\x00*", UploadFormat.TIFF),  # big-endian TIFF
    # HEIC has the "ftyp" box at offset 4, with brand bytes 8..12.
    # The brand bytes are e.g. "heic", "heix", "mif1", "msf1" — we
    # match the box header and check the brand at offset 8.
    # The pragmatic check is `bytes[4:8] == b"ftyp"` AND brand ∈ HEIC set,
    # done in `_match_heic_magic` below.
    (b"RIFF", UploadFormat.WEBP),  # WEBP starts with RIFF<4-byte size>WEBP
)

# Direct-text formats — bypass OCR; text extracted at finalize time.
# K-2 set: DOCX/ODT (parsed via python-docx / odfpy) + TXT/XML/HTML
# (stdlib-only). K-3 extension: EPUB (ebooklib), MOBI/AZW/AZW3 (mobi).
# DjVu is NOT direct-text — it's a paged raster format like PDF and
# goes through the OCR pipeline via `_rasterize_page`'s `ddjvu` branch.
_DIRECT_TEXT_FORMATS: frozenset[UploadFormat] = frozenset(
    {
        UploadFormat.DOCX,
        UploadFormat.ODT,
        UploadFormat.TXT,
        UploadFormat.XML,
        UploadFormat.HTML,
        UploadFormat.EPUB,
        UploadFormat.MOBI,
        UploadFormat.AZW,
        UploadFormat.AZW3,
    }
)

# Archive formats — extracted at finalize time; each inner entry that
# resolves to a supported (non-archive) format is processed via the
# existing per-format finalize path. ZIP/CBZ via stdlib zipfile;
# RAR/CBR via rarfile + `unrar` system binary.
_ARCHIVE_FORMATS: frozenset[UploadFormat] = frozenset(
    {
        UploadFormat.ZIP,
        UploadFormat.RAR,
        UploadFormat.CBZ,
        UploadFormat.CBR,
    }
)

_HEIC_BRANDS: frozenset[bytes] = frozenset(
    {b"heic", b"heix", b"heim", b"heis", b"mif1", b"msf1", b"hevc", b"hevx"}
)


class UnsupportedFormat(ValueError):
    """Raised when a file's suffix is not in `_SUFFIX_MAP` AND its
    magic bytes don't match any known signature. The upload finalize
    surface converts this to HTTP 415."""


def detect_format(*, filename: str, head_bytes: bytes) -> UploadFormat:
    """Resolve the upload's format from its filename + first few bytes.

    Strategy:
      1. Match by file suffix (cheap, usually right).
      2. **Suffix-authoritative for the K-2 direct-text group** — DOCX
         and ODT share the ZIP-magic prefix `PK\\x03\\x04` (they're both
         ZIP containers); TXT has no magic; XML/HTML magic is weak.
         When the suffix maps to one of `_DIRECT_TEXT_FORMATS` we trust
         the suffix and don't even check magic.
      3. For the K-1 binary group (PDF + images), verify against magic
         bytes. When suffix and magic agree → use it. When they
         disagree → magic wins (defends against misnamed files like
         `book.pdf` whose body is a JPEG). When magic resolves but
         suffix doesn't → use magic (defensive). When suffix resolves
         but magic doesn't (short/empty file) → use suffix.

    Raises `UnsupportedFormat` when neither suffix nor magic resolves.

    `head_bytes` should be at least 16 bytes for HEIC's box-header check;
    the upload service reads the first 64 bytes for finalize-time
    detection so this is always satisfied in production.
    """
    suffix = Path(filename).suffix.lstrip(".").lower()
    by_suffix = _SUFFIX_MAP.get(suffix)

    # K-2 direct-text suffix-authority — trust the suffix for these,
    # no magic check needed (and would mis-classify ZIP-shaped DOCX/ODT
    # if we tried, since both share `PK\\x03\\x04`).
    if by_suffix is not None and by_suffix in _DIRECT_TEXT_FORMATS:
        return by_suffix

    by_magic = _detect_by_magic(head_bytes)

    if by_suffix is not None and by_magic is not None:
        # Both resolved → magic wins on disagreement (K-1 rule).
        return by_magic
    if by_magic is not None:
        return by_magic
    if by_suffix is not None:
        return by_suffix
    raise UnsupportedFormat(
        f"Unsupported upload format: suffix={suffix!r}, "
        f"head_bytes_prefix={head_bytes[:16]!r}"
    )


def _detect_by_magic(head_bytes: bytes) -> UploadFormat | None:
    """Try every magic signature in `_MAGIC_SIGNATURES`. HEIC needs the
    special box-header + brand check."""
    if _match_heic_magic(head_bytes):
        return UploadFormat.HEIC
    if head_bytes.startswith(b"RIFF") and head_bytes[8:12] == b"WEBP":
        # Disambiguate RIFF: only `RIFF<size>WEBP` is WEBP; the bare
        # `RIFF` prefix also covers WAV/AVI which we don't accept.
        return UploadFormat.WEBP
    for prefix, fmt in _MAGIC_SIGNATURES:
        if fmt == UploadFormat.WEBP:
            continue  # handled above with the WEBP-brand check
        if head_bytes.startswith(prefix):
            return fmt
    return None


def _match_heic_magic(head_bytes: bytes) -> bool:
    """HEIC files start with a `ftyp` box; bytes 4..8 are `ftyp`, bytes
    8..12 are the major brand. We accept any brand in `_HEIC_BRANDS`."""
    if len(head_bytes) < 12:
        return False
    if head_bytes[4:8] != b"ftyp":
        return False
    return head_bytes[8:12] in _HEIC_BRANDS


# ---------------------------------------------------------------------
# Page counting — format-specific.
# ---------------------------------------------------------------------


def is_image_format(fmt: UploadFormat) -> bool:
    """True for every format in the §2.1 image group. Used at OCR time
    to skip the pdftoppm rasterize step."""
    return fmt in (
        UploadFormat.JPEG,
        UploadFormat.PNG,
        UploadFormat.TIFF,
        UploadFormat.HEIC,
        UploadFormat.WEBP,
    )


def is_direct_text_format(fmt: UploadFormat) -> bool:
    """True for K-2 + K-3 direct-text formats — DOCX/ODT/TXT/XML/HTML
    plus EPUB/MOBI/AZW/AZW3.

    The finalize branch extracts text at upload time and writes
    Segments directly, bypassing the OCR pipeline. The OCR endpoint
    refuses these (no rasterizable bytes — `_rasterize_page` raises)."""
    return fmt in _DIRECT_TEXT_FORMATS


def is_archive_format(fmt: UploadFormat) -> bool:
    """True for K-4 archive formats — ZIP/RAR/CBZ/CBR.

    The finalize branch extracts entries, sorts by filename (canon
    §2.1), and recurses into each supported entry via the existing
    per-format finalize path. Nested archives (archive-of-archive)
    are NOT recursed — canon stops at one level.
    """
    return fmt in _ARCHIVE_FORMATS


def count_pages(*, path: Path, fmt: UploadFormat) -> int:
    """Count the logical pages in the source file.

    PDF: `pypdf.PdfReader.pages`.
    TIFF: `PIL.Image.n_frames` — multi-page TIFFs (common in scanned
          books) become one Page per frame.
    DjVu (K-3): `djvused -e 'n'` reports the page count. Raises
          `DjvuToolsMissing` when `djvused` isn't on PATH (deployment
          needs `apt install djvulibre-bin`).
    Direct-text formats (DOCX/ODT/TXT/XML/HTML/EPUB/MOBI/AZW/AZW3):
          always 1 — the paragraphs become Segments within a single
          Block on a single Page. Multi-page-document pagination (e.g.
          honoring DOCX explicit page breaks or EPUB spine items) is
          deferred; python-docx doesn't expose page boundaries anyway
          (they're rendered at print) and EPUB chapters can be very
          uneven in length.
    Other images (JPEG / PNG / HEIC / WEBP): always 1.
    """
    if fmt == UploadFormat.PDF:
        return _count_pdf_pages(path)
    if fmt == UploadFormat.TIFF:
        return _count_tiff_frames(path)
    if fmt == UploadFormat.DJVU:
        return _count_djvu_pages(path)
    return 1


def _count_pdf_pages(path: Path) -> int:
    from pypdf import PdfReader

    return len(PdfReader(path).pages)


def _count_tiff_frames(path: Path) -> int:
    """Return the number of frames in a TIFF. PIL's `n_frames` is the
    canonical accessor; falls back to 1 if the TIFF is malformed enough
    that PIL can't enumerate (we trust PIL to raise on actual decode
    failure rather than silently mis-count)."""
    from PIL import Image

    with Image.open(path) as img:
        return int(getattr(img, "n_frames", 1))


class DjvuToolsMissing(RuntimeError):
    """Raised when `djvused` / `ddjvu` aren't on PATH. The deployment
    must install `djvulibre-bin` (apt) to enable DjVu uploads. The
    upload service converts this to HTTP 415 with a clear install hint
    so the user knows it's a host-side gap, not a corrupt file."""


class UnrarToolsMissing(RuntimeError):
    """Raised when `unrar` isn't on PATH (K-4 RAR/CBR uploads). The
    deployment must install `unrar` (apt) to enable. Same pattern as
    `DjvuToolsMissing` — adapter wired, system bin activates. The
    upload service surfaces as HTTP 503."""


def _count_djvu_pages(path: Path) -> int:
    """Use `djvused -e 'n'` to count pages — the canonical DjVu CLI
    way. Output is a single number on stdout. Same canonical pattern
    as `pdftoppm` for PDFs: deployment-supplied system binary, adapter
    fails gracefully when absent."""
    import shutil
    import subprocess

    if shutil.which("djvused") is None:
        raise DjvuToolsMissing(
            "djvused not found on PATH. DjVu uploads need the "
            "djvulibre-bin package — install via `apt install djvulibre-bin`."
        )
    proc = subprocess.run(
        ["djvused", "-e", "n", str(path)],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise DjvuToolsMissing(
            f"djvused failed (rc={proc.returncode}): "
            f"{proc.stderr.decode('utf-8', errors='replace')[:200]}"
        )
    raw = proc.stdout.decode("utf-8", errors="replace").strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise DjvuToolsMissing(
            f"djvused returned non-integer page count: {raw!r}"
        ) from exc


__all__ = [
    "DjvuToolsMissing",
    "UnrarToolsMissing",
    "UnsupportedFormat",
    "UploadFormat",
    "count_pages",
    "detect_format",
    "is_archive_format",
    "is_direct_text_format",
    "is_image_format",
]
