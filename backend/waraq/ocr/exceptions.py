"""OCR pipeline exceptions.

T-4.1.1 introduces the base classes; T-4.1.3 will refine them into the
canonical F-01 through F-09 error classes per CAB §B / Dokument 1 §3.4.
"""

from __future__ import annotations


class OcrError(Exception):
    """Base for OCR-pipeline errors."""


class GeminiApiError(OcrError):
    """Wraps any error returned by or raised against the Gemini API.

    Carries `cause` (the underlying exception) and `model` (which model was
    targeted) so T-4.1.3 can profile failures into F-01..F-09."""

    def __init__(self, *, model: str, cause: BaseException) -> None:
        super().__init__(f"Gemini call to {model!r} failed: {cause!r}")
        self.model = model
        self.cause = cause


class MissingGeminiApiKey(OcrError):
    """Raised when the OCR service is invoked without GOOGLE_AI_API_KEY set."""

    def __init__(self) -> None:
        super().__init__(
            "GOOGLE_AI_API_KEY is empty in settings/env. "
            "Set it in backend/.env or pass an explicit extractor for tests."
        )
