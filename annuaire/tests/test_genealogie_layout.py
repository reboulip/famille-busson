"""Regression guard for #80: genealogy tree label clipping. These properties
can't be asserted through a rendered page (there's no JS test runner in this
project) -- assert on the source text of family_tree.js/main.css instead,
mirroring test_carte_dropdown_layering.py's approach.

#81's compact card spacing and gender-based spouse-side hint (previously
guarded here alongside #80) were reverted as a hotfix: they made the label
wrap onto too-narrow lines and broke name display (see #81)."""

import re
from pathlib import Path

MAIN_CSS = Path(__file__).resolve().parent.parent / "static" / "css" / "main.css"
FAMILY_TREE_JS = Path(__file__).resolve().parent.parent / "static" / "js" / "family_tree.js"


def _strip_comments(css_text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)


def _rule_body(css_text: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", _strip_comments(css_text))
    assert match, f"No {selector!r} rule found in {MAIN_CSS}"
    return match.group(1)


def _declared_value(body: str, prop: str) -> str | None:
    match = re.search(rf"{prop}\s*:\s*([^;]+);", body)
    return match.group(1).strip() if match else None


def test_genealogy_label_wraps_instead_of_clipping():
    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".f3 div.card-image-circle div.card-label")
    assert _declared_value(body, "white-space") == "normal"


def test_genealogy_label_max_width_uses_the_shared_spacing_variable():
    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".f3 div.card-image-circle div.card-label")
    max_width = _declared_value(body, "max-width")
    assert max_width is not None
    assert "--genealogie-label-max-width" in max_width


def test_genealogy_card_genderless_ring_override_is_removed():
    # #59's ring-color override was dead code (beaten by the vendor CSS on
    # load order) and stayed dead code on purpose -- see #80's resolved
    # question. It must not silently come back now that the load-order bug
    # is fixed.
    content = _strip_comments(MAIN_CSS.read_text(encoding="utf-8"))
    assert ".card-genderless" not in content


def test_family_tree_js_publishes_label_max_width_as_a_css_custom_property():
    content = FAMILY_TREE_JS.read_text(encoding="utf-8")
    assert "--genealogie-label-max-width" in content
    assert "setProperty" in content


def test_family_tree_js_splits_first_and_last_name_onto_separate_lines():
    content = FAMILY_TREE_JS.read_text(encoding="utf-8")
    assert "setCardDisplay([['first name'], ['last name']" in content


def test_family_tree_js_mounts_search_dropdown_in_toolbar():
    # 6.3: the search field moves out of the chart overlay into the toolbar's
    # #genealogie-search mount, via family-chart's supported `cont` option.
    content = FAMILY_TREE_JS.read_text(encoding="utf-8")
    assert "setPersonDropdown(" in content
    assert "genealogie-search" in content


def test_genealogy_autocomplete_overrides_are_scoped_to_search_mount_not_f3():
    # Moving the widget out of .f3 orphans the vendor's own --background-color/
    # --text-color custom properties (declared on .f3) -- our override must be
    # re-scoped to .genealogie-search, or the field silently regresses to
    # black-on-near-black.
    content = _strip_comments(MAIN_CSS.read_text(encoding="utf-8"))
    assert ".genealogie-search .f3-autocomplete input" in content
    assert ".f3 .f3-autocomplete input" not in content


def test_genealogy_autocomplete_results_list_is_positioned_absolute():
    # The vendor result list is in normal flow -- without this it would grow
    # the toolbar row and shove the chart down on every keystroke.
    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".genealogie-search .f3-autocomplete-items")
    assert _declared_value(body, "position") == "absolute"


def test_genealogy_fullscreen_panel_is_a_fixed_overlay():
    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".genealogie-panel--fullscreen")
    assert _declared_value(body, "position") == "fixed"
    assert _declared_value(body, "inset") == "0"


def test_genealogy_fullscreen_detail_panel_floats_over_the_tree():
    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".genealogie-panel--fullscreen .genealogie-detail")
    assert _declared_value(body, "position") == "absolute"


def test_family_tree_js_refits_the_chart_after_fullscreen_toggle():
    # No resize/ResizeObserver handler exists in the vendored bundle -- the
    # implementer must explicitly re-fit after every size change.
    content = FAMILY_TREE_JS.read_text(encoding="utf-8")
    assert "genealogie-fullscreen" in content
    assert "requestAnimationFrame" in content
    assert "tree_position: 'fit'" in content


def test_family_tree_js_exits_fullscreen_on_escape():
    content = FAMILY_TREE_JS.read_text(encoding="utf-8")
    assert "Escape" in content
