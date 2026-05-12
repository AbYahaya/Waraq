"""Phase 4 sub-batch H — OpenCV-backed `Preprocessor` production adapter."""

from __future__ import annotations

from io import BytesIO

import pytest

from waraq.ocr.preprocessing import preprocess_if_needed
from waraq.ocr.preprocessing_opencv import opencv_preprocessor

pytest.importorskip("cv2")
pytest.importorskip("PIL")


def _solid_png(*, size: tuple[int, int] = (400, 300), color: str = "white") -> bytes:
    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _decode_size(image_bytes: bytes) -> tuple[int, int]:
    from PIL import Image

    with Image.open(BytesIO(image_bytes)) as pil:
        return pil.size  # (width, height)


class TestUpsample:
    def test_below_threshold_dpi_doubles_size(self) -> None:
        # source DPI 100 → target 300 → scale capped at 2× → 800×600.
        original = _solid_png(size=(400, 300), color="white")
        out = opencv_preprocessor(original, source_dpi=100)
        out_w, out_h = _decode_size(out)
        # After 2× upsample.
        assert out_w == 800
        assert out_h == 600

    def test_at_target_dpi_no_upsample_returns_original_bytes(self) -> None:
        # source DPI 300 = target → scale ≤ 1.0 → return original.
        original = _solid_png(size=(400, 300))
        out = opencv_preprocessor(original, source_dpi=300)
        assert out == original

    def test_unknown_dpi_zero_assumes_worst_case(self) -> None:
        original = _solid_png(size=(400, 300))
        out = opencv_preprocessor(original, source_dpi=0)
        out_w, out_h = _decode_size(out)
        # Worst-case: 2× scale.
        assert out_w == 800
        assert out_h == 600

    def test_garbage_bytes_returned_unchanged(self) -> None:
        garbage = b"not-an-image"
        out = opencv_preprocessor(garbage, source_dpi=100)
        assert out == garbage

    def test_output_is_decodable_png(self) -> None:
        from PIL import Image

        original = _solid_png(size=(400, 300))
        out = opencv_preprocessor(original, source_dpi=100)
        with Image.open(BytesIO(out)) as pil:
            pil.verify()  # raises if malformed


class TestHarnessIntegration:
    def test_preprocess_if_needed_uses_opencv_when_supplied(self) -> None:
        # The §3.3 harness gate fires below 200 DPI. Wire the OpenCV
        # adapter in and verify the output is upsampled.
        original = _solid_png(size=(400, 300))
        out, was_preprocessed = preprocess_if_needed(
            original, 100, preprocessor=opencv_preprocessor
        )
        assert was_preprocessed is True
        out_w, out_h = _decode_size(out)
        assert (out_w, out_h) == (800, 600)

    def test_above_threshold_skips_preprocessor(self) -> None:
        # 300 DPI is at-target — the gate does NOT fire above the
        # threshold, so the preprocessor isn't invoked at all.
        original = _solid_png(size=(400, 300))
        out, was_preprocessed = preprocess_if_needed(
            original, 300, preprocessor=opencv_preprocessor
        )
        assert was_preprocessed is False
        assert out == original
