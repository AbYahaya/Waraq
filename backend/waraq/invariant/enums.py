from __future__ import annotations

from enum import StrEnum


class LockFlag(StrEnum):
    """Per CAB §B.1 — segment lock flag canonical values."""

    NONE = "none"
    MANUAL_LOCAL = "manual_local"
    MANUAL_EDITORIAL = "manual_editorial"


class OperationMode(StrEnum):
    """Whether an operation is system-automatic or manual with explicit user confirmation."""

    AUTOMATIC = "automatic"
    MANUAL_WITH_CONFIRMATION = "manual_with_confirmation"


class OperationKind(StrEnum):
    """H-4: check operations never get a revision-UUID; text changes do."""

    CHECK = "check"
    TEXT_CHANGE = "text_change"
