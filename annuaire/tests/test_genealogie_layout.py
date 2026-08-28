"""Regression guard for #80/#81: genealogy tree compaction, label clipping and
spouse-side positioning. These properties can't be asserted through a rendered
page (there's no JS test runner in this project) -- assert on the source text
of family_tree.js/main.css instead, mirroring test_carte_dropdown_layering.py's
approach."""

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
    # load order) and stayed dead code on purpose -- see #80/#81's resolved
    # question. It must not silently come back now that the load-order bug
    # is fixed.
    content = _strip_comments(MAIN_CSS.read_text(encoding="utf-8"))
    assert ".card-genderless" not in content


def test_family_tree_js_sets_a_compact_card_x_spacing():
    content = FAMILY_TREE_JS.read_text(encoding="utf-8")
    assert "CARD_X_SPACING" in content
    assert ".setCardXSpacing(CARD_X_SPACING)" in content
    match = re.search(r"const CARD_X_SPACING\s*=\s*(\d+)", content)
    assert match, "Expected a CARD_X_SPACING constant in family_tree.js"
    # Vendor default is 250 -- must be meaningfully narrower to compact the tree.
    assert int(match.group(1)) < 250


def test_family_tree_js_publishes_label_max_width_as_a_css_custom_property():
    content = FAMILY_TREE_JS.read_text(encoding="utf-8")
    assert "--genealogie-label-max-width" in content
    assert "setProperty" in content


def test_family_tree_js_splits_first_and_last_name_onto_separate_lines():
    content = FAMILY_TREE_JS.read_text(encoding="utf-8")
    assert "setCardDisplay([['first name'], ['last name']" in content


def test_family_tree_js_applies_a_gender_layout_hint_for_spouse_positioning():
    # family-chart hardcodes which side a spouse renders on based on
    # data.gender ("M" => left of the descendant). Person.gender was
    # deliberately dropped from the server payload (#59) and must stay gone
    # -- the fix is a client-side rendering-only hint, applied uniformly so
    # it encodes no real data about any individual.
    content = FAMILY_TREE_JS.read_text(encoding="utf-8")
    assert re.search(r"\.data\.gender\s*=\s*['\"]M['\"]", content)
