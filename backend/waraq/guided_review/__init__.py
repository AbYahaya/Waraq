"""§2.1 Phase 3 — Guided review (walk through findings systematically).

Canon names the feature without pinning internals. v1.0 ships a deterministic
queue builder that yields unresolved findings in canonical priority order:

  1. P-03 blocking — kritisch audit Befunde, kritisch Konsistenz, kritisch
     OCR-error instances, Hadith H-2 status rows.
  2. P-04 blocking — hoch audit Befunde (Pflichthinweis).
  3. W-01..W-03 warning — mittel audit Befunde, non-kritisch Konsistenz,
     Hadith H-1 status rows.

Within each tier the queue orders by `detected_at` (oldest first) so the
walk is stable across calls. Each item carries the canonical
finding-class identifier the resolver UI needs to dispatch to the
right resolution surface.

This is a READ service — it does not mutate any state. The UI calls
`build_review_queue` to render "next finding", and resolution flows
through the existing per-finding services (audit `quittiere_befund`,
consistency resolver, OCR-review resolver, hadith preflight resolvers).
"""

from waraq.guided_review.service import (
    GuidedReviewItem,
    GuidedReviewItemKind,
    GuidedReviewQueue,
    GuidedReviewTier,
    build_review_queue,
)

__all__ = [
    "GuidedReviewItem",
    "GuidedReviewItemKind",
    "GuidedReviewQueue",
    "GuidedReviewTier",
    "build_review_queue",
]
