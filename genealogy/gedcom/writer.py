"""Hand-rolled GEDCOM 5.5.1 line writer -- no PyPI dependency.

Same rationale as annuaire/ical.py: the surface this project needs (a handful
of tags, CRLF line endings, byte-count value folding via CONC, `@`
pointer-escaping) is small, must stay source-text testable, and a maintained
GEDCOM library on PyPI is a read-only parser anyway -- useless for writing.
"""

from __future__ import annotations

import datetime

_MAX_LINE_BYTES = 255  # GEDCOM 5.5.1 line length limit, in bytes

_MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def escape_value(value: str) -> str:
    """GEDCOM escapes a literal '@' by doubling it -- otherwise it would be
    read as the start of a pointer."""
    return value.replace("@", "@@")


def format_date(d: datetime.date) -> str:
    """GEDCOM's DATE value: day, a fixed 3-letter English month abbreviation
    (never locale-dependent -- locale.setlocale() is process-global and not
    thread-safe, so this is a hardcoded table instead), and a 4-digit year."""
    return f"{d.day} {_MONTHS[d.month - 1]} {d.year}"


def _split_by_bytes(value: str, limit: int) -> list[str]:
    """Split `value` into <=`limit`-byte chunks, never inside a UTF-8 sequence
    -- same technique as ical.py's _fold_line, applied to GEDCOM's CONC
    continuation mechanism instead of RFC 5545 line folding."""
    data = value.encode("utf-8")
    if len(data) <= limit:
        return [value]
    chunks = []
    start = 0
    while start < len(data):
        end = min(start + limit, len(data))
        while end < len(data) and (data[end] & 0xC0) == 0x80:
            end -= 1
        chunks.append(data[start:end].decode("utf-8"))
        start = end
    return chunks


def pointer_line(level: int, tag: str, target_xref: str) -> str:
    """A pointer reference (e.g. `1 HUSB @I1@`, `1 FAMS @F2@`) -- the xref is
    a structural pointer, never escaped or folded (it's always well under the
    line-length limit), unlike a literal text value passed to tag_lines()."""
    return f"{level} {tag} {target_xref}"


def tag_lines(level: int, tag: str, value: str = "", xref: str | None = None) -> list[str]:
    """One logical GEDCOM tag as one or more physical lines: the base line,
    plus `level+1 CONC <chunk>` continuations if the escaped value doesn't fit
    in one 255-byte line. `xref` here names *this* record (e.g. `0 @I1@ INDI`)
    -- for a pointer *reference* to another record, use pointer_line() instead,
    since a pointer value must never be @-escaped."""
    head = f"{level} {xref} {tag}" if xref else f"{level} {tag}"
    if not value:
        return [head]
    escaped = escape_value(value)
    budget = max(_MAX_LINE_BYTES - len(head.encode("utf-8")) - 1, 1)
    chunks = _split_by_bytes(escaped, budget)
    lines = [f"{head} {chunks[0]}"]
    for chunk in chunks[1:]:
        lines.append(f"{level + 1} CONC {chunk}")
    return lines


def render_gedcom(record_lines: list[str]) -> bytes:
    """Wrap the given already-built tag lines (individuals, families) with the
    HEAD/TRLR envelope and encode as CRLF UTF-8 bytes."""
    lines = [
        "0 HEAD",
        "1 SOUR famille_busson",
        "1 GEDC",
        "2 VERS 5.5.1",
        "2 FORM LINEAGE-LINKED",
        "1 CHAR UTF-8",
    ]
    lines.extend(record_lines)
    lines.append("0 TRLR")
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")
