"""§3.5 — External-source HTTP utilities (Model U).

`waraq.external` is the home of the canonical Model U request profile
and the Class A / Class B / Class C error mapping per §4.18. Every
external HTTP path (sunnah.com, dorar.net, quranenc.com, Shamela
Mode-A network paths if/when added) routes through `model_u_fetch` so
the conservative-request-profile rules apply uniformly.

Local sources (Tanzil-Hafs ingest, Shamela bulk ingest) are excluded
per §3.5: "Local sources are excluded; Shamela as a local collection
is an explicit exception."
"""

from waraq.external.model_u import (
    DEFAULT_MODEL_U_PROFILE,
    ExternalSourceError,
    JsonFetcher,
    ModelUClassA,
    ModelUClassB,
    ModelURequestProfile,
    model_u_fetch,
)

__all__ = [
    "DEFAULT_MODEL_U_PROFILE",
    "ExternalSourceError",
    "JsonFetcher",
    "ModelUClassA",
    "ModelUClassB",
    "ModelURequestProfile",
    "model_u_fetch",
]
