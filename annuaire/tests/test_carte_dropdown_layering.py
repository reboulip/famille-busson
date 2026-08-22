"""Regression guard for #78: the Carte person-search dropdown rendering behind
the map. Leaflet forces `position: relative` on its container inline but leaves
`z-index` at `auto`, so its panes escape into the root stacking context above
`.person-picker-results`. `.map-container` must declare its own non-auto z-index
(any value, paired with a position other than `static`) so it becomes a stacking
context and traps Leaflet's panes below the dropdown -- this test doesn't pin the
exact numbers, just the containment property, so it survives a Leaflet upgrade
that changes its pane z-indexes."""

import re
from pathlib import Path

MAIN_CSS = Path(__file__).resolve().parent.parent / "static" / "css" / "main.css"
LEAFLET_CSS = Path(__file__).resolve().parent.parent / "static" / "vendor" / "leaflet" / "leaflet.css"
CARTE_HTML = Path(__file__).resolve().parent.parent / "templates" / "annuaire" / "carte.html"


def _strip_comments(css_text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)


def _rule_body(css_text: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", _strip_comments(css_text))
    assert match, f"No {selector!r} rule found in {MAIN_CSS}"
    return match.group(1)


def _declared_value(body: str, prop: str) -> str | None:
    match = re.search(rf"{prop}\s*:\s*([^;]+);", body)
    return match.group(1).strip() if match else None


def test_map_container_establishes_a_stacking_context():
    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".map-container")
    position = _declared_value(body, "position")
    z_index = _declared_value(body, "z-index")
    assert position is not None and position != "static"
    assert z_index is not None and z_index != "auto"


def test_map_container_z_index_is_not_greater_than_leaflet_panes():
    leaflet_content = LEAFLET_CSS.read_text(encoding="utf-8", errors="ignore")
    pane_z_indexes = [
        int(value) for value in re.findall(r"\.leaflet-[\w-]*pane[^{]*\{[^}]*z-index:\s*(\d+)", leaflet_content)
    ]
    assert pane_z_indexes, "Expected to find at least one Leaflet pane z-index in the vendored CSS"

    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".map-container")
    z_index_str = _declared_value(body, "z-index")
    assert z_index_str is not None
    map_z_index = int(z_index_str)

    # The map container's own z-index only matters relative to its siblings
    # (e.g. the person-picker dropdown) in the *root* stacking context -- it
    # must not itself claim a value at or above what Leaflet uses internally,
    # or a future author could be tempted to "fix" a similar bug by copying it.
    assert map_z_index < min(pane_z_indexes)


def test_carte_person_picker_has_listbox_role_and_bounded_width():
    content = CARTE_HTML.read_text(encoding="utf-8")
    assert 'role="listbox"' in content
    assert "person-picker-inline" in content
    assert ".person-picker-inline" in MAIN_CSS.read_text(encoding="utf-8")


def test_person_picker_js_guards_against_mismatched_markup():
    # carte.html reuses the .person-picker/.person-picker-results classes but
    # not the shared component's .person-picker-input class (its input is
    # .search-input instead), so the shared initPicker() -- which runs on every
    # .person-picker on the page, including Carte's -- must not crash on a null
    # input/resultsList.
    js_path = Path(__file__).resolve().parent.parent / "static" / "js" / "person_picker.js"
    content = js_path.read_text(encoding="utf-8")
    assert "if (!input || !resultsList) return;" in content
