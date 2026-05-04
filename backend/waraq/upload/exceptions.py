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
