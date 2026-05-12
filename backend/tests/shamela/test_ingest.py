"""Phase 2E — section-line parser + ingest tests."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.schemas import ShamelaRegistry, ShamelaSection
from waraq.shamela import (
    SectionRow,
    ingest_text,
    parse_section_lines,
    register_text,
)
from waraq.shamela.registry import get_text_spec

_BUKHARI_FIXTURE = """\
# كتاب بدء الوحي
| إنما الأعمال بالنيات
| وإنما لكل امرئ ما نوى

# كتاب الإيمان
| الإسلام أن تشهد أن لا إله إلا الله

| من حسن إسلام المرء تركه ما لا يعنيه
"""


# --- Parser tests ---------------------------------------------------


class TestParseSectionLines:
    def test_parses_two_kitabs_three_sections(self) -> None:
        rows = list(parse_section_lines(_BUKHARI_FIXTURE))
        assert len(rows) == 3

        # First section: kitāb 1.
        assert rows[0].section_path == "كتاب بدء الوحي"
        assert "إنما الأعمال" in rows[0].text_arabic
        assert "ما نوى" in rows[0].text_arabic

        # Second + third sections: kitāb 2.
        assert rows[1].section_path == "كتاب الإيمان"
        assert "الإسلام" in rows[1].text_arabic
        assert rows[2].section_path == "كتاب الإيمان"
        assert "حسن إسلام" in rows[2].text_arabic

    def test_section_indices_monotonic(self) -> None:
        rows = list(parse_section_lines(_BUKHARI_FIXTURE))
        indices = [r.section_index for r in rows]
        assert indices == sorted(indices)
        assert indices[0] == 1

    def test_strips_openiti_markers(self) -> None:
        text = "# كتاب\n| الإسلام @QB@1 أن @QE@1 تشهد"
        rows = list(parse_section_lines(text))
        assert len(rows) == 1
        # OpenITI markers stripped.
        assert "@QB@" not in rows[0].text_arabic
        assert "@QE@" not in rows[0].text_arabic
        # Surrounding text preserved.
        assert "الإسلام" in rows[0].text_arabic
        assert "تشهد" in rows[0].text_arabic

    def test_empty_input_returns_no_rows(self) -> None:
        assert list(parse_section_lines("")) == []
        assert list(parse_section_lines("\n\n\n")) == []

    def test_loose_paragraph_lines_accepted(self) -> None:
        """Lines without a leading `|` are accepted as content too."""
        text = "# كتاب\nالإسلام أن تشهد\n"
        rows = list(parse_section_lines(text))
        assert len(rows) == 1
        assert rows[0].text_arabic.startswith("الإسلام")


# --- Ingest tests ---------------------------------------------------


@pytest.mark.asyncio
class TestRegisterText:
    async def test_first_register_writes_row(self, db_session: AsyncSession) -> None:
        spec = get_text_spec("sahih_bukhari")
        registry = await register_text(
            session=db_session, spec=spec, source_version="phase2e-test-A"
        )
        assert registry.text_slug == "sahih_bukhari"
        assert registry.is_kutub_as_sitta is True
        assert registry.text_type == "hadith"

    async def test_re_register_same_version_idempotent(self, db_session: AsyncSession) -> None:
        spec = get_text_spec("lisan_al_arab")
        first = await register_text(session=db_session, spec=spec, source_version="phase2e-test-A")
        second = await register_text(session=db_session, spec=spec, source_version="phase2e-test-A")
        assert first.text_slug == second.text_slug
        # Single registry row only.
        rows = list(
            (
                await db_session.execute(
                    select(ShamelaRegistry)
                    .where(ShamelaRegistry.text_slug == "lisan_al_arab")
                    .where(ShamelaRegistry.source_version == "phase2e-test-A")
                )
            ).scalars()
        )
        assert len(rows) == 1


@pytest.mark.asyncio
class TestIngestText:
    async def test_initial_ingest_writes_sections(self, db_session: AsyncSession) -> None:
        sections = list(parse_section_lines(_BUKHARI_FIXTURE))
        result = await ingest_text(
            session=db_session,
            text_slug="sahih_bukhari",
            source_version="phase2e-test-A",
            sections=sections,
        )
        assert result.inserted_count == 3
        assert result.updated_count == 0

        rows = list(
            (
                await db_session.execute(
                    select(ShamelaSection)
                    .where(ShamelaSection.text_slug == "sahih_bukhari")
                    .where(ShamelaSection.source_version == "phase2e-test-A")
                )
            ).scalars()
        )
        assert len(rows) == 3
        # Skeleton derived (no diacritics).
        first = rows[0]
        assert "ِ" not in first.text_skeleton

    async def test_unknown_slug_raises(self, db_session: AsyncSession) -> None:
        with pytest.raises(KeyError, match="unknown text_slug"):
            await ingest_text(
                session=db_session,
                text_slug="unknown_text",
                source_version="phase2e-test-A",
                sections=[],
            )

    async def test_re_ingest_same_version_with_change_updates_in_place(
        self, db_session: AsyncSession
    ) -> None:
        sections = list(parse_section_lines(_BUKHARI_FIXTURE))
        await ingest_text(
            session=db_session,
            text_slug="sahih_bukhari",
            source_version="phase2e-test-A",
            sections=sections,
        )

        modified = [
            SectionRow(
                section_index=s.section_index,
                section_path=s.section_path,
                text_arabic=(
                    s.text_arabic + " — corrected" if s.section_index == 2 else s.text_arabic
                ),
                metadata=s.metadata,
            )
            for s in sections
        ]
        result = await ingest_text(
            session=db_session,
            text_slug="sahih_bukhari",
            source_version="phase2e-test-A",
            sections=modified,
        )
        assert result.inserted_count == 0
        assert result.updated_count == 1

    async def test_new_version_supersedes_old(self, db_session: AsyncSession) -> None:
        sections = list(parse_section_lines(_BUKHARI_FIXTURE))
        await ingest_text(
            session=db_session,
            text_slug="sahih_bukhari",
            source_version="phase2e-test-A",
            sections=sections,
        )
        result = await ingest_text(
            session=db_session,
            text_slug="sahih_bukhari",
            source_version="phase2e-test-B",
            sections=sections,
        )
        assert result.inserted_count == 3
        # Both registry rows exist for THIS test's two source_versions;
        # filter on those versions so a real-corpus ingest under the same
        # text_slug (e.g. interactive `fetch_openiti.py` runs against the
        # dev DB) doesn't pollute the assertion.
        test_versions = {"phase2e-test-A", "phase2e-test-B"}
        registries = list(
            (
                await db_session.execute(
                    select(ShamelaRegistry)
                    .where(ShamelaRegistry.text_slug == "sahih_bukhari")
                    .where(ShamelaRegistry.source_version.in_(test_versions))
                )
            ).scalars()
        )
        assert len(registries) == 2
        active = [r for r in registries if r.active]
        inactive = [r for r in registries if not r.active]
        assert len(active) == 1
        assert active[0].source_version == "phase2e-test-B"
        assert len(inactive) == 1
        assert inactive[0].source_version == "phase2e-test-A"

    async def test_duplicate_section_index_in_input_rejected(
        self, db_session: AsyncSession
    ) -> None:
        dup = [
            SectionRow(section_index=1, section_path="k", text_arabic="x", metadata={}),
            SectionRow(section_index=1, section_path="k", text_arabic="y", metadata={}),
        ]
        with pytest.raises(ValueError, match="duplicate section_index"):
            await ingest_text(
                session=db_session,
                text_slug="sahih_bukhari",
                source_version="phase2e-test-A",
                sections=dup,
            )
