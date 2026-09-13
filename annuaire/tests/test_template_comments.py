"""Django's template-comment lexer only matches within a single line: a comment
opened on one line and closed on a later one is never recognized as a comment at
all, and leaks as literal text in the rendered page. This guards against that
mistake recurring anywhere in the repo -- the fix is always to use the multi-line
block form instead."""

from pathlib import Path

TEMPLATE_APPS = ("annuaire", "publications", "documents", "photos", "events", "genealogy")

_OPEN = "{" + "#"
_CLOSE = "#" + "}"


def _offending_lines(content: str) -> list[str]:
    offenders = []
    in_script_or_style = False
    for line in content.splitlines():
        lowered = line.lower()
        if "<script" in lowered or "<style" in lowered:
            in_script_or_style = True
        if in_script_or_style:
            if "</script>" in lowered or "</style>" in lowered:
                in_script_or_style = False
            continue
        if _OPEN in line and _CLOSE not in line:
            offenders.append(line)
    return offenders


def test_no_multiline_only_template_comments():
    root = Path(__file__).resolve().parent.parent.parent
    offenders: dict[str, list[str]] = {}
    for app in TEMPLATE_APPS:
        for path in (root / app).rglob("*.html"):
            found = _offending_lines(path.read_text(encoding="utf-8"))
            if found:
                offenders[str(path.relative_to(root))] = found

    assert not offenders, (
        "single-line-only Django comment syntax spans multiple lines and will leak "
        f"as visible text -- use the block comment tag instead: {offenders}"
    )
