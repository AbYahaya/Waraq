"""Pydantic request/response models for the HTTP layer.

Naming convention: `<Resource><Action>Request` for inputs, `<Resource>Response`
for outputs. UUIDs surface as strings on the wire (Pydantic handles the
conversion both ways).

These are NOT the SQLAlchemy schemas — they're the API contract. Keep them
narrow: only fields the client actually sends/receives.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# --- Auth ---------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    display_name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_uuid: _uuid.UUID
    email: str
    display_name: str | None
    active: bool


# --- Projects -----------------------------------------------------------


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_uuid: _uuid.UUID
    account_uuid: _uuid.UUID
    name: str
    active: bool


# --- Uploads ------------------------------------------------------------


class UploadStartRequest(BaseModel):
    project_uuid: _uuid.UUID
    original_filename: str = Field(min_length=1, max_length=512)
    total_chunks: int = Field(gt=0)
    total_size_bytes: int = Field(gt=0)


class UploadStartResponse(BaseModel):
    job_uuid: _uuid.UUID
    state: str
    expected_next_chunk: int


class UploadStatusResponse(BaseModel):
    job_uuid: _uuid.UUID
    state: str
    received_chunks: int
    total_chunks: int
    expected_next_chunk: int | None


class UploadFinalizeResponse(BaseModel):
    job_uuid: _uuid.UUID
    state: str
    page_count: int
    page_uuids: list[_uuid.UUID]
    source_sha256: str


# --- OCR ----------------------------------------------------------------


class OcrStartResponse(BaseModel):
    job_uuid: _uuid.UUID
    state: str


class OcrRunResponse(BaseModel):
    job_uuid: _uuid.UUID
    state: str
    text: str
    text_chars: int
    text_changed: bool
    rev_uuid: _uuid.UUID | None


# --- Errors -------------------------------------------------------------


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
    context: dict[str, Any] | None = None
