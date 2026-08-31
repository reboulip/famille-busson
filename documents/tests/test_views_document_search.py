import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from documents.models import Document, DocumentFile


def _uploaded(name="scan.pdf"):
    return SimpleUploadedFile(name=name, content=b"%PDF-fake", content_type="application/pdf")


@pytest.mark.django_db
def test_search_matches_by_title_only_no_badge(auth_client, category):
    Document.objects.create(title="Acte de mariage", category=category)
    response = auth_client.get(reverse("document-list"), {"q": "mariage"})
    content = response.content.decode()
    assert "Acte de mariage" in content
    assert "Trouvé dans le contenu" not in content


@pytest.mark.django_db
def test_search_matches_by_content_shows_badge(auth_client, category):
    document = Document.objects.create(title="Sans rapport", category=category)
    DocumentFile.objects.create(document=document, file=_uploaded(), extracted_text="mot-clé recherché ici")
    response = auth_client.get(reverse("document-list"), {"q": "recherché"})
    content = response.content.decode()
    assert "Sans rapport" in content
    assert "Trouvé dans le contenu" in content


@pytest.mark.django_db
def test_search_content_match_does_not_show_badge_when_query_also_in_title(auth_client, category):
    document = Document.objects.create(title="Facture EDF", category=category)
    DocumentFile.objects.create(document=document, file=_uploaded(), extracted_text="Facture EDF détails")
    response = auth_client.get(reverse("document-list"), {"q": "facture"})
    content = response.content.decode()
    assert "Facture EDF" in content
    assert "Trouvé dans le contenu" not in content


@pytest.mark.django_db
def test_search_no_match_excludes_document(auth_client, category):
    document = Document.objects.create(title="Sans rapport", category=category)
    DocumentFile.objects.create(document=document, file=_uploaded(), extracted_text="rien à voir")
    response = auth_client.get(reverse("document-list"), {"q": "introuvable"})
    assert "Sans rapport" not in response.content.decode()


@pytest.mark.django_db
def test_search_multi_file_document_content_match_no_duplicate_rows(auth_client, category):
    document = Document.objects.create(title="Dossier multi-fichiers", category=category)
    DocumentFile.objects.create(document=document, file=_uploaded("a.pdf"), extracted_text="cible trouvée ici")
    DocumentFile.objects.create(document=document, file=_uploaded("b.pdf"), extracted_text="cible aussi présente")
    response = auth_client.get(reverse("document-list"), {"q": "cible"})
    content = response.content.decode()
    assert content.count("Dossier multi-fichiers") == 1


@pytest.mark.django_db
def test_search_content_match_respects_category_access(auth_client, restricted_category):
    document = Document.objects.create(title="Doc restreint", category=restricted_category)
    DocumentFile.objects.create(document=document, file=_uploaded(), extracted_text="contenu secret recherché")
    response = auth_client.get(reverse("document-list"), {"q": "secret"})
    assert "Doc restreint" not in response.content.decode()


@pytest.mark.django_db
def test_search_content_match_included_for_member_with_access(auth_client, person, restricted_category, group):
    person.account.groups.add(group)
    document = Document.objects.create(title="Doc restreint", category=restricted_category)
    DocumentFile.objects.create(document=document, file=_uploaded(), extracted_text="contenu secret recherché")
    response = auth_client.get(reverse("document-list"), {"q": "secret"})
    assert "Doc restreint" in response.content.decode()


@pytest.mark.django_db
def test_search_content_match_pagination_still_correct(auth_client, category):
    for i in range(25):
        document = Document.objects.create(title=f"Document {i}", category=category)
        DocumentFile.objects.create(document=document, file=_uploaded(), extracted_text="correspondance partout")
    response = auth_client.get(reverse("document-list"), {"q": "correspondance"})
    content = response.content.decode()
    assert "q=correspondance" in content
    assert response.context["page_obj"].paginator.count == 25
