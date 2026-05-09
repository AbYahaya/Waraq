"""T-6.1.1 — extend ocr_error_instances.error_code CHECK with F-06-QR

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-06

Sprint 2 §2 acceptance for T-6.1.1 release gate condition #2:
"F-06-QR error class (Qurʾān-recognition class) has no unresolved instance
anywhere in the project."

F-06-QR is a Qurʾān-recognition error class distinct from the API-side
F-01..F-09 OCR-error vocabulary canonized 2026-05-04. Sprint 2 §B says
"Qurʾān-Stellen-Ausklammerung remains canonical but inert here" — the
detection pipeline that produces F-06-QR rows belongs to §4.15 Stage-3
Qurʾān-recognition (M5 territory). The release gate condition that reads
for unresolved F-06-QR instances ships now, structurally correct against
an empty set; the writer ships later.

Drop and recreate the existing CHECK constraint to include "F-06-QR".
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_F_XX_VALUES = (
    "F-01",
    "F-02",
    "F-03",
    "F-04",
    "F-05",
    "F-06",
    "F-07",
    "F-08",
    "F-09",
    # Qurʾān-recognition class. Read by T-6.1.1 release gate condition #2.
    # Detection writer lands with §4.15 Stage-3 in M5.
    "F-06-QR",
)


def _check_in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    op.drop_constraint("ck_ocr_error_instance_error_code", "ocr_error_instances", type_="check")
    op.create_check_constraint(
        "ck_ocr_error_instance_error_code",
        "ocr_error_instances",
        _check_in("error_code", _F_XX_VALUES),
    )


def downgrade() -> None:
    op.drop_constraint("ck_ocr_error_instance_error_code", "ocr_error_instances", type_="check")
    op.create_check_constraint(
        "ck_ocr_error_instance_error_code",
        "ocr_error_instances",
        _check_in("error_code", _F_XX_VALUES[:-1]),  # drop F-06-QR
    )
