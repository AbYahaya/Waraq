"""§2.1 Phase 5 K-4 — archive extraction + filename-sort for ZIP/RAR/CBZ/CBR.

The four archive formats wrap a sequence of inner files. Per canon
§2.1 "Archive formats (ZIP/RAR/CBZ/CBR with filename-sort)", we:

  1. Extract each entry to disk (under the upload's per-job dir so
     the bytes survive between finalize and downstream OCR / direct-
     text materialization).
  2. **Sort by filename** — archive orderings are not stable, but the
     CBZ/CBR comic-book convention is alphabetical-by-filename. We
     normalize to that for every archive type so the user sees pages
     in a predictable order regardless of how the archive was built.
  3. Filter out entries that don't resolve to a supported upload
     format. Hidden files (`.*`), MacOS `__MACOSX` resource forks, and
     `Thumbs.db` are silently skipped.
  4. **Refuse nested archives** — canon §2.1 says "recurse into
     supported formats", which the supported-formats set names; archive
     formats are NOT among the recursion targets. An archive inside an
     archive is silently skipped (not an error) — surfacing that as
     422 would be hostile when the rest of the archive is fine.

`extract_and_sort(path, archive_fmt, dest_dir)` returns a list of
`(inner_path, inner_format)` tuples in canonical filename-sorted order.
Raises `UnrarToolsMissing` for RAR/CBR when `unrar` isn't on PATH;
raises `ArchiveCorrupted` for unreadable archives; raises
`EmptyArchive` when zero supported entries are found.

RAR/CBR support requires the `unrar` system binary (apt install unrar).
Mirrors the `pdftoppm` / `djvulibre-bin` pattern: adapter wired in code,
system install activates.
"""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from waraq.upload.file_type import (
    UnrarToolsMissing,
    UnsupportedFormat,
    UploadFormat,
    detect_format,
    is_archive_format,
)


class ArchiveError(ValueError):
    """Base class for archive-extraction failures."""


class ArchiveCorrupted(ArchiveError):
    """Raised when the archive can't be opened / read (bad CRC, truncated,
    wrong format). Surfaces as HTTP 422."""


class EmptyArchive(ArchiveError):
    """Raised when the archive has no entries that resolve to supported
    upload formats. Surfaces as HTTP 422 rather than silently producing
    a 0-Page upload."""


@dataclass(frozen=True, kw_only=True, slots=True)
class ArchiveEntry:
    """One extracted entry ready for per-format finalize processing.

    `inner_path` is the path of the extracted file on disk (under the
    upload's per-job dir).
    `inner_filename` is the original filename inside the archive (for
    SCAN-PO audit + filename-sort verification).
    `fmt` is the resolved `UploadFormat` of the inner file.
    """

    inner_path: Path
    inner_filename: str
    fmt: UploadFormat


def extract_and_sort(
    *, archive_path: Path, archive_fmt: UploadFormat, dest_dir: Path
) -> list[ArchiveEntry]:
    """Extract `archive_path` (a ZIP/RAR/CBZ/CBR) into `dest_dir`,
    filter to supported non-archive entries, sort by filename, return
    the list in processing order.

    Args:
        archive_path: Path to the assembled archive source.
        archive_fmt: Which archive format — picks ZIP-vs-RAR backend.
        dest_dir: Where to extract entries. Created if missing; the
            caller owns cleanup.

    Raises:
        UnrarToolsMissing: RAR/CBR upload, `unrar` not on PATH.
        ArchiveCorrupted: archive can't be opened or read.
        EmptyArchive: zero supported entries after filtering.
    """
    if not is_archive_format(archive_fmt):
        raise ArchiveError(f"Format {archive_fmt.value!r} is not an archive format")

    dest_dir.mkdir(parents=True, exist_ok=True)

    if archive_fmt in (UploadFormat.ZIP, UploadFormat.CBZ):
        raw_entries = _extract_zip(archive_path, dest_dir)
    else:  # RAR / CBR
        raw_entries = _extract_rar(archive_path, dest_dir)

    # Filter + classify each extracted file.
    classified: list[ArchiveEntry] = []
    for entry_filename, entry_path in raw_entries:
        if _is_noise_entry(entry_filename):
            continue
        try:
            with entry_path.open("rb") as f:
                head = f.read(64)
            inner_fmt = detect_format(filename=entry_filename, head_bytes=head)
        except (OSError, UnsupportedFormat):
            # Skip entries we can't read or that don't resolve to a
            # supported format. The canon rule is "recurse into
            # supported formats" — unsupported entries are silent
            # skips, not errors.
            continue
        if is_archive_format(inner_fmt):
            # Nested archives are silent skips per the one-level
            # canon recursion rule.
            continue
        classified.append(
            ArchiveEntry(
                inner_path=entry_path,
                inner_filename=entry_filename,
                fmt=inner_fmt,
            )
        )

    # Filename-sort per canon §2.1. Case-insensitive so a mixed-case
    # comic archive ('Page01.jpg', 'page02.jpg') still produces the
    # user's expected order.
    classified.sort(key=lambda e: e.inner_filename.casefold())

    if not classified:
        raise EmptyArchive(
            f"Archive {archive_path.name!r} contains no supported entries "
            "(supported formats are PDF, images, documents, e-books — "
            "nested archives are not recursed)."
        )
    return classified


def _extract_zip(archive_path: Path, dest_dir: Path) -> list[tuple[str, Path]]:
    """ZIP / CBZ extraction via stdlib zipfile. Returns `(name, path)`
    tuples — names preserved exactly as recorded in the archive (for
    sorting); paths are flattened under `dest_dir` to avoid path-
    traversal attacks (zip-slip)."""
    try:
        zf = zipfile.ZipFile(archive_path)
    except zipfile.BadZipFile as exc:
        raise ArchiveCorrupted(f"Could not open ZIP {archive_path.name}: {exc!r}") from exc

    out: list[tuple[str, Path]] = []
    try:
        for info in zf.infolist():
            if info.is_dir():
                continue
            inner_name = info.filename
            # Flatten the inner directory tree to prevent zip-slip:
            # use only the basename when writing to disk. Filename-sort
            # uses the full archive-internal name so directory order
            # is preserved (foo/01.jpg sorts before foo/02.jpg).
            safe_basename = _safe_flat_name(inner_name)
            out_path = dest_dir / safe_basename
            # Ensure uniqueness when two entries flatten to the same
            # basename (rare; archives with deep directory structure).
            out_path = _unique_path(out_path)
            try:
                with zf.open(info) as src, out_path.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
            except Exception as exc:
                raise ArchiveCorrupted(f"Could not read ZIP entry {inner_name!r}: {exc!r}") from exc
            out.append((inner_name, out_path))
    finally:
        zf.close()
    return out


def _extract_rar(archive_path: Path, dest_dir: Path) -> list[tuple[str, Path]]:
    """RAR / CBR extraction via the `rarfile` lib. Requires `unrar` on
    PATH; raises `UnrarToolsMissing` cleanly when absent."""
    if shutil.which("unrar") is None:
        raise UnrarToolsMissing(
            "unrar not found on PATH. RAR/CBR uploads need the `unrar` "
            "system binary — install via `apt install unrar`."
        )
    try:
        import rarfile
    except ImportError as exc:
        raise ArchiveError(
            "rarfile not installed in this venv. Install via `pip install rarfile`."
        ) from exc

    try:
        rf = rarfile.RarFile(archive_path)
    except (rarfile.NotRarFile, rarfile.BadRarFile) as exc:
        raise ArchiveCorrupted(f"Could not open RAR {archive_path.name}: {exc!r}") from exc

    out: list[tuple[str, Path]] = []
    try:
        for info in rf.infolist():
            if info.is_dir():
                continue
            inner_name = info.filename
            safe_basename = _safe_flat_name(inner_name)
            out_path = dest_dir / safe_basename
            out_path = _unique_path(out_path)
            try:
                with rf.open(info) as src, out_path.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
            except Exception as exc:
                raise ArchiveCorrupted(f"Could not read RAR entry {inner_name!r}: {exc!r}") from exc
            out.append((inner_name, out_path))
    finally:
        rf.close()
    return out


def _is_noise_entry(filename: str) -> bool:
    """Skip OS-level junk that creeps into archives: macOS resource
    forks, hidden files (dot-prefixed at any level), Windows
    `Thumbs.db`. These are not supported uploads; they'd just produce
    detection failures."""
    parts = filename.replace("\\", "/").split("/")
    for part in parts:
        if not part:
            continue
        if part.startswith("__MACOSX") or part.startswith("._"):
            return True
        if part.startswith(".") and part not in (".", ".."):
            return True
        if part == "Thumbs.db":
            return True
    return False


def _safe_flat_name(inner_name: str) -> str:
    """Flatten any directory structure inside the archive to a single
    basename, and strip anything that could escape `dest_dir` via
    path-traversal. The original `inner_name` is preserved separately
    for filename-sort and SCAN-PO audit."""
    # Replace path separators with `__` so the resulting basename is
    # still informative ('chapter1__page05.jpg') but can't escape the
    # dest dir. Strip leading dots / slashes defensively.
    normalized = inner_name.replace("\\", "/").lstrip("/.")
    flattened = normalized.replace("/", "__")
    if not flattened or flattened in (".", ".."):
        flattened = "entry"
    return flattened


def _unique_path(path: Path) -> Path:
    """If `path` already exists in `dest_dir`, append `_1`, `_2`, ...
    until unique. Prevents collisions when two archive entries flatten
    to the same basename."""
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    n = 1
    while True:
        candidate = parent / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


__all__ = [
    "ArchiveCorrupted",
    "ArchiveEntry",
    "ArchiveError",
    "EmptyArchive",
    "extract_and_sort",
]
