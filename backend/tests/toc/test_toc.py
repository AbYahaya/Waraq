"""Phase 3 sub-batch E — §2.1 TOC handling tests."""

from __future__ import annotations

import uuid as _uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project
from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag
from waraq.schemas import Block, Page, Segment
from waraq.schemas.enums import OcrStatus
from waraq.toc import (
    HEADING_BLOCK_TYPES,
    TocFallbackKind,
    detect_toc,
    edit_toc_entry_heading,
)


async def _seed_page_with_block(
    session: AsyncSession,
    *,
    project,
    page_index: int,
    block_type: str,
    text: str,
) -> tuple[Page, Block, Segment]:
    page = Page(
        page_uuid=new_uuid(),
        project_uuid=project.project_uuid,
        page_index=page_index,
        ocr_status=OcrStatus.GO,
    )
    session.add(page)
    await session.flush()
    block = Block(
        block_uuid=new_uuid(),
        page_uuid=page.page_uuid,
        block_type=block_type,
        block_index=0,
    )
    session.add(block)
    await session.flush()
    segment = Segment(
        satz_uuid=new_uuid(),
        block_uuid=block.block_uuid,
        satz_index=0,
        lock_flag=LockFlag.NONE,
        text_content=text,
    )
    session.add(segment)
    await session.flush()
    return page, block, segment


@pytest.mark.asyncio
class TestNoTocFallback:
    async def test_empty_project_zero_entries(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        result = await detect_toc(session=db_session, project_uuid=project.project_uuid)
        assert result.entries == []
        assert result.fallback_kind == TocFallbackKind.PAGE_BY_PAGE
        assert result.detected_heading_count == 0
        assert result.page_count == 0

    async def test_pages_without_headings_yield_page_by_page_fallback(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        await _seed_page_with_block(
            db_session, project=project, page_index=1, block_type="MT", text="body"
        )
        await _seed_page_with_block(
            db_session, project=project, page_index=2, block_type="MT", text="more body"
        )
        result = await detect_toc(session=db_session, project_uuid=project.project_uuid)
        assert result.fallback_kind == TocFallbackKind.PAGE_BY_PAGE
        assert result.detected_heading_count == 0
        assert result.page_count == 2
        assert len(result.entries) == 2
        # Fallback entries lack a real segment.
        assert all(e.satz_uuid is None and e.block_uuid is None for e in result.entries)
        assert result.entries[0].page_index == 1
        assert result.entries[1].page_index == 2


@pytest.mark.asyncio
class TestDetection:
    async def test_ue_block_detected_as_level_1(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        page, block, seg = await _seed_page_with_block(
            db_session,
            project=project,
            page_index=3,
            block_type="UE",
            text="مقدمة\n---\nEinleitung",
        )
        result = await detect_toc(session=db_session, project_uuid=project.project_uuid)
        assert result.fallback_kind == TocFallbackKind.NONE
        assert result.detected_heading_count == 1
        assert len(result.entries) == 1
        e = result.entries[0]
        assert e.level == 1
        assert e.satz_uuid == seg.satz_uuid
        assert e.block_uuid == block.block_uuid
        assert e.page_index == page.page_index
        assert e.ar_text == "مقدمة"
        assert e.de_text == "Einleitung"

    async def test_hd_block_detected_as_level_2(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        await _seed_page_with_block(
            db_session,
            project=project,
            page_index=4,
            block_type="HD",
            text="فصل أول\n---\nKapitel 1",
        )
        result = await detect_toc(session=db_session, project_uuid=project.project_uuid)
        assert len(result.entries) == 1
        assert result.entries[0].level == 2

    async def test_mixed_levels_ordered_by_page_then_block(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        # Seed in non-canonical order; result must be page-asc.
        await _seed_page_with_block(
            db_session, project=project, page_index=2, block_type="HD", text="b\n---\nB"
        )
        await _seed_page_with_block(
            db_session, project=project, page_index=1, block_type="UE", text="a\n---\nA"
        )
        result = await detect_toc(session=db_session, project_uuid=project.project_uuid)
        assert [e.page_index for e in result.entries] == [1, 2]
        assert HEADING_BLOCK_TYPES["UE"] == 1
        assert HEADING_BLOCK_TYPES["HD"] == 2

    async def test_segment_without_separator_treated_as_ar_only(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        await _seed_page_with_block(
            db_session, project=project, page_index=1, block_type="UE", text="عنوان"
        )
        result = await detect_toc(session=db_session, project_uuid=project.project_uuid)
        e = result.entries[0]
        assert e.ar_text == "عنوان"
        assert e.de_text == ""

    async def test_other_project_excluded(self, db_session: AsyncSession) -> None:
        a = await seed_project(db_session, name="A")
        b = await seed_project(db_session, name="B")
        await _seed_page_with_block(
            db_session, project=a, page_index=1, block_type="UE", text="X\n---\nY"
        )
        result_b = await detect_toc(session=db_session, project_uuid=b.project_uuid)
        assert result_b.detected_heading_count == 0


@pytest.mark.asyncio
class TestEdit:
    async def test_edit_ar_only_preserves_de(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        _page, _block, seg = await _seed_page_with_block(
            db_session,
            project=project,
            page_index=1,
            block_type="UE",
            text="old-ar\n---\nold-de",
        )
        rev = await edit_toc_entry_heading(
            session=db_session, satz_uuid=seg.satz_uuid, new_ar_text="new-ar"
        )
        assert rev.after_text == "new-ar\n---\nold-de"
        await db_session.refresh(seg)
        assert seg.text_content == "new-ar\n---\nold-de"

    async def test_edit_de_only_preserves_ar(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        _p, _b, seg = await _seed_page_with_block(
            db_session,
            project=project,
            page_index=1,
            block_type="UE",
            text="ar\n---\nold-de",
        )
        rev = await edit_toc_entry_heading(
            session=db_session, satz_uuid=seg.satz_uuid, new_de_text="new-de"
        )
        assert rev.after_text == "ar\n---\nnew-de"

    async def test_edit_both_at_once(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        _p, _b, seg = await _seed_page_with_block(
            db_session,
            project=project,
            page_index=1,
            block_type="UE",
            text="x\n---\ny",
        )
        rev = await edit_toc_entry_heading(
            session=db_session,
            satz_uuid=seg.satz_uuid,
            new_ar_text="aaa",
            new_de_text="bbb",
        )
        assert rev.after_text == "aaa\n---\nbbb"

    async def test_edit_neither_raises(self, db_session: AsyncSession) -> None:
        with pytest.raises(ValueError):
            await edit_toc_entry_heading(session=db_session, satz_uuid=_uuid.uuid4())

    async def test_edit_unknown_satz_uuid_raises(self, db_session: AsyncSession) -> None:
        with pytest.raises(LookupError):
            await edit_toc_entry_heading(
                session=db_session, satz_uuid=_uuid.uuid4(), new_ar_text="x"
            )
