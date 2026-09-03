"""Tests for the AJAX live-filter behavior of DocumentListView. The documents list kept
an explicit "Rechercher" button after the annuaire's filter went live in #110; both now
share annuaire/static/js/live_filter.js, so the two lists behave the same way.

The JS side of the contract is asserted in
annuaire/tests/test_views_directory_live_filter.py -- this file covers the server half
plus the documents-specific markup."""

import pytest
from django.urls import reverse

from documents.models import Document


@pytest.mark.django_db
def test_document_list_ajax_request_returns_only_the_results_partial(auth_client, document):
    response = auth_client.get(reverse("document-list"), headers={"x-requested-with": "XMLHttpRequest"})
    assert response.status_code == 200
    assert [t.name for t in response.templates] == [
        "documents/_document_results.html",
        "documents/_document_card.html",
    ]
    content = response.content.decode()
    assert "<h1>Documents</h1>" not in content
    assert "document-filter-form" not in content
    assert document.title in content


@pytest.mark.django_db
def test_document_list_non_ajax_request_returns_the_full_page(auth_client, document):
    response = auth_client.get(reverse("document-list"))
    assert "documents/document_list.html" in [t.name for t in response.templates]
    assert "document-filter-form" in response.content.decode()


@pytest.mark.django_db
def test_document_list_ajax_and_non_ajax_responses_vary_on_the_ajax_header(auth_client):
    response = auth_client.get(reverse("document-list"))
    assert "X-Requested-With" in response["Vary"]


@pytest.mark.django_db
def test_document_list_ajax_request_still_applies_search_and_category(auth_client, category, document):
    other = Document.objects.create(title="Sans rapport", category=category)
    response = auth_client.get(
        reverse("document-list"),
        {"q": document.title, "category": str(category.pk)},
        headers={"x-requested-with": "XMLHttpRequest"},
    )
    documents = list(response.context["documents"])
    assert document in documents
    assert other not in documents


@pytest.mark.django_db
def test_document_list_pagination_is_inside_the_swapped_partial(auth_client, category):
    """The nav has to travel with the results, or filtering would leave the previous
    page's pagination behind."""
    for index in range(25):  # paginate_by = 20
        Document.objects.create(title=f"Document {index}", category=category)
    response = auth_client.get(reverse("document-list"), headers={"x-requested-with": "XMLHttpRequest"})
    assert "Suivant" in response.content.decode()


@pytest.mark.django_db
def test_document_list_search_button_is_removed(auth_client):
    content = auth_client.get(reverse("document-list")).content.decode()
    assert "Rechercher</button>" not in content


@pytest.mark.django_db
def test_document_list_form_declares_its_results_container(auth_client):
    content = auth_client.get(reverse("document-list")).content.decode()
    assert 'data-live-filter="#document-results"' in content


@pytest.mark.django_db
def test_add_document_link_keeps_the_active_category_while_filtering(auth_client, category):
    """The "+ Ajouter un document" button sits outside the swapped partial, so the
    script rebuilds its href -- otherwise picking a category live would silently stop
    pre-filling it on the creation form."""
    content = auth_client.get(reverse("document-list")).content.decode()
    assert 'data-live-filter-carry="category"' in content

    filtered = auth_client.get(reverse("document-list"), {"category": str(category.pk)}).content.decode()
    assert f"{reverse('document-create')}?category={category.pk}" in filtered


@pytest.mark.django_db
def test_document_list_clear_link_starts_hidden_when_no_filter_is_active(auth_client):
    content = auth_client.get(reverse("document-list")).content.decode()
    reset_tag = content[content.index("data-live-filter-reset") : content.index("data-live-filter-reset") + 200]
    assert "hidden" in reset_tag


@pytest.mark.django_db
def test_document_list_clear_link_is_visible_when_a_filter_is_active(auth_client):
    content = auth_client.get(reverse("document-list"), {"q": "acte"}).content.decode()
    reset_tag = content[content.index("data-live-filter-reset") : content.index("data-live-filter-reset") + 200]
    assert "hidden" not in reset_tag
