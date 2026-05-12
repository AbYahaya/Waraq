"""Sub-batch N — Project Audit Dashboard (out-of-phase, 2026-05-12).

Read-only aggregation surface over existing canon data:
- Page `ocr_status` distribution
- OCR-PO confidence_class distribution + engine_agreement counts
- TRANSLATION-PO cross_check.situation distribution
- Open audit Befunde counts (by severity)
- Open consistency Befunde counts
- Open conflict_instances count

Pure aggregation — NO new domain concepts, NO new write paths. Decisions
on flagged items continue to go through the existing canonical paths
(OCR-Review, segment lock-management, audit resolution). The dashboard
links to those surfaces; it does not duplicate them. This is what kept
it out of §2.6 CR-cycle territory.
"""

from waraq.audit_dashboard.service import (
    AttentionFilter,
    AttentionItem,
    BefundDetail,
    ConfidenceDistribution,
    CrossCheckDistribution,
    EngineReading,
    OcrStatusDistribution,
    ProjectAuditSummary,
    SegmentAuditDetail,
    list_attention_segments,
    segment_audit_detail,
    summarize_project,
)

__all__ = [
    "AttentionFilter",
    "AttentionItem",
    "BefundDetail",
    "ConfidenceDistribution",
    "CrossCheckDistribution",
    "EngineReading",
    "OcrStatusDistribution",
    "ProjectAuditSummary",
    "SegmentAuditDetail",
    "list_attention_segments",
    "segment_audit_detail",
    "summarize_project",
]
