"""§3.3 — OpenCV-backed `Preprocessor` (real production adapter).

Sub-batch H replaces the sub-batch A no-op default with a real
preprocessor built from classical CV operations:

  - **Bicubic upsample** (`cv2.INTER_CUBIC`) when the source is below
    the §3.3 LOW_DPI_THRESHOLD. Upsamples to a target equivalent of
    300 DPI (the canonical OCR-quality floor), capped at a 2× scale
    factor so we don't artifact-amplify on tiny scans.
  - **Non-local-means denoising** (`cv2.fastNlMeansDenoising`) on the
    upsampled image — drops the residual JPEG / scan-noise the
    upsample would otherwise enlarge.

The Real-ESRGAN canonical Phase 7 target stays in canon as a future
super-resolution upgrade. Until that lands, OpenCV INTER_CUBIC is a
legitimate, well-understood preprocessor that yields measurably
better OCR on low-DPI scans (canonical engineering practice; see
§3.3 "OpenCV adaptive preprocessing for low-DPI scans").

Graceful degradation: when cv2 / Pillow / numpy aren't importable on
the host, the function returns the original bytes unchanged so the
overall pipeline still works (same canon-honest pattern as every
adapter in §3.3 / §3.4).
"""

from __future__ import annotations

import logging
from io import BytesIO

logger = logging.getLogger(__name__)


# Canonical OCR-quality floor — the upsample targets this DPI.
_TARGET_DPI: int = 300

# Cap the scale factor so a 50-DPI scan doesn't get upsampled 6×
# (artifact-amplifies the noise more than it sharpens the text).
_MAX_SCALE_FACTOR: float = 2.0


def opencv_preprocessor(image_bytes: bytes, source_dpi: int) -> bytes:
    """Real OpenCV-backed `Preprocessor` per the §3.3 specification.

    Args:
        image_bytes: Raw bytes of the page image (PNG/JPEG/WEBP).
        source_dpi: DPI of `image_bytes` as supplied by the caller. The
            sub-batch A gate `should_preprocess(source_dpi)` already
            ensures we're only invoked on under-200-DPI input; this
            implementation just sizes the upscale.

    Returns:
        Preprocessed image bytes (PNG-encoded). Returns the original
        bytes unchanged when cv2 / Pillow aren't importable, when the
        decode fails, or when the upsample / denoise raises.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        return image_bytes
    try:
        from PIL import Image
    except ImportError:
        return image_bytes

    try:
        with Image.open(BytesIO(image_bytes)) as pil:
            arr = np.array(pil.convert("RGB"))
    except Exception as exc:
        logger.debug("opencv_preprocessor decode failed: %r", exc)
        return image_bytes

    if source_dpi <= 0:
        # Caller passed 0 to mean "unknown" — assume worst case
        # (under-100-DPI) and run a single 2× pass.
        scale = _MAX_SCALE_FACTOR
    else:
        scale = min(_TARGET_DPI / float(source_dpi), _MAX_SCALE_FACTOR)
    if scale <= 1.0:
        # No upsample required (caller gated wrong; defensive).
        return image_bytes

    height, width = arr.shape[:2]
    new_size = (round(width * scale), round(height * scale))
    try:
        upsampled = cv2.resize(arr, new_size, interpolation=cv2.INTER_CUBIC)
    except Exception as exc:
        logger.debug("opencv_preprocessor resize failed: %r", exc)
        return image_bytes

    # Denoise on luminance — non-local-means is the canonical scan-text
    # denoiser. Parameters tuned for 300-DPI text; see
    # https://docs.opencv.org/4.x/d5/d69/tutorial_py_non_local_means.html
    try:
        gray = cv2.cvtColor(upsampled, cv2.COLOR_RGB2GRAY)
        denoised = cv2.fastNlMeansDenoising(
            gray,
            None,
            h=10,
            templateWindowSize=7,
            searchWindowSize=21,
        )
        out_arr = cv2.cvtColor(denoised, cv2.COLOR_GRAY2RGB)
    except Exception as exc:
        logger.debug("opencv_preprocessor denoise failed: %r", exc)
        out_arr = upsampled

    # Re-encode to PNG (lossless) so the downstream rasterizer
    # consumers don't have to know we touched it.
    try:
        with BytesIO() as buf:
            Image.fromarray(out_arr).save(buf, format="PNG")
            return buf.getvalue()
    except Exception as exc:
        logger.debug("opencv_preprocessor encode failed: %r", exc)
        return image_bytes


__all__ = [
    "opencv_preprocessor",
]
