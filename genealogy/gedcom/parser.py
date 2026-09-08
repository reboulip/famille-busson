"""Pure GEDCOM lexer -- bytes/text to a tree of records, zero DB awareness.

Tag semantics (INDI vs FAM, what BIRT/DEAT/MARR mean) belong to importer.py,
mirroring how writer.py (generic line mechanics) and export.py (GEDCOM
semantics) are already split for the write side.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_SUPPORTED_CHARSETS = {
    "UTF-8": "utf-8",
    "UNICODE": "utf-8",
    "ANSI": "cp1252",
    "ASCII": "cp1252",
    "CP1252": "cp1252",
    "LATIN1": "cp1252",
}


class GedcomParseError(Exception):
    """A structural problem with the uploaded file -- always carries a French
    message suitable for showing directly to the staff member who uploaded it."""


@dataclass
class GedcomRecord:
    level: int
    xref: str | None
    tag: str
    value: str
    children: list[GedcomRecord] = field(default_factory=list)

    def child(self, tag: str) -> GedcomRecord | None:
        return next((c for c in self.children if c.tag == tag), None)


def _detect_charset(raw: bytes) -> str:
    """A BOM wins outright. Otherwise scan the HEAD's `1 CHAR <value>` line,
    decoded permissively as latin-1 since it's plain ASCII in practice --
    the real decoding of the whole file only happens once this is known."""
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    head = raw[:4096].decode("latin-1", errors="ignore")
    for line in head.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("1 CHAR"):
            parts = stripped.split(None, 2)
            if len(parts) == 3:
                declared = parts[2].strip().upper()
                if declared == "ANSEL":
                    raise GedcomParseError(
                        "Encodage ANSEL non pris en charge. Veuillez ré-exporter le fichier en UTF-8."
                    )
                return _SUPPORTED_CHARSETS.get(declared, "utf-8")
    return "utf-8"


def decode_gedcom(raw: bytes) -> str:
    """Decode an uploaded GEDCOM file's bytes to text, UTF-8 (with or without
    BOM) or CP1252/Latin-1 only -- see _detect_charset()."""
    charset = _detect_charset(raw)
    try:
        return raw.decode(charset)
    except UnicodeDecodeError as exc:
        raise GedcomParseError("Impossible de décoder ce fichier. Veuillez ré-exporter en UTF-8.") from exc


def _parse_line(line: str) -> tuple[int, str | None, str, str]:
    # Only the trailing CRLF/LF is insignificant -- a value's own trailing
    # whitespace can be meaningful when a CONC continuation concatenates
    # directly onto it with no separator of its own.
    tokens = line.rstrip("\r\n").split(" ")
    if not tokens or not tokens[0].isdigit():
        raise GedcomParseError(f"Ligne GEDCOM invalide : {line!r}")
    level = int(tokens[0])
    idx = 1
    xref = None
    # A record-identifying xref (e.g. "0 @I1@ INDI") sits right after the
    # level, before the tag. A pointer *value* (e.g. "1 HUSB @I1@") sits
    # after the tag instead, and is left as plain value text below.
    if idx < len(tokens) and len(tokens[idx]) > 1 and tokens[idx].startswith("@") and tokens[idx].endswith("@"):
        xref = tokens[idx]
        idx += 1
    if idx >= len(tokens):
        raise GedcomParseError(f"Ligne GEDCOM invalide (balise manquante) : {line!r}")
    tag = tokens[idx]
    idx += 1
    value = " ".join(tokens[idx:])
    return level, xref, tag, value


def parse_gedcom(content: str) -> list[GedcomRecord]:
    """Parse already-decoded GEDCOM text into a forest of top-level records
    (one per level-0 line, e.g. one per INDI/FAM/HEAD/TRLR)."""
    lines = [ln for ln in content.split("\n") if ln.strip()]
    parsed = [_parse_line(ln) for ln in lines]

    # Reassemble CONC (concatenated directly) / CONT (concatenated with a
    # newline) into the value of the record they continue -- always the most
    # recently emitted one, since GEDCOM file order guarantees a
    # CONC/CONT line immediately follows the line whose value it extends.
    flat: list[tuple[int, str | None, str, str]] = []
    for level, xref, tag, value in parsed:
        if tag == "CONC" and flat:
            prev = flat[-1]
            flat[-1] = (prev[0], prev[1], prev[2], prev[3] + value)
        elif tag == "CONT" and flat:
            prev = flat[-1]
            flat[-1] = (prev[0], prev[1], prev[2], prev[3] + "\n" + value)
        else:
            flat.append((level, xref, tag, value))

    root: list[GedcomRecord] = []
    stack: list[GedcomRecord] = []
    for level, xref, tag, value in flat:
        record = GedcomRecord(level=level, xref=xref, tag=tag, value=value)
        while stack and stack[-1].level >= level:
            stack.pop()
        if stack:
            stack[-1].children.append(record)
        else:
            root.append(record)
        stack.append(record)
    return root
