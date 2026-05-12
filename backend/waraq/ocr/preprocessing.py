"""§3.3 — OCR image preprocessing harness for low-DPI scans.

Canon §3.3 mandates Real-ESRGAN super-resolution + OpenCV adaptive
preprocessing for low-DPI scans. This module ships the **harness**:

  - DPI threshold constant for "low-DPI" detection (calibration,
    re-tunable in Phase 7).
  - `Preprocessor` Protocol — pluggable adapter signature.
  - `_default_preprocessor` — pass-through (no-op). Production
    deployments wire the real Real-ESRGAN + OpenCV adapter via the
    `preprocessor` parameter on `preprocess_if_needed`.
  - `should_preprocess(source_dpi)` — pure predicate.
  - `preprocess_if_needed(image_bytes, source_dpi, preprocessor)` —
    the integration point `run_ocr_for_page` calls.

The Real-ESRGAN model invocation itself is deferred to a deployment
concern (the model is ~70 MB + PyTorch). This module's contract is:
the *gate* (when to preprocess) is in code; the *implementation*
(what preprocessing does) is pluggable.
"""

from __future__ import annotations

from collections.abc import Callable

# Below this DPI a scan is considered low-quality enough that
# Real-ESRGAN + adaptive preprocessing is canonically warranted.
# 200 DPI is the PDF-rendering default elsewhere in the pipeline
# (`_render_page_png(dpi=200)`); a source PDF rendered below that
# threshold is the trigger condition.
LOW_DPI_THRESHOLD: int = 200

# A preprocessor takes (image_bytes, source_dpi) and returns the
# possibly-enhanced image_bytes. The default is the identity; real
# adapters return bytes of the same image format (PNG in / PNG out).
Preprocessor = Callable[[bytes, int], bytes]


def _default_preprocessor(image_bytes: bytes, source_dpi: int) -> bytes:
    """No-op identity preprocessor.

    The default deliberately does nothing so a host without
    Real-ESRGAN / OpenCV behaves exactly like the pre-Phase-4
    pipeline. Production deployments override via the `preprocessor`
    parameter on `preprocess_if_needed`.
    """
    _ = source_dpi
    return image_bytes


def should_preprocess(source_dpi: int) -> bool:
    """Pure: would a scan at `source_dpi` warrant preprocessing?

    Returns True iff `source_dpi` is below `LOW_DPI_THRESHOLD`. A
    `source_dpi` of 0 or unknown (caller passes 0 to mean "couldn't
    detect") triggers preprocessing — the conservative choice when
    we can't tell.
    """
    return source_dpi < LOW_DPI_THRESHOLD


def preprocess_if_needed(
    image_bytes: bytes,
    source_dpi: int,
    *,
    preprocessor: Preprocessor | None = None,
) -> tuple[bytes, bool]:
    """Apply preprocessing iff `source_dpi` is below the low-DPI gate.

    Returns `(possibly_modified_bytes, was_preprocessed)`. The bool
    is recorded on the OCR-PO so audit can tell whether the OCR
    engine saw raw-rasterized bytes or super-resolved bytes.
    """
    if not should_preprocess(source_dpi):
        return image_bytes, False
    fn = preprocessor if preprocessor is not None else _default_preprocessor
    return fn(image_bytes, source_dpi), True


__all__ = [
    "LOW_DPI_THRESHOLD",
    "Preprocessor",
    "preprocess_if_needed",
    "should_preprocess",
]
