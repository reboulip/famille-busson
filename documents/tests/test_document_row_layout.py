"""Guards for the documents list row cleanup (#123).

The row layout is CSS with no test runner behind it, so the modifier's rules are
asserted on the source text of components.css -- same approach as
annuaire/tests/test_genealogie_layout.py.
"""

import re
from pathlib import Path

import pytest
from django.urls import reverse

COMPONENTS_CSS = Path(__file__).resolve().parent.parent.parent / "annuaire" / "static" / "css" / "components.css"


def _strip_comments(css_text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)


def _rule_body(css_text: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", _strip_comments(css_text))
    assert match, f"No {selector!r} rule found in {COMPONENTS_CSS}"
    return match.group(1)


def _declared_value(body: str, prop: str) -> str | None:
    match = re.search(rf"{prop}\s*:\s*([^;]+);", body)
    return match.group(1).strip() if match else None


@pytest.mark.django_db
def test_document_rows_carry_the_documents_modifier(auth_client, document):
    content = auth_client.get(reverse("document-list")).content.decode()
    assert "fb-post-card--doc" in content


@pytest.mark.django_db
def test_category_and_date_follow_the_title_in_the_row(auth_client, document):
    # The meta line used to precede the description; it now closes the row so it
    # can be pushed to the right edge.
    content = auth_client.get(reverse("document-list")).content.decode()
    assert content.index("fb-post-card__body") < content.index("fb-post-card__meta")


@pytest.mark.django_db
def test_document_list_lede_is_the_shortened_copy(auth_client):
    content = auth_client.get(reverse("document-list")).content.decode()
    assert "Actes, plans et archives de la famille." in content


@pytest.mark.django_db
def test_category_list_lede_is_the_shortened_copy(auth_client):
    content = auth_client.get(reverse("category-list")).content.decode()
    assert "Comment les documents sont classés." in content


def test_the_documents_modifier_beats_the_base_card_rule():
    # Same specificity as .fb-post-card, so a single-class selector would lose or
    # win purely on source order.
    css = COMPONENTS_CSS.read_text(encoding="utf-8")
    assert ".fb-post-card.fb-post-card--doc" in css


def test_the_meta_column_is_pushed_to_the_right_edge():
    body = _rule_body(COMPONENTS_CSS.read_text(encoding="utf-8"), ".fb-post-card--doc .fb-post-card__meta")
    assert _declared_value(body, "margin-left") == "auto"
    assert _declared_value(body, "text-align") == "right"


def test_the_description_is_smaller_on_a_documents_row_only():
    body = _rule_body(COMPONENTS_CSS.read_text(encoding="utf-8"), ".fb-post-card--doc .fb-post-card__excerpt")
    assert _declared_value(body, "font-size") == "var(--fb-text-sm)"
    # The publications feed keeps the base size.
    base = _rule_body(COMPONENTS_CSS.read_text(encoding="utf-8"), ".fb-post-card__excerpt")
    assert _declared_value(base, "font-size") is None
