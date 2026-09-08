import datetime

from genealogy.gedcom.writer import escape_value, format_date, pointer_line, render_gedcom, tag_lines


def test_pointer_line_shape():
    assert pointer_line(1, "HUSB", "@I1@") == "1 HUSB @I1@"


def test_pointer_line_does_not_escape_the_at_signs():
    # A pointer's '@'s are structural, not literal text -- must never be
    # doubled the way tag_lines()/escape_value() would treat a text value.
    assert pointer_line(1, "FAMS", "@F2@") == "1 FAMS @F2@"


def test_escape_value_doubles_at_signs():
    assert escape_value("user@example.com") == "user@@example.com"


def test_format_date_uses_english_three_letter_month():
    assert format_date(datetime.date(1990, 5, 12)) == "12 MAY 1990"


def test_format_date_january_and_december():
    assert format_date(datetime.date(2000, 1, 1)) == "1 JAN 2000"
    assert format_date(datetime.date(2000, 12, 31)) == "31 DEC 2000"


def test_tag_lines_without_value():
    assert tag_lines(1, "BIRT") == ["1 BIRT"]


def test_tag_lines_with_value():
    assert tag_lines(2, "DATE", "12 MAY 1990") == ["2 DATE 12 MAY 1990"]


def test_tag_lines_with_xref():
    assert tag_lines(1, "FAMS", xref="@F1@") == ["1 @F1@ FAMS"]


def test_tag_lines_escapes_at_signs_in_value():
    assert tag_lines(1, "PLAC", "Café @ Lyon") == ["1 PLAC Café @@ Lyon"]


def test_tag_lines_splits_long_value_into_conc_continuations():
    long_value = "x" * 500
    lines = tag_lines(1, "NOTE", long_value)
    assert len(lines) > 1
    assert lines[0].startswith("1 NOTE ")
    for continuation in lines[1:]:
        assert continuation.startswith("2 CONC ")
    # Reassembling (dropping the tag prefixes) must reproduce the original value.
    reassembled = lines[0][len("1 NOTE ") :] + "".join(line[len("2 CONC ") :] for line in lines[1:])
    assert reassembled == long_value


def test_tag_lines_never_splits_inside_a_multibyte_utf8_character():
    # Each 'é' is 2 bytes in UTF-8 -- a naive byte-count split could land
    # mid-character. If it did, decoding the truncated bytes back to str
    # inside tag_lines() would raise UnicodeDecodeError before this line is
    # ever reached; reassembling must also reproduce the exact original text.
    value = "é" * 200
    lines = tag_lines(1, "NOTE", value)
    assert len(lines) > 1
    reassembled = lines[0][len("1 NOTE ") :] + "".join(line[len("2 CONC ") :] for line in lines[1:])
    assert reassembled == value


def test_render_gedcom_wraps_head_and_trailer():
    payload = render_gedcom(["0 @I1@ INDI", "1 NAME Jean /Busson/"])
    text = payload.decode("utf-8")
    assert text.startswith("0 HEAD\r\n")
    assert "1 CHAR UTF-8\r\n" in text
    assert text.endswith("0 TRLR\r\n")
    assert "0 @I1@ INDI\r\n" in text


def test_render_gedcom_uses_crlf_line_endings():
    payload = render_gedcom(["0 @I1@ INDI"])
    assert b"\r\n" in payload
    assert b"\n\n" not in payload.replace(b"\r\n", b"")
