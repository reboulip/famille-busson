"""Regression guard for #85: non-square profile pictures were left-aligned
inside their marker medallion instead of centered (Leaflet's own CSS beats
main.css's width:100% at higher specificity -- see the comment next to the
!important in main.css). Assert on CSS source text, mirroring
test_genealogie_layout.py's approach -- there's no JS test runner here."""

import re
from pathlib import Path

MAIN_CSS = Path(__file__).resolve().parent.parent / "static" / "css" / "main.css"


def _strip_comments(css_text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)


def _rule_body(css_text: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", _strip_comments(css_text))
    assert match, f"No {selector!r} rule found in {MAIN_CSS}"
    return match.group(1)


def _declared_value(body: str, prop: str) -> str | None:
    match = re.search(rf"{prop}\s*:\s*([^;]+);", body)
    return match.group(1).strip() if match else None


def test_marker_avatar_img_width_beats_leaflet_with_important():
    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".map-marker-avatar img")
    assert _declared_value(body, "width") == "100% !important"


def test_marker_avatar_img_is_centered():
    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".map-marker-avatar img")
    assert _declared_value(body, "object-position") == "center"


def test_marker_avatar_img_keeps_object_fit_cover():
    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".map-marker-avatar img")
    assert _declared_value(body, "object-fit") == "cover"
