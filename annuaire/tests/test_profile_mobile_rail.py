"""Guards for the profile view's relocated actions and mobile sticky identity (#124).

The sticky/condensing behaviour itself is CSS and JS with no test runner behind
it, so the contract between the three files is asserted on their source text --
same approach as test_genealogie_layout.py. Note that its `_rule_body` helper
cannot see inside an `@media` block, so the mobile rules are checked as raw
substrings instead.
"""

import re
from pathlib import Path

import pytest
from django.urls import reverse

from annuaire.models import Relation

STATIC = Path(__file__).resolve().parent.parent / "static"
MAIN_CSS = STATIC / "css" / "main.css"
STICKY_JS = STATIC / "js" / "profile_sticky_identity.js"
COMPONENTS_CSS = STATIC / "css" / "components.css"


def _mobile_block(css_text: str) -> str:
    """The @media (max-width: 767.98px) block, sliced by brace balance."""
    start = css_text.index("@media (max-width: 767.98px)")
    depth = 0
    for index in range(css_text.index("{", start), len(css_text)):
        if css_text[index] == "{":
            depth += 1
        elif css_text[index] == "}":
            depth -= 1
            if depth == 0:
                return css_text[start : index + 1]
    raise AssertionError("unterminated media block")


@pytest.mark.django_db
def test_relations_action_renders_once_when_there_are_relations(auth_client, person, other_person):
    Relation.objects.create(person1=person, person2=other_person, relationship_type=2)
    content = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk})).content.decode()
    assert content.count("Modifier les relations") == 1


@pytest.mark.django_db
def test_relations_action_renders_once_when_there_are_none(auth_client, person):
    # The empty state used to carry its own copy of this button; with the actions
    # block moved below the section, that would have rendered it twice.
    content = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk})).content.decode()
    assert content.count("Modifier les relations") == 1


@pytest.mark.django_db
def test_actions_sit_after_the_relations_section(auth_client, person):
    content = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk})).content.decode()
    assert content.index("fb-relations") < content.index("profile-record__actions")


@pytest.mark.django_db
def test_profile_page_loads_the_sticky_identity_script(auth_client, person):
    content = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk})).content.decode()
    assert "js/profile_sticky_identity.js" in content
    assert "profile-identity-sentinel" in content


def test_the_identity_card_only_sticks_below_the_mobile_breakpoint():
    block = _mobile_block(MAIN_CSS.read_text(encoding="utf-8"))
    assert ".profile-record .profile-identity" in block
    assert "position: sticky;" in block
    assert "var(--profile-sticky-top" in block


def test_the_condensed_state_stands_down_everything_but_name_and_photo():
    block = _mobile_block(MAIN_CSS.read_text(encoding="utf-8"))
    assert ".profile-record .profile-identity--pinned" in block
    assert re.search(r"\.profile-identity--pinned \.fb-meta \{ display: none; \}", block)


def test_the_shared_record_component_is_not_restyled_for_the_profile_page():
    # .fb-record is also the chalet detail page's layout -- the profile's rules
    # hang off .profile-record so that page is untouched.
    assert "profile-record" not in COMPONENTS_CSS.read_text(encoding="utf-8")


def test_the_sticky_offset_is_measured_rather_than_hardcoded():
    content = STICKY_JS.read_text(encoding="utf-8")
    assert "getBoundingClientRect" in content
    assert "setProperty" in content
    assert "--profile-sticky-top" in content
    assert "IntersectionObserver" in content
    assert "profile-identity--pinned" in content
