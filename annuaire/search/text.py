import re
import unicodedata

MAX_SEARCH_TEXT_LENGTH = 100_000

_TERM_RE = re.compile(r"\w+")


def normalize(text: str | None) -> str:
    """Fold accents, casefold, and collapse whitespace for indexing and querying.

    Applied identically on both the indexed text and the incoming query, on both
    the Postgres and the SQLite fallback backend, so "Bus" reliably matches "Büsson"
    everywhere rather than only on whichever database happens to have an unaccent
    extension.
    """
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    collapsed = re.sub(r"\s+", " ", without_marks).strip().casefold()
    return collapsed[:MAX_SEARCH_TEXT_LENGTH]


def terms(query: str | None) -> list[str]:
    """Split a normalized query into safe word terms.

    Keeping only `\\w+` runs is what makes the Postgres backend's raw tsquery safe:
    a term list built here never contains the characters (', &, |, !, (, )) that
    would otherwise turn a hostile search into a tsquery syntax error.
    """
    return _TERM_RE.findall(normalize(query))
