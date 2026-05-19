from waraq.translation.line_protocol import (
    build_tagged_translation_input,
    parse_tagged_translation_output,
    split_tagged_translation_input,
)


def test_preserves_marker_and_blank_lines_exactly():
    tagged = build_tagged_translation_input("12\n\nهذا سطر")
    output = "[[L0001]] 999\n[[L0002]] leer\n[[L0003]] This is a line"
    parsed = parse_tagged_translation_output(output, tagged)
    assert parsed == ["12", "", "This is a line"]


def test_rejects_missing_line_tags():
    tagged = build_tagged_translation_input("12\nهذا سطر")
    try:
        parse_tagged_translation_output("[[L0001]] 12", tagged)
    except ValueError as exc:
        assert "missing translation line tag" in str(exc)
    else:
        raise AssertionError("expected missing-tag failure")


def test_splits_long_tagged_input_into_smaller_batches():
    source = "\n".join(f"line {i}" for i in range(1, 33))
    tagged = build_tagged_translation_input(source)
    batches = split_tagged_translation_input(tagged, max_lines=20, max_chars=10000)
    assert len(batches) == 2
    assert len(batches[0].lines) == 20
    assert len(batches[1].lines) == 12
    assert batches[0].lines[0].tag == "L0001"
    assert batches[1].lines[-1].tag == "L0032"
