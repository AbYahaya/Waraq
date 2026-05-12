"""Phase 4 sub-batch B' — OpenITI mARkdown preprocessor tests.

Round-trip: OpenITI `.mARkdown` → section-line → parsed `SectionRow`s.
The preprocessor must:

  - Strip the `######OpenITI` magic line.
  - Skip the `#META#...` block until `#META#Header#End#`.
  - Recognize `### |` as kitāb-level heading and `### ||` as bāb-level.
  - Recognize `# <text>` (single `#`) as paragraph content.
  - Append `~~<text>` continuation lines to the most recent paragraph.
  - Strip inline markers: `@QB@/@QE@`, `@HUB@`, `@FOOT@`, `*` hadith
    marker, page anchors `PageVxxPxxx`, hadith-number `\\ N \\`.
  - Emit blank-line section separators between paragraphs.
"""

from __future__ import annotations

from waraq.shamela import openiti_markdown_to_section_lines, parse_section_lines


def _rows(content: str) -> list[tuple[str, str]]:
    """Run the full preprocessing+parse pipeline; return (section_path, text)."""
    return [
        (row.section_path, row.text_arabic)
        for row in parse_section_lines(openiti_markdown_to_section_lines(content))
    ]


class TestHeaderHandling:
    def test_meta_block_skipped(self) -> None:
        content = (
            "######OpenITI#\n"
            "#META# 010.AuthorAKA :: Bukhari\n"
            "#META# 020.BookTITLE :: Sahih\n"
            "#META#Header#End#\n"
            "\n"
            "# يقول الراوي\n"
        )
        rows = _rows(content)
        # Only the body paragraph should land — meta lines yielded
        # nothing.
        assert rows == [("", "يقول الراوي")]

    def test_no_magic_no_meta_still_works(self) -> None:
        # A test fixture without the magic prefix — preprocessor must
        # still hit the `#META#Header#End#` sentinel before a body line.
        content = "#META#Header#End#\n# plain content\n"
        rows = _rows(content)
        assert rows == [("", "plain content")]


class TestHeadingClassification:
    def test_kitab_heading(self) -> None:
        content = "#META#Header#End#\n### | كتاب الإيمان\n# content one\n"
        rows = _rows(content)
        assert rows == [("كتاب الإيمان", "content one")]

    def test_bab_heading_overrides_kitab(self) -> None:
        content = "#META#Header#End#\n### | كتاب الإيمان\n### || باب البيعة\n# hadith one\n"
        rows = _rows(content)
        # parse_section_lines tracks one heading scope; bāb wins.
        assert rows == [("باب البيعة", "hadith one")]


class TestContinuationsAndMarkers:
    def test_continuation_appends_to_paragraph(self) -> None:
        content = "#META#Header#End#\n# line one\n~~line two continuation\n"
        rows = _rows(content)
        assert rows == [("", "line one line two continuation")]

    def test_hadith_number_marker_stripped(self) -> None:
        content = "#META#Header#End#\n# hadith content \\ 42 \\\n"
        rows = _rows(content)
        assert rows == [("", "hadith content")]

    def test_page_anchor_stripped(self) -> None:
        content = "#META#Header#End#\n# before PageV01P003 after\n"
        rows = _rows(content)
        assert rows == [("", "before after")]

    def test_quran_quotation_markers_stripped(self) -> None:
        content = "#META#Header#End#\n# قال @QB@ إنا أنزلناه @QE@ لقوم\n"
        rows = _rows(content)
        assert rows == [("", "قال إنا أنزلناه لقوم")]

    def test_asterisk_hadith_marker_stripped(self) -> None:
        content = "#META#Header#End#\n# قال * إنما الأعمال بالنيات\n"
        rows = _rows(content)
        assert rows == [("", "قال إنما الأعمال بالنيات")]

    def test_multiple_paragraphs_kept_separate(self) -> None:
        content = (
            "#META#Header#End#\n# hadith one\n~~continuation of one\n# hadith two\n# hadith three\n"
        )
        rows = _rows(content)
        assert rows == [
            ("", "hadith one continuation of one"),
            ("", "hadith two"),
            ("", "hadith three"),
        ]


class TestRealisticBukhariSample:
    def test_round_trip_on_realistic_excerpt(self) -> None:
        # Mirror of the actual Bukhari mARkdown shape (probed
        # 2026-05-10 against OpenITI/0275AH).
        content = (
            "######OpenITI#\n"
            "\n"
            "#META# 010.AuthorAKA :: البخاري\n"
            "#META# 020.BookTITLE :: الجامع الصحيح المختصر\n"
            "#META#Header#End#\n"
            "\n"
            "# صحيح البخاري PageV01P001 بسم الله الرحمن الرحيم\n"
            "### | ( باب بدء الوحي )\n"
            "### || ( 1 باب كيف كان بدء الوحي إلى رسول الله )\n"
            "# 1 حدثنا الحميدي * إنما الأعمال بالنيات وإنما لكل\n"
            "~~امرئ ما نوى \\ 1 \\\n"
            "# 2 حدثنا عبد الله بن يوسف عن مالك @QB@ إنا أوحينا @QE@ هكذا\n"
        )
        rows = _rows(content)

        assert len(rows) == 3
        # First paragraph (before any heading) — section_path empty.
        assert rows[0][0] == ""
        assert "بسم الله الرحمن الرحيم" in rows[0][1]
        assert "PageV01P001" not in rows[0][1]
        # Second + third paragraphs sit under the bāb heading.
        assert rows[1][0] == "( 1 باب كيف كان بدء الوحي إلى رسول الله )"
        assert "إنما الأعمال بالنيات" in rows[1][1]
        assert "ما نوى" in rows[1][1]
        # Hadith number stripped.
        assert "\\" not in rows[1][1]
        assert "* " not in rows[1][1]
        # Quran quotation kept as content; markers stripped.
        assert rows[2][0] == "( 1 باب كيف كان بدء الوحي إلى رسول الله )"
        assert "إنا أوحينا" in rows[2][1]
        assert "@QB@" not in rows[2][1]
        assert "@QE@" not in rows[2][1]
