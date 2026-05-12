"""Convert OpenITI `.mARkdown` content to the section-line format
the existing `waraq.shamela.ingest.parse_section_lines` consumes.

OpenITI mARkdown shape (anchors observed in the v1.0 canonical-floor
texts: Bukhari, Muslim, Abu Dawud, Tirmidhi, Nasāʾī, Mālik, Ibn Mājah,
Lisān al-ʿArab, Tāj al-ʿArūs, Qāmūs al-Muḥīṭ):

  - First line is the magic `######OpenITI#`.
  - Header block: zero or more `#META#` lines, terminated by the
    sentinel `#META#Header#End#`.
  - Body:
      `### | <text>`     — kitāb-level heading (level 1).
      `### || <text>`    — bāb-level heading (level 2; nested under
                           the most recent kitāb).
      `### ||| <text>`   — sub-bāb (rare; collapsed into bāb level).
      `# <text>`         — paragraph / hadith content line.
      `~~<continuation>` — soft line-wrap for the previous line.
      Inline structural markers we strip:
          `@QB@.../@QE@`    — Qurʾān quotation start/end (kept content).
          `@HUB@`           — hadith-unit boundary.
          `@FOOT@.../@FOOTNOTE@` — footnote markers.
          `@TQB@.../@TQE@`  — text-quotation markers.
          `@RWY@`           — riwāya marker.
          `@MILESTONE@`     — section milestone.
          `PageV<vol>P<page>` — page anchors.
          `\\ <num> \\`     — hadith number annotations.
          `*` (paragraph-internal) — hadith-text marker.

The output uses the canonical section-line format the v1.0 ingest
expects:

  # <heading>
  | <content>
  blank line                ← section separator

The existing `parse_section_lines` then folds those into
`SectionRow`s.  Heading nesting is flattened to a single-`#` line
because `parse_section_lines` only tracks one current heading scope.
A deeper hierarchy can be re-introduced when the consumers actually
need the kitāb/bāb distinction; v1.0 lookup only cares about
`section_path` as a sortable identifier and `text_arabic` as the
matchable content.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

# --- Module-internal regexes -------------------------------------------

# Header sentinel — everything before this line is metadata, skipped.
_HEADER_END_SENTINEL: str = "#META#Header#End#"

# Heading lines.
_KITAB_HEADING_RE = re.compile(r"^###\s*\|\s*(.+?)\s*$")
_BAB_HEADING_RE = re.compile(r"^###\s*\|\|+\s*(.+?)\s*$")

# Page anchor: `PageV01P003` style, may appear mid-line.
_PAGE_MARKER_RE = re.compile(r"PageV\d+P\d+")

# Hadith-number annotation: `\ 1 \` style.
_HADITH_NUMBER_RE = re.compile(r"\\\s*\d+\s*\\")

# `@TAG@` markers we strip whole. Some carry a numeric suffix (e.g.
# `@FOOT@123`); the `(?:\d+)?` covers both forms.
_TAG_MARKER_RE = re.compile(r"@(?:QB|QE|HUB|HE|TQB|TQE|YQB|YQE|RWY|MILESTONE|FOOT|FOOTNOTE)@\d*")

# Hadith-text marker (`*`) at line start or after whitespace. We strip
# the marker but keep the surrounding text content.
_HADITH_TEXT_MARKER_RE = re.compile(r"(?:^|\s)\*\s")


def _strip_inline_markers(text: str) -> str:
    """Strip every OpenITI inline marker we know about from `text`."""
    text = _PAGE_MARKER_RE.sub(" ", text)
    text = _HADITH_NUMBER_RE.sub(" ", text)
    text = _TAG_MARKER_RE.sub(" ", text)
    text = _HADITH_TEXT_MARKER_RE.sub(" ", text)
    # Collapse multiple spaces to one.
    return " ".join(text.split())


def openiti_markdown_to_section_lines(content: str) -> str:
    """Translate OpenITI `.mARkdown` content into the canonical
    section-line format `parse_section_lines` consumes.

    Behavior:
        - Skip the magic `######OpenITI#` line.
        - Skip every `#META#...` line up to and including
          `#META#Header#End#`.
        - For every body line: classify (kitāb / bāb / continuation /
          paragraph), strip inline markers, and emit:
              `# <heading>` for headings,
              `| <content>` for paragraph content,
              blank lines after each completed paragraph (so
              `parse_section_lines` cuts sections cleanly).

    Continuation lines (`~~...`) are appended to the most recent
    paragraph buffer. A new heading or a non-continuation paragraph
    flushes the buffer.
    """
    return "\n".join(_iter_section_lines(content))


def _iter_section_lines(content: str) -> Iterator[str]:
    in_header = True
    pending_paragraph: list[str] = []

    def _flush_paragraph() -> Iterator[str]:
        if pending_paragraph:
            joined = _strip_inline_markers(" ".join(pending_paragraph))
            if joined:
                yield "| " + joined
                yield ""  # blank line = section separator
            pending_paragraph.clear()

    for raw in content.splitlines():
        line = raw.rstrip()

        # Skip the magic line.
        if line.startswith("######OpenITI"):
            continue

        # Header phase — skip until sentinel.
        if in_header:
            if line.strip() == _HEADER_END_SENTINEL:
                in_header = False
            continue

        # Drop any trailing-empty / whitespace-only lines that aren't
        # paragraph-buffered. (Within a paragraph, blanks act as
        # boundaries — we flush.)
        if not line:
            yield from _flush_paragraph()
            continue

        # Continuation line (soft wrap).
        if line.startswith("~~"):
            pending_paragraph.append(line[2:].strip())
            continue

        # Headings — order matters (more `|`s wins; check bāb before
        # kitāb because bāb is a strict superset of the kitāb pattern).
        bab = _BAB_HEADING_RE.match(line)
        if bab:
            yield from _flush_paragraph()
            heading = _strip_inline_markers(bab.group(1))
            if heading:
                yield "# " + heading
            continue

        kitab = _KITAB_HEADING_RE.match(line)
        if kitab:
            yield from _flush_paragraph()
            heading = _strip_inline_markers(kitab.group(1))
            if heading:
                yield "# " + heading
            continue

        # Paragraph / content line. The body convention is leading `#`.
        if line.startswith("#"):
            # Flush any prior paragraph BEFORE starting a new one
            # (each leading-`#` line is a new logical paragraph head).
            yield from _flush_paragraph()
            stripped = line.lstrip("#").strip()
            if stripped:
                pending_paragraph.append(stripped)
            continue

        # Loose line — accept as continuation of the current paragraph.
        pending_paragraph.append(line)

    yield from _flush_paragraph()


__all__ = ["openiti_markdown_to_section_lines"]
