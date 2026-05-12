"""Upload service exceptions."""

from __future__ import annotations


class UploadError(Exception):
    """Base for upload-pipeline errors."""


class ChunkOutOfOrder(UploadError):
    """Caller sent chunk N when chunk M was expected next."""

    def __init__(self, *, expected: int, received: int) -> None:
        super().__init__(f"Expected chunk {expected}, received chunk {received}")
        self.expected = expected
        self.received = received


class IncompleteUpload(UploadError):
    """finalize_upload called before all chunks were received."""

    def __init__(self, *, received: int, total: int) -> None:
        super().__init__(f"Upload incomplete: {received}/{total} chunks received")
        self.received = received
        self.total = total


class UploadSizeMismatch(UploadError):
    """Total bytes on disk differ from the size declared at start_upload."""

    def __init__(self, *, declared: int, actual: int) -> None:
        super().__init__(f"Declared {declared} bytes, got {actual} bytes")
        self.declared = declared
        self.actual = actual


class UploadNotFound(UploadError):
    """get_upload_status was called with a job_uuid that doesn't exist or
    isn't an upload job."""

    def __init__(self, *, job_uuid: object) -> None:
        super().__init__(f"No upload Job found for job_uuid={job_uuid}")
        self.job_uuid = job_uuid


class UploadTooLarge(UploadError):
    """Upload exceeds the canon §2.1 2 GB maximum. Raised at `start_upload`
    when the declared total exceeds the limit, and defensively at
    `append_chunk` if the cumulative bytes-on-disk exceed it (defends
    against a client that lied about `total_size_bytes`). The upload
    router surfaces as HTTP 413 Payload Too Large."""

    def __init__(self, *, size_bytes: int, max_bytes: int) -> None:
        super().__init__(
            f"Upload size {size_bytes} bytes exceeds the {max_bytes}-byte "
            "(canon §2.1 2 GB) maximum."
        )
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes
