"""Exceptions for the OCR-text-export pipeline (Sprint-OCR)."""

from __future__ import annotations


class OcrExportError(Exception):
    """Base class for OCR-export violations."""


class OcrExportBlocked(OcrExportError):
    """`run_ocr_export` was invoked but the OCR-export gate is blocked.

    Per Sprint-OCR §2 / OCR-Gate-Blockiert-Start-Kein-Log-Test: a blocked
    `start_ocr_export` produces NO log entry and NO job start. This
    exception fires after the pre-check; no log entry is written before
    raising."""


class OcrExportPflichtfragenMissing(OcrExportError):
    """Required Pflichtfragen confirmations missing (page range, block
    types, markings, export mode). Per OCR-Gate-Pflichtfragen-Aktiv-Test:
    export without actively answered Pflichtfragen → blocked.

    Sprint-OCR §A H-3 analogue: no artefact creation without active
    confirmations. Saved profiles pre-fill but never replace."""


class DocxArtefactFailed(OcrExportError):
    """The DOCX artefact build raised an error mid-build. Per Sprint-OCR
    §2: a failed DOCX produces NO OCR_EXPORT_EVENT and a single
    `OCR_EXPORT_FAILED` log entry."""
