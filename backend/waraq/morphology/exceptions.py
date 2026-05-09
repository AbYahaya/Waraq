"""Morphology service exceptions.

Two concrete failure modes the HTTP layer must distinguish:

- `MorphologyNotInstalled` — the optional `camel-tools` Python package
  isn't importable in this environment. Server returns HTTP 503 with a
  message indicating the user should `pip install camel-tools` and
  download the morphology DB.

- `MorphologyDataMissing` — `camel-tools` is installed but the morphology
  database file isn't on disk. The user must run `camel_data -i
  morphology-db-msa-r13` (or set CAMELTOOLS_DATA env var). Also surfaces
  as 503.
"""

from __future__ import annotations


class MorphologyError(Exception):
    """Base class for morphology service failures."""


class MorphologyNotInstalled(MorphologyError):
    """`camel-tools` is not importable in this environment."""


class MorphologyDataMissing(MorphologyError):
    """`camel-tools` is importable, but the morphology DB file is missing."""
