"""Deterministic line-tag protocol for translation runs.

This module protects full-page translations from silent truncation and
protects pagination/header marker lines from being translated or dropped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

LineKind = Literal["text", "marker", "blank"]
_TAG_RE = re.compile(r"\[\[(L\d{4})\]\]")


@dataclass(frozen=True, slots=True)
class TaggedLine:
    tag: str
    source_text: str
    kind: LineKind


@dataclass(frozen=True, slots=True)
class TaggedTranslationInput:
    lines: tuple[TaggedLine, ...]
    prompt_text: str


def is_pagination_or_marker_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    normalized = stripped.replace(" ", "")
    if normalized.isdigit():
        return True
    if normalized.startswith("[") and normalized.endswith("]") and normalized[1:-1].isdigit():
        return True
    return normalized.startswith("(") and normalized.endswith(")") and normalized[1:-1].isdigit()


def build_tagged_translation_input(source_text: str) -> TaggedTranslationInput:
    raw_lines = source_text.split("\n")
    tagged_lines: list[TaggedLine] = []
    rendered_lines: list[str] = []
    for idx, raw_line in enumerate(raw_lines, start=1):
        tag = f"L{idx:04d}"
        if raw_line == "":
            kind: LineKind = "blank"
            rendered = f"[[{tag}]] <BLANK_LINE>"
        elif is_pagination_or_marker_text(raw_line):
            kind = "marker"
            rendered = f"[[{tag}]] {raw_line}"
        else:
            kind = "text"
            rendered = f"[[{tag}]] {raw_line}"
        tagged_lines.append(TaggedLine(tag=tag, source_text=raw_line, kind=kind))
        rendered_lines.append(rendered)
    return TaggedTranslationInput(lines=tuple(tagged_lines), prompt_text="\n".join(rendered_lines))


def split_tagged_translation_input(
    tagged: TaggedTranslationInput,
    *,
    max_lines: int = 20,
    max_chars: int = 2500,
) -> list[TaggedTranslationInput]:
    if not tagged.lines:
        return [tagged]

    batches: list[TaggedTranslationInput] = []
    current_lines: list[TaggedLine] = []
    current_rendered: list[str] = []
    current_chars = 0

    for line in tagged.lines:
        rendered = (
            f"[[{line.tag}]] <BLANK_LINE>"
            if line.kind == "blank"
            else f"[[{line.tag}]] {line.source_text}"
        )
        projected_chars = current_chars + len(rendered) + (1 if current_rendered else 0)
        if current_lines and (len(current_lines) >= max_lines or projected_chars > max_chars):
            batches.append(
                TaggedTranslationInput(
                    lines=tuple(current_lines),
                    prompt_text="\n".join(current_rendered),
                )
            )
            current_lines = []
            current_rendered = []
            current_chars = 0

        current_lines.append(line)
        current_rendered.append(rendered)
        current_chars += len(rendered) + (1 if current_rendered[:-1] else 0)

    if current_lines:
        batches.append(
            TaggedTranslationInput(
                lines=tuple(current_lines),
                prompt_text="\n".join(current_rendered),
            )
        )
    return batches


def parse_tagged_translation_output(output_text: str, tagged: TaggedTranslationInput) -> list[str]:
    matches = list(_TAG_RE.finditer(output_text))
    if not matches:
        raise ValueError("translation output missing line tags")

    by_tag: dict[str, str] = {}
    for i, match in enumerate(matches):
        tag = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(output_text)
        content = output_text[start:end].strip()
        if tag in by_tag:
            raise ValueError(f"duplicate translation line tag {tag}")
        by_tag[tag] = content

    rendered_lines: list[str] = []
    for line in tagged.lines:
        if line.tag not in by_tag:
            raise ValueError(f"missing translation line tag {line.tag}")
        if line.kind == "blank":
            rendered_lines.append("")
            continue
        if line.kind == "marker":
            rendered_lines.append(line.source_text)
            continue
        content = by_tag[line.tag].strip()
        if not content:
            raise ValueError(f"empty translated content for {line.tag}")
        rendered_lines.append(content)
    return rendered_lines


__all__ = [
    "TaggedLine",
    "TaggedTranslationInput",
    "build_tagged_translation_input",
    "is_pagination_or_marker_text",
    "parse_tagged_translation_output",
    "split_tagged_translation_input",
]
