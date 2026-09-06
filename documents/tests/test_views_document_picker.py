"""Phase 8.4 — the AJAX document picker backing the publication form's "Documents
liés" field (#133)."""

import pytest
from django.urls import reverse

from documents.models import Document


@pytest.mark.django_db
def test_document_search_requires_two_characters(auth_client):
    response = auth_client.get(reverse("document-search-ajax"), {"q": "a"})
    assert response.json() == {"results": []}


@pytest.mark.django_db
def test_document_search_returns_matching_documents(auth_client, document):
    response = auth_client.get(reverse("document-search-ajax"), {"q": document.title[:4]})
    results = response.json()["results"]
    assert {"id": document.pk, "name": document.title} in results


@pytest.mark.django_db
def test_document_search_excludes_ids_in_the_exclude_param(auth_client, document):
    response = auth_client.get(reverse("document-search-ajax"), {"q": document.title[:4], "exclude": str(document.pk)})
    assert response.json()["results"] == []


@pytest.mark.django_db
def test_document_search_hides_restricted_documents(auth_client, category, restricted_category):
    accessible = Document.objects.create(title="Acte accessible", category=category)
    restricted = Document.objects.create(title="Acte restreint", category=restricted_category)
    response = auth_client.get(reverse("document-search-ajax"), {"q": "Acte"})
    ids = {r["id"] for r in response.json()["results"]}
    assert accessible.pk in ids
    assert restricted.pk not in ids


@pytest.mark.django_db
def test_document_search_requires_login(client, document):
    response = client.get(reverse("document-search-ajax"), {"q": document.title[:4]})
    assert response.status_code == 302
