"""T-9.2.1 — Atomic artefact-store abstraction.

Per Sprint 5 §2 / DBB Abkürzung 4: the EXPORT_EVENT must never be
created without a fully-successful artefact persisted at its final
location. The atomic-commit step (a) "moves the artefact to its
persistent location" is gated by this store.

This module provides the storage abstraction. The default
`InMemoryArtefactStore` keeps bytes in memory keyed by artefact_uuid;
for tests, callers can pass a `failing_store` that raises
`ArtefactStoreCommitFailed` to exercise the atomic-commit failure
path (Atomare-Commit-Step-Test).

In v1.0 the artefact bytes are not durably persisted on disk by the
default store — only the artefact identity (sha256, size_bytes) lives
on the EXPORT_EVENT-PO payload. M5 work will swap in a content-
addressed disk/S3 store. The interface is stable.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Protocol


class ArtefactStoreCommitFailed(Exception):
    """Raised when the artefact-storage commit step fails.

    Used by `InMemoryArtefactStore` test-injection hooks to simulate
    a failure during step (a) of the atomic-commit transaction. The
    export pipeline catches this, marks the Job FAILED, writes the
    Exportlauf-Ereignis Log-Eintrag, and refuses to write
    EXPORT_EVENT. The caller's transaction rolls back any partial
    state.
    """


class ArtefactStore(Protocol):
    """Storage interface — the export service depends only on this.

    `commit` is the atomic-commit step (a) per Sprint 5 §2. It is the
    sole writer to the persistent location; failures here are the
    canonical "step (a) failure" the atomicity test exercises.
    """

    def commit(self, *, artefact_uuid: _uuid.UUID, bytes_: bytes) -> str: ...

    def get(self, *, artefact_uuid: _uuid.UUID) -> bytes | None: ...


class InMemoryArtefactStore:
    """In-process artefact store. Default for v1.0.

    The optional `fail_on_commit` switch lets tests force a step-(a)
    failure without touching production code paths. The store keeps
    bytes only when commit succeeds; a failed commit leaves the store
    untouched (no orphaned bytes).
    """

    def __init__(self, *, fail_on_commit: bool = False) -> None:
        self._fail_on_commit = fail_on_commit
        self._bytes_by_uuid: dict[_uuid.UUID, bytes] = {}

    def commit(self, *, artefact_uuid: _uuid.UUID, bytes_: bytes) -> str:
        if self._fail_on_commit:
            raise ArtefactStoreCommitFailed(f"forced commit failure for artefact {artefact_uuid}")
        self._bytes_by_uuid[artefact_uuid] = bytes_
        return f"memory://{artefact_uuid}"

    def get(self, *, artefact_uuid: _uuid.UUID) -> bytes | None:
        return self._bytes_by_uuid.get(artefact_uuid)


__all__ = [
    "ArtefactStore",
    "ArtefactStoreCommitFailed",
    "InMemoryArtefactStore",
]
