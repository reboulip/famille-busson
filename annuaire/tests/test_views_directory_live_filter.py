"""Tests for the AJAX live-filter behavior of DirectoryListView (#110). JS behaviors
(debounce timing, the stale-response guard, history.replaceState) have no browser test
runner in this project -- assert on directory_filter.js's source text instead, mirroring
test_document_viewer_layout.py's approach."""

from pathlib import Path

import pytest
from django.urls import reverse

from annuaire.models import Person

DIRECTORY_FILTER_JS = Path(__file__).resolve().parent.parent / "static" / "js" / "directory_filter.js"


@pytest.mark.django_db
def test_directory_ajax_request_returns_only_the_results_partial(auth_client, person):
    response = auth_client.get(reverse("directory"), headers={"x-requested-with": "XMLHttpRequest"})
    assert response.status_code == 200
    assert [t.name for t in response.templates] == ["annuaire/_annuaire_results.html"]
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
    assert "Aucune personne trouvée." in response.content.decode()


def test_directory_filter_js_debounces_search_input():
    content = DIRECTORY_FILTER_JS.read_text(encoding="utf-8")
    assert "DEBOUNCE_MS = 200" in content
    assert "searchInput.addEventListener('input'" in content


def test_directory_filter_js_applies_sort_immediately_without_debounce():
    content = DIRECTORY_FILTER_JS.read_text(encoding="utf-8")
    assert "sortSelect.addEventListener('change'" in content


def test_directory_filter_js_sends_ajax_header():
    content = DIRECTORY_FILTER_JS.read_text(encoding="utf-8")
    assert "'X-Requested-With': 'XMLHttpRequest'" in content


def test_directory_filter_js_guards_against_stale_responses():
    content = DIRECTORY_FILTER_JS.read_text(encoding="utf-8")
    assert "requestSeq" in content


def test_directory_filter_js_syncs_the_url_without_pushing_history():
    content = DIRECTORY_FILTER_JS.read_text(encoding="utf-8")
    assert "history.replaceState" in content
