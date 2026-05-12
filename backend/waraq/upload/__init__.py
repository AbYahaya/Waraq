"""Upload pipeline — chunked receive, finalize, SCAN-PO materialization.

Side-effect on import: registers `pillow_heif` as a PIL opener so that
HEIC/HEIF uploads (Phase 5 sub-batch K-1) load through `PIL.Image.open`
without per-call setup. Lazy/guarded so a host without `pillow_heif`
installed degrades to "HEIC not supported" rather than failing imports.
"""

from __future__ import annotations

from waraq.upload.archive import (
    ArchiveCorrupted,
    ArchiveError,
    EmptyArchive,
    extract_and_sort,
)
from waraq.upload.exceptions import (
    ChunkOutOfOrder,
    IncompleteUpload,
    UploadError,
    UploadNotFound,
    UploadSizeMismatch,
    UploadTooLarge,
)
from waraq.upload.file_type import (
    DjvuToolsMissing,
    UnrarToolsMissing,
    UnsupportedFormat,
    UploadFormat,
    count_pages,
    detect_format,
    is_archive_format,
    is_direct_text_format,
    is_image_format,
)
from waraq.upload.service import (
    JOB_TYPE,
    UploadStatus,
    append_chunk,
    finalize_upload,
    get_upload_status,
    start_upload,
)
from waraq.upload.text_extraction import (
    EmptyDocument,
    TextExtractionError,
    extract_paragraphs,
)


def _try_register_heif_opener() -> None:
    """Register pillow_heif's HEIF opener with PIL globally. Idempotent
    — pillow_heif tolerates being called more than once. Swallows
    ImportError so dev hosts without the package can still import this
    module; HEIC uploads then fall through to the format-unsupported
    branch in `detect_format`."""
    try:
        import pillow_heif
    except ImportError:
        return
    pillow_heif.register_heif_opener()


_try_register_heif_opener()


__all__ = [
    "JOB_TYPE",
    "ArchiveCorrupted",
    "ArchiveError",
    "ChunkOutOfOrder",
    "DjvuToolsMissing",
    "EmptyArchive",
    "EmptyDocument",
    "IncompleteUpload",
    "TextExtractionError",
    "UnrarToolsMissing",
    "UnsupportedFormat",
    "UploadError",
    "UploadFormat",
    "UploadNotFound",
    "UploadSizeMismatch",
    "UploadStatus",
    "UploadTooLarge",
    "append_chunk",
    "count_pages",
    "detect_format",
    "extract_and_sort",
    "extract_paragraphs",
    "finalize_upload",
    "get_upload_status",
    "is_archive_format",
    "is_direct_text_format",
    "is_image_format",
    "start_upload",
]
