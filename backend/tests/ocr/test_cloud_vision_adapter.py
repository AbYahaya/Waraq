"""Phase 4 sub-batch C — Cloud Vision adapter unit tests.

Two layers covered:

1. `CloudVisionResult` dataclass shape — text + averaged confidence.
2. `extract_with_confidence` SDK call:
   - Auth-failure path raises `MissingCloudVisionCredentials`.
   - API-error path raises `CloudVisionApiError`.
   - Confidence aggregation rule (mean of `pages[*].confidence`).

The real Cloud Vision SDK is monkey-patched at the import-site that
`extract_with_confidence` does its lazy imports through. No live
calls are made — this is hermetic.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass

import pytest

from waraq.ocr.cloud_vision import (
    CloudVisionApiError,
    CloudVisionResult,
    MissingCloudVisionCredentials,
    extract_with_confidence,
)


@dataclass
class _FakePage:
    confidence: float | None


class _FakeFullText:
    def __init__(self, text: str, pages: list[_FakePage]) -> None:
        self.text = text
        self.pages = pages


class _FakeError:
    def __init__(self, message: str = "") -> None:
        self.message = message


class _FakeResponse:
    def __init__(self, *, full_text: _FakeFullText | None, error_message: str = "") -> None:
        self.full_text_annotation = full_text
        self.error = _FakeError(error_message)


def _install_fake_vision_sdk(
    monkeypatch: pytest.MonkeyPatch,
    *,
    response: _FakeResponse | None = None,
    raise_on_call: BaseException | None = None,
    raise_on_construct: BaseException | None = None,
    raise_perm_denied: bool = False,
) -> dict[str, list[bytes]]:
    """Stub the lazy-imported google modules.

    Returns a dict tracking calls so tests can assert what was sent.
    """
    captured: dict[str, list[bytes]] = {"image_bytes": []}

    # google.cloud.vision module
    vision = types.ModuleType("google.cloud.vision")

    class _ImageAnnotatorClient:
        def __init__(self) -> None:
            if raise_on_construct is not None:
                raise raise_on_construct

        def document_text_detection(self, *, image, timeout: float = 20.0):  # type: ignore[no-untyped-def]
            captured["image_bytes"].append(image.content)
            if raise_perm_denied:
                # PermissionDenied gets handled separately from generic
                # SDK exceptions.
                from google.api_core import exceptions as gcp_exceptions

                raise gcp_exceptions.PermissionDenied("nope")
            if raise_on_call is not None:
                raise raise_on_call
            return response

    class _Image:
        def __init__(self, *, content: bytes) -> None:
            self.content = content

    vision.ImageAnnotatorClient = _ImageAnnotatorClient  # type: ignore[attr-defined]
    vision.Image = _Image  # type: ignore[attr-defined]

    google_cloud = types.ModuleType("google.cloud")
    google_cloud.vision = vision  # type: ignore[attr-defined]

    # google.api_core.exceptions module
    api_core_exc = types.ModuleType("google.api_core.exceptions")

    class _PermissionDenied(Exception):
        pass

    api_core_exc.PermissionDenied = _PermissionDenied  # type: ignore[attr-defined]
    api_core = types.ModuleType("google.api_core")
    api_core.exceptions = api_core_exc  # type: ignore[attr-defined]

    # google.auth.exceptions module
    auth_exc = types.ModuleType("google.auth.exceptions")

    class _DefaultCredentialsError(Exception):
        pass

    auth_exc.DefaultCredentialsError = _DefaultCredentialsError  # type: ignore[attr-defined]
    auth = types.ModuleType("google.auth")
    auth.exceptions = auth_exc  # type: ignore[attr-defined]

    google_pkg = types.ModuleType("google")
    google_pkg.cloud = google_cloud  # type: ignore[attr-defined]
    google_pkg.api_core = api_core  # type: ignore[attr-defined]
    google_pkg.auth = auth  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "google", google_pkg)
    monkeypatch.setitem(sys.modules, "google.cloud", google_cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.vision", vision)
    monkeypatch.setitem(sys.modules, "google.api_core", api_core)
    monkeypatch.setitem(sys.modules, "google.api_core.exceptions", api_core_exc)
    monkeypatch.setitem(sys.modules, "google.auth", auth)
    monkeypatch.setitem(sys.modules, "google.auth.exceptions", auth_exc)
    return captured


@pytest.mark.asyncio
class TestExtractWithConfidence:
    async def test_returns_text_and_mean_confidence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        full = _FakeFullText(
            text="بسم الله\n",
            pages=[_FakePage(confidence=0.90), _FakePage(confidence=0.80)],
        )
        captured = _install_fake_vision_sdk(monkeypatch, response=_FakeResponse(full_text=full))

        result = await extract_with_confidence(b"image-bytes", "image/png")

        assert isinstance(result, CloudVisionResult)
        assert result.text == "بسم الله"  # stripped
        assert result.confidence == pytest.approx(0.85)  # (0.9+0.8)/2
        assert captured["image_bytes"] == [b"image-bytes"]

    async def test_returns_none_confidence_when_pages_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        full = _FakeFullText(text="x", pages=[])
        _install_fake_vision_sdk(monkeypatch, response=_FakeResponse(full_text=full))
        result = await extract_with_confidence(b"image", "image/png")
        assert result.confidence is None
        assert result.text == "x"

    async def test_returns_empty_text_when_full_text_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_fake_vision_sdk(monkeypatch, response=_FakeResponse(full_text=None))
        result = await extract_with_confidence(b"image", "image/png")
        assert result.text == ""
        assert result.confidence is None

    async def test_response_error_message_raises_api_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_fake_vision_sdk(
            monkeypatch,
            response=_FakeResponse(full_text=None, error_message="quota exceeded"),
        )
        with pytest.raises(CloudVisionApiError):
            await extract_with_confidence(b"image", "image/png")

    async def test_permission_denied_raises_credential_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_fake_vision_sdk(monkeypatch, response=None, raise_perm_denied=True)
        with pytest.raises(MissingCloudVisionCredentials):
            await extract_with_confidence(b"image", "image/png")

    async def test_default_credentials_error_raises_credential_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Construct-time DefaultCredentialsError flows through the
        # except branch and surfaces as MissingCloudVisionCredentials.
        # We install the SDK first, grab the installed class, and pass
        # an instance of *that* class as the construct-time error so
        # the `except DefaultCredentialsError` in cloud_vision.py
        # catches a class identity it actually imports.
        _install_fake_vision_sdk(monkeypatch, response=None)
        dce_cls = sys.modules["google.auth.exceptions"].DefaultCredentialsError

        def _construct_raises(self) -> None:  # type: ignore[no-untyped-def]
            raise dce_cls("no creds")

        vision_mod = sys.modules["google.cloud.vision"]
        monkeypatch.setattr(vision_mod.ImageAnnotatorClient, "__init__", _construct_raises)

        with pytest.raises(MissingCloudVisionCredentials):
            await extract_with_confidence(b"image", "image/png")

    async def test_other_sdk_exception_wrapped_as_api_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_fake_vision_sdk(
            monkeypatch,
            response=None,
            raise_on_call=RuntimeError("transient network blip"),
        )
        with pytest.raises(CloudVisionApiError) as ei:
            await extract_with_confidence(b"image", "image/png")
        assert isinstance(ei.value.cause, RuntimeError)
