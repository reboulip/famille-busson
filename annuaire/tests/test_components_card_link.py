"""Source-text guards for the whole-card click target (#128). There is no JS test
runner in this project, so the CSS contract the overlay depends on is asserted on
the text of components.css -- mirroring test_genealogie_layout.py's approach.

The overlay is Bootstrap's stretched-link: its ::after fills the nearest
positioned ancestor, so the card (and the category row) must stay positioned, and
anything meant to remain independently clickable must sit above it.
"""

import re
from pathlib import Path

COMPONENTS_CSS = Path(__file__).resolve().parent.parent / "static" / "css" / "components.css"


def _strip_comments(css_text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)


def _rule_body(css_text: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", _strip_comments(css_text))
    assert match, f"No {selector!r} rule found in {COMPONENTS_CSS}"
    return match.group(1)


def _declared_value(body: str, prop: str) -> str | None:
    match = re.search(rf"{prop}\s*:\s*([^;]+);", body)
    return match.group(1).strip() if match else None


def test_post_card_is_a_positioned_ancestor_for_the_overlay():
    body = _rule_body(COMPONENTS_CSS.read_text(encoding="utf-8"), ".fb-post-card")
    assert _declared_value(body, "position") == "relative"


def test_meta_links_stay_above_the_overlay():
    # Without this the author links on a post and the category link on a document
    # would be swallowed by the overlay and stop working.
    body = _rule_body(COMPONENTS_CSS.read_text(encoding="utf-8"), ".fb-post-card .fb-meta a")
    assert _declared_value(body, "position") == "relative"
    assert _declared_value(body, "z-index") == "2"


def test_category_tree_row_is_a_positioned_ancestor_for_the_overlay():
    # The wrapper is what bounds the overlay to one row: anchored to the <li>
    # instead, it would cover the nested child list and make those rows dead.
    body = _rule_body(COMPONENTS_CSS.read_text(encoding="utf-8"), ".category-tree__row")
    assert _declared_value(body, "position") == "relative"
