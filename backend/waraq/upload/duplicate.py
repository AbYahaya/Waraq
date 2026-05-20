"""§2.1 + §2.2 Phase 5 K-5 — duplicate detection + 1-book-at-a-time check.

Two warning surfaces (canon §2.1 row 6, §2.2 row 7):

  1. **Duplicate filename or SHA-256** within the same project. The
     user uploaded a file whose name or content matches an existing
     upload in this project. Modal warning, NOT a hard block — the
     user can confirm "yes, upload anyway" (some workflows legitimately
     re-upload the same scan).

  2. **1-book-at-a-time** — uploading a new file into a project that
     already has materialized Pages from a prior upload. Modal warning
     to confirm the user wants a multi-source project.

This module is read-only over `ProvenanceObject` and `Page`. The
upload `service.py` is forbidden from importing `ProvenanceObject`
directly (Abkürzung 7 AST guard on the write path); placing these
read queries in a sibling module preserves that guard while keeping
the logic in the upload domain.
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.schemas import Job, Page, ProvenanceObject
from waraq.schemas.enums import POType, ScopeType


@dataclass(frozen=True, kw_only=True, slots=True)
class DuplicateMatch:
    """One existing Page that matches the new upload on filename or
    SHA-256. The frontend renders this in the duplicate-warning modal
    so the user knows *which* prior upload they'd be duplicating."""

    page_uuid: _uuid.UUID
    page_index: int
    upload_job_uuid: _uuid.UUID | None
    original_filename: str | None
    source_sha256: str | None
    match_kind: str  # "filename" | "sha256"


@dataclass(frozen=True, kw_only=True, slots=True)
class PrecheckResult:
    """Result of the pre-upload check fired when a user selects a file.

    `filename_matches` is non-empty when the new upload's filename
    matches an earlier upload's filename in this project.
    `project_has_existing_pages` is True when this project already
    has any active Page rows (the 1-book-at-a-time warning trigger).
    Both are warnings, NOT hard blocks. SHA-256 match is checked
    post-upload via `find_sha256_matches` because the server doesn't
    know the content's hash until the upload is assembled.
    """

    filename_matches: tuple[DuplicateMatch, ...]
    project_has_existing_pages: bool


async def precheck_for_project(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    filename: str,
) -> PrecheckResult:
    """Look up filename matches + project-has-pages state for the
    pre-upload modal.

    Filename matching reads the `original_filename` from completed
    upload Jobs in this project — that's where the user-supplied name
    lives. Page-existence is a simple count over active Pages.
    """
    # Filename match: find upload Jobs in this project whose payload
    # has `original_filename` equal to the new filename.
    job_q = await session.execute(
        select(Job).where(Job.project_uuid == project_uuid).where(Job.job_type == "upload")
    )
    filename_matches: list[DuplicateMatch] = []
    matching_job_uuids: set[_uuid.UUID] = set()
    for job in job_q.scalars():
        payload: dict[str, Any] = job.payload or {}
        existing_name = payload.get("original_filename")
        if isinstance(existing_name, str) and existing_name == filename:
            matching_job_uuids.add(job.job_uuid)

    # For each matching job, surface ALL Pages that came from it.
    if matching_job_uuids:
        # Walk SCAN-POs whose `upload_job_uuid` matches.
        for job_uuid in matching_job_uuids:
            po_q = await session.execute(
                select(ProvenanceObject)
                .where(ProvenanceObject.po_type == POType.SCAN.value)
                .where(ProvenanceObject.scope_type == ScopeType.PAGE.value)
            )
            for po in po_q.scalars():
                po_payload: dict[str, Any] = po.payload or {}
                if str(po_payload.get("upload_job_uuid")) != str(job_uuid):
                    continue
                page = await session.get(Page, po.scope_uuid)
                if page is None or page.project_uuid != project_uuid:
                    continue
                filename_matches.append(
                    DuplicateMatch(
                        page_uuid=page.page_uuid,
                        page_index=page.page_index,
                        upload_job_uuid=job_uuid,
                        original_filename=filename,
                        source_sha256=po_payload.get("source_sha256"),
                        match_kind="filename",
                    )
                )

    # Project-has-pages: any active Page in this project.
    page_q = await session.execute(select(Page).where(Page.project_uuid == project_uuid).limit(1))
    project_has_existing_pages = page_q.scalar_one_or_none() is not None

    return PrecheckResult(
        filename_matches=tuple(filename_matches),
        project_has_existing_pages=project_has_existing_pages,
    )


async def find_sha256_matches(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    sha256: str,
    exclude_job_uuid: _uuid.UUID | None = None,
) -> tuple[DuplicateMatch, ...]:
    """Find Pages in `project_uuid` whose SCAN-PO records a
    `source_sha256` equal to `sha256`. Excludes pages from
    `exclude_job_uuid` so the just-completed upload doesn't match
    itself.

    Called post-finalize: the upload service computes the SHA-256
    once at finalize time, then this function reports any prior
    Pages with the same content hash.
    """
    matches: list[DuplicateMatch] = []
    po_q = await session.execute(
        select(ProvenanceObject)
        .where(ProvenanceObject.po_type == POType.SCAN.value)
        .where(ProvenanceObject.scope_type == ScopeType.PAGE.value)
    )
    for po in po_q.scalars():
        payload: dict[str, Any] = po.payload or {}
        if payload.get("source_sha256") != sha256:
            continue
        # Filter to this project.
        page = await session.get(Page, po.scope_uuid)
        if page is None or page.project_uuid != project_uuid:
            continue
        po_job_str = payload.get("upload_job_uuid")
        po_job: _uuid.UUID | None = None
        if isinstance(po_job_str, str):
            try:
                po_job = _uuid.UUID(po_job_str)
            except ValueError:
                po_job = None
        if exclude_job_uuid is not None and po_job == exclude_job_uuid:
            continue
        matches.append(
            DuplicateMatch(
                page_uuid=page.page_uuid,
                page_index=page.page_index,
                upload_job_uuid=po_job,
                original_filename=None,
                source_sha256=sha256,
                match_kind="sha256",
            )
        )
    return tuple(matches)


__all__ = [
    "DuplicateMatch",
    "PrecheckResult",
    "find_sha256_matches",
    "precheck_for_project",
]
