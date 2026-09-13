"""17.2 -- the document detail description spans the page's full width instead of
being capped to the long-form reading measure, via a paired modifier class -- same
CSS-source-text-assertion approach as documents/tests/test_document_row_layout.py.
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
def test_document_detail_description_carries_the_full_width_modifier(auth_client, document):
    document.description = "Une description assez longue pour être visible."
    document.save()
    content = auth_client.get(reverse("document-detail", args=[document.pk])).content.decode()
    assert "fb-longform fb-longform--full" in content


def test_full_width_modifier_removes_the_reading_measure_cap():
    css_text = COMPONENTS_CSS.read_text(encoding="utf-8")
    body = _rule_body(css_text, ".fb-longform.fb-longform--full")
    assert _declared_value(body, "max-width") == "none"


def test_base_longform_rule_keeps_its_reading_measure():
    css_text = COMPONENTS_CSS.read_text(encoding="utf-8")
    body = _rule_body(css_text, ".fb-longform")
    assert _declared_value(body, "max-width") == "var(--fb-measure-max)"
