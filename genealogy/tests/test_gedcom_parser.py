import pytest

from genealogy.gedcom.parser import GedcomParseError, decode_gedcom, parse_gedcom


def test_parse_gedcom_builds_a_tree():
    content = "0 @I1@ INDI\n1 NAME Jean /Busson/\n1 BIRT\n2 DATE 12 MAY 1990\n"
    records = parse_gedcom(content)
    assert len(records) == 1
    indi = records[0]
    assert indi.level == 0
    assert indi.xref == "@I1@"
    assert indi.tag == "INDI"
    name = indi.child("NAME")
    assert name is not None
    assert name.value == "Jean /Busson/"
    birt = indi.child("BIRT")
    assert birt is not None
    assert birt.child("DATE").value == "12 MAY 1990"


def test_parse_gedcom_reassembles_conc_with_no_separator():
    content = "0 @I1@ INDI\n1 NOTE hello \n2 CONC world\n"
    records = parse_gedcom(content)
    note = records[0].child("NOTE")
    assert note.value == "hello world"


def test_parse_gedcom_reassembles_cont_with_a_newline():
    content = "0 @I1@ INDI\n1 NOTE first line\n2 CONT second line\n"
    records = parse_gedcom(content)
    note = records[0].child("NOTE")
    assert note.value == "first line\nsecond line"


def test_parse_gedcom_pointer_value_is_not_mistaken_for_a_record_xref():
    content = "0 @F1@ FAM\n1 HUSB @I1@\n1 WIFE @I2@\n"
    records = parse_gedcom(content)
    fam = records[0]
    assert fam.xref == "@F1@"
    husb = fam.child("HUSB")
    assert husb.xref is None
    assert husb.value == "@I1@"


def test_parse_gedcom_ignores_blank_lines():
    content = "0 @I1@ INDI\n\n1 NAME Jean /Busson/\n\n"
    records = parse_gedcom(content)
    assert records[0].child("NAME").value == "Jean /Busson/"


def test_parse_gedcom_multiple_top_level_records():
    content = "0 @I1@ INDI\n1 NAME Jean /Busson/\n0 @I2@ INDI\n1 NAME Bob /Busson/\n"
    records = parse_gedcom(content)
    assert len(records) == 2
    assert records[0].xref == "@I1@"
    assert records[1].xref == "@I2@"


def test_parse_gedcom_rejects_line_with_no_digit_level():
    with pytest.raises(GedcomParseError):
        parse_gedcom("not a gedcom line\n")


def test_parse_gedcom_rejects_line_with_no_tag():
    with pytest.raises(GedcomParseError):
        parse_gedcom("0\n")


def test_decode_gedcom_utf8_no_bom():
    raw = "0 @I1@ INDI\n1 NAME Éric /Büsson/\n".encode()
    assert "Éric" in decode_gedcom(raw)


def test_decode_gedcom_utf8_with_bom():
    raw = b"\xef\xbb\xbf" + b"0 @I1@ INDI\n1 NAME Jean /Busson/\n"
    content = decode_gedcom(raw)
    assert content.startswith("0 @I1@ INDI")


def test_decode_gedcom_cp1252_declared_in_head():
    content = "0 HEAD\n1 CHAR ANSI\n0 @I1@ INDI\n1 NAME Éric /Büsson/\n"
    raw = content.encode("cp1252")
    decoded = decode_gedcom(raw)
    assert "Éric" in decoded


def test_decode_gedcom_rejects_ansel():
    content = "0 HEAD\n1 CHAR ANSEL\n0 @I1@ INDI\n"
    raw = content.encode("ascii")
    with pytest.raises(GedcomParseError):
        decode_gedcom(raw)
