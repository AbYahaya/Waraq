"""Exceptions for the T-7.1.1 / T-7.1.2 translation pipeline."""

from __future__ import annotations


class TranslationJobError(Exception):
    """Base class for translation-pipeline violations."""


class TranslationJobNotPending(TranslationJobError):
    """`run_translation_job` called on a Job that is not in PENDING state.
    Use `resume_translation_job` to continue a paused/running job."""


class TranslationJobUebersetzungsstartMissing(TranslationJobError):
    """Job was started without a corresponding `uebersetzungsstart`
    Decision Event (per Sprint 2 §2 / DBB §B Abkürzung 5).

    The release-gate `start_translation` writes the DE; the translation
    job creation reads for it and refuses if it's missing. This decouples
    "gate ready" from "translation actually requested" and makes
    auto-trigger-on-go structurally impossible."""


class TranslationJobCancelled(TranslationJobError):
    """Cooperative cancellation: the user (or an admin path) flipped
    `payload.cancel_requested = true`; the `_execute` loop noticed
    between chunks and aborted. The Job is left in `failed` state with
    `error.phase = "user_cancelled"` so the §3.6 30-min watcher does NOT
    fire (the user knows about this failure)."""
