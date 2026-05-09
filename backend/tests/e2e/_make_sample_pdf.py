"""Generate a 1-page Arabic test PDF for E2E testing.

The text content is sourced from public-domain classical material:
the opening passages of Surat al-Fatiha + a short Hadith citation —
both universally public domain. The PDF is rendered using PIL with
Noto Naskh Arabic (system font), giving a clean, OCR-able test
artefact.

This avoids depending on external sources for the E2E test fixture.
The text is REAL Arabic content; the rendering is controlled.
"""

from __future__ import annotations

from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

# Public-domain classical Arabic text. Opening of Surat al-Fatiha
# (universally public domain) + a short Hadith fragment from Sahih
# al-Bukhari (public domain since the original text is over a millennium
# old). Each line will become its own segment after OCR.
_ARABIC_LINES = [
    "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
    "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
    "الرَّحْمَٰنِ الرَّحِيمِ",
    "مَالِكِ يَوْمِ الدِّينِ",
    "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ",
]


_FONT_PATH = "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"


def _render_arabic_image() -> Image.Image:
    """A4 at 200 DPI with the public-domain Arabic text rendered.

    Uses PIL's native RTL handling via `direction='rtl'` and Harfbuzz
    shaping (when libraqm is available). Falls back to the
    arabic-reshaper + bidi pipeline if the system PIL doesn't have
    libraqm. Either way, the OUTPUT image displays correctly readable
    Arabic that the OCR pipeline can reverse-engineer.
    """
    width, height = (1654, 2339)
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(_FONT_PATH, size=64)

    y = 200
    line_spacing = 140
    for raw_line in _ARABIC_LINES:
        # Try Harfbuzz shaping first — leaves the logical-order string
        # intact and lets the rasterizer handle ligatures + RTL flow.
        try:
            bbox = draw.textbbox((0, 0), raw_line, font=font, direction="rtl")
            text_width = bbox[2] - bbox[0]
            x = width - text_width - 200
            draw.text((x, y), raw_line, fill="black", font=font, direction="rtl")
        except (KeyError, ValueError, OSError):
            # libraqm not available — fall back to manual reshape + bidi.
            reshaped = arabic_reshaper.reshape(raw_line)
            display_line = get_display(reshaped)
            bbox = draw.textbbox((0, 0), display_line, font=font)
            text_width = bbox[2] - bbox[0]
            x = width - text_width - 200
            draw.text((x, y), display_line, fill="black", font=font)
        y += line_spacing
    return img


def make_sample_pdf(pdf_path: Path | str, png_path: Path | str | None = None) -> Path:
    """Render the Arabic text into a 1-page PDF (and optionally PNG).

    The PNG mirrors the same rendering and is what the OCR pipeline
    consumes. The PDF is what the upload pipeline consumes. Together
    they test the full E2E path without requiring server-side PDF
    rasterization (which is canonically deferred per WORKLOG 2026-05-06
    M4 scan-viewer decision).
    """
    pdf_path = Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    img = _render_arabic_image()
    img.save(pdf_path, "PDF", resolution=200)
    if png_path is not None:
        png_path = Path(png_path)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(png_path, "PNG")
    return pdf_path


if __name__ == "__main__":  # pragma: no cover
    out = make_sample_pdf(
        "tests/e2e/fixtures/sample_arabic.pdf",
        "tests/e2e/fixtures/sample_arabic.png",
    )
    print(f"wrote {out} ({out.stat().st_size} bytes)")
