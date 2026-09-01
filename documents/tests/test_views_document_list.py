import pytest
from django.urls import reverse

from documents.models import Document

LOGIN_URL = "/annuaire/login/"


@pytest.mark.django_db
def test_document_list_requires_login(client):
    response = client.get(reverse("document-list"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_document_list_shows_accessible_document(auth_client, document):
    response = auth_client.get(reverse("document-list"))
    assert document.title in response.content.decode()


@pytest.mark.django_db
def test_document_list_excludes_documents_in_restricted_category(auth_client, category, restricted_category):
    Document.objects.create(title="Doc public", category=category)
    Document.objects.create(title="Doc restreint", category=restricted_category)
    response = auth_client.get(reverse("document-list"))
    content = response.content.decode()
    assert "Doc public" in content
    assert "Doc restreint" not in content


@pytest.mark.django_db
def test_document_list_includes_restricted_document_for_member(auth_client, person, restricted_category, group):
    person.account.groups.add(group)
    Document.objects.create(title="Doc restreint", category=restricted_category)
    response = auth_client.get(reverse("document-list"))
    assert "Doc restreint" in response.content.decode()


@pytest.mark.django_db
def test_staff_sees_all_documents_regardless_of_category_access(staff_client, restricted_category):
    Document.objects.create(title="Doc restreint", category=restricted_category)
    response = staff_client.get(reverse("document-list"))
    assert "Doc restreint" in response.content.decode()


@pytest.mark.django_db
def test_document_list_search_by_title(auth_client, category):
    Document.objects.create(title="Acte de mariage", category=category)
    Document.objects.create(title="Facture EDF", category=category)
    response = auth_client.get(reverse("document-list"), {"q": "mariage"})
    content = response.content.decode()
    assert "Acte de mariage" in content
    assert "Facture EDF" not in content


@pytest.mark.django_db
def test_document_list_search_by_description(auth_client, category):
    Document.objects.create(title="Sans titre utile", description="contrat de bail", category=category)
    response = auth_client.get(reverse("document-list"), {"q": "bail"})
    assert "Sans titre utile" in response.content.decode()


@pytest.mark.django_db
def test_document_list_filters_by_category(auth_client, category):
    from documents.models import Category

    other_category = Category.objects.create(name="Autre")
    Document.objects.create(title="Dans la bonne catégorie", category=category)
    Document.objects.create(title="Dans une autre catégorie", category=other_category)
    response = auth_client.get(reverse("document-list"), {"category": str(category.pk)})
    content = response.content.decode()
    assert "Dans la bonne catégorie" in content
    assert "Dans une autre catégorie" not in content


@pytest.mark.django_db
def test_document_list_pagination_preserves_query(auth_client, category):
    for i in range(25):
        Document.objects.create(title=f"Document {i} correspondance", category=category)
    response = auth_client.get(reverse("document-list"), {"q": "correspondance"})
    content = response.content.decode()
    assert "q=correspondance" in content


@pytest.mark.django_db
def test_document_list_filter_categories_excludes_restricted_for_non_member(auth_client, restricted_category):
    response = auth_client.get(reverse("document-list"))
    assert restricted_category not in response.context["filter_categories"]


@pytest.mark.django_db
def test_document_card_strips_markdown_from_description(auth_client, category):
    Document.objects.create(
        title="Avec markdown", description="**gras** et [lien](https://example.com)", category=category
    )
    response = auth_client.get(reverse("document-list"))
    content = response.content.decode()
    assert "gras" in content
    assert "<strong>" not in content
    assert "[lien]" not in content
