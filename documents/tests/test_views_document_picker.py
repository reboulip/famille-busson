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


@pytest.mark.django_db
def test_document_search_matches_substring_not_just_prefix(auth_client, category):
    document = Document.objects.create(title="Contrat de vente du chalet", category=category)
    response = auth_client.get(reverse("document-search-ajax"), {"q": "vente"})
    ids = {r["id"] for r in response.json()["results"]}
    assert document.pk in ids


@pytest.mark.django_db
def test_document_search_matches_tokens_in_any_order(auth_client, category):
    document = Document.objects.create(title="Contrat de vente du chalet", category=category)
    response = auth_client.get(reverse("document-search-ajax"), {"q": "vente chalet"})
    ids = {r["id"] for r in response.json()["results"]}
    assert document.pk in ids


@pytest.mark.django_db
def test_document_search_requires_every_token_to_match(auth_client, category):
    Document.objects.create(title="Contrat de vente du chalet", category=category)
    response = auth_client.get(reverse("document-search-ajax"), {"q": "vente maison"})
    assert response.json()["results"] == []


@pytest.mark.django_db
def test_document_search_ranks_prefix_matches_first(auth_client, category):
    mid_match = Document.objects.create(title="Autre acte administratif", category=category)
    prefix_match = Document.objects.create(title="Acte de naissance", category=category)
    response = auth_client.get(reverse("document-search-ajax"), {"q": "acte"})
    ids = [r["id"] for r in response.json()["results"]]
    assert ids.index(prefix_match.pk) < ids.index(mid_match.pk)
