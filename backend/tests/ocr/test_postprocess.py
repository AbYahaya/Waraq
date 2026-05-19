from __future__ import annotations

from waraq.ocr.postprocess import sanitize_ocr_output


def test_strips_openai_refusal_tail_from_ocr_output() -> None:
    raw = (
        "سؤال ، رؤية .\n"
        "I'm unable to perform OCR on this image. If you have any other questions "
        "or need assistance, feel free to ask"
    )
    assert sanitize_ocr_output(raw) == "سؤال ، رؤية ."
