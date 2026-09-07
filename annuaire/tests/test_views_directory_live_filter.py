"""Tests for the AJAX live-filter behavior of DirectoryListView (#110). JS behaviors
(debounce timing, the stale-response guard, history.replaceState) have no browser test
runner in this project -- assert on live_filter.js's source text instead, mirroring
test_document_viewer_layout.py's approach.

live_filter.js is shared with the documents list; see
documents/tests/test_views_document_live_filter.py for that side of the contract."""

from pathlib import Path

import pytest
from django.urls import reverse

from annuaire.models import Person

LIVE_FILTER_JS = Path(__file__).resolve().parent.parent / "static" / "js" / "live_filter.js"


def _js() -> str:
    return LIVE_FILTER_JS.read_text(encoding="utf-8")


@pytest.mark.django_db
def test_directory_ajax_request_returns_only_the_results_partial(auth_client, person):
    response = auth_client.get(reverse("directory"), headers={"x-requested-with": "XMLHttpRequest"})
    assert response.status_code == 200
    assert [t.name for t in response.templates] == ["annuaire/_annuaire_results.html", "annuaire/_person_card.html"]
    content = response.content.decode()
    assert "<h1>Annuaire</h1>" not in content
    assert "directory-filter-form" not in content
    assert person.first_name in content


@pytest.mark.django_db
def test_directory_non_ajax_request_returns_the_full_page(auth_client, person):
    response = auth_client.get(reverse("directory"))
    assert "annuaire/annuaire_list.html" in [t.name for t in response.templates]
    assert "directory-filter-form" in response.content.decode()


@pytest.mark.django_db
def test_directory_ajax_and_non_ajax_responses_vary_on_the_ajax_header(auth_client):
    response = auth_client.get(reverse("directory"))
    assert "X-Requested-With" in response["Vary"]


@pytest.mark.django_db
def test_directory_ajax_request_still_applies_search_and_sort(auth_client, person, other_person):
    response = auth_client.get(
        reverse("directory"),
        {"q": "Busson", "sort": "name_asc"},
        headers={"x-requested-with": "XMLHttpRequest"},
    )
    persons = list(response.context["persons"])
    assert person in persons
    assert other_person in persons
    assert persons.index(person) < persons.index(other_person)


@pytest.mark.django_db
def test_directory_search_button_is_removed(auth_client):
    response = auth_client.get(reverse("directory"))
    content = response.content.decode()
    assert "Rechercher</button>" not in content


@pytest.mark.django_db
def test_directory_no_minimum_query_length_returns_empty_grid_message(auth_client):
    Person.objects.all().delete()
    response = auth_client.get(reverse("directory"), {"q": "z"})
    # Copy lost its trailing period when the bare <p>Aucun…</p> became the shared
    # empty-state component (annuaire/_empty.html), where it is a title, not a sentence.
    assert "Aucune personne trouvée" in response.content.decode()


@pytest.mark.django_db
def test_directory_form_declares_its_results_container_and_sort_default(auth_client):
    content = auth_client.get(reverse("directory")).content.decode()
    assert 'data-live-filter="#directory-results"' in content
    # "recent" is the default sort, so it must stay out of the synced URL.
    assert 'data-live-filter-default="recent"' in content


@pytest.mark.django_db
def test_directory_clear_link_starts_hidden_when_no_filter_is_active(auth_client):
    """The "Effacer" link lives in the page header, outside the swapped-in partial, so
    the script has to show/hide it -- it used to never appear when you typed, and to
    linger after you cleared the box (#110)."""
    content = auth_client.get(reverse("directory")).content.decode()
    assert "data-live-filter-reset" in content
    reset_tag = content[content.index("data-live-filter-reset") : content.index("data-live-filter-reset") + 200]
    assert "hidden" in reset_tag


@pytest.mark.django_db
def test_directory_clear_link_is_visible_when_a_filter_is_active(auth_client):
    content = auth_client.get(reverse("directory"), {"q": "Busson"}).content.decode()
    reset_tag = content[content.index("data-live-filter-reset") : content.index("data-live-filter-reset") + 200]
    assert "hidden" not in reset_tag


def test_live_filter_js_debounces_free_text_input():
    content = _js()
    assert "DEBOUNCE_MS = 200" in content
    assert "control.addEventListener('input'" in content


def test_live_filter_js_applies_non_text_controls_immediately_without_debounce():
    content = _js()
    assert "control.addEventListener('change'" in content


def test_live_filter_js_sends_ajax_header():
    assert "'X-Requested-With': 'XMLHttpRequest'" in _js()


def test_live_filter_js_guards_against_stale_responses():
    assert "requestSeq" in _js()


def test_live_filter_js_syncs_the_url_without_pushing_history():
    assert "history.replaceState" in _js()


def test_live_filter_js_omits_default_values_from_the_url():
    assert "control.dataset.liveFilterDefault" in _js()


def test_live_filter_js_updates_links_outside_the_swapped_partial():
    content = _js()
    assert "data-live-filter-reset" in content
    assert "resetLink.hidden" in content
    assert "data-live-filter-carry" in content
