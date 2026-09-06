import datetime

import pytest
from django.urls import reverse

from documents.models import Document


@pytest.mark.django_db
def test_document_default_sort_is_most_recently_deposited_first(auth_client, category, document):
    second = Document.objects.create(title="Second", category=category)
    third = Document.objects.create(title="Third", category=category)
    response = auth_client.get(reverse("document-list"))
    documents = list(response.context["documents"])
    assert documents.index(third) < documents.index(second) < documents.index(document)


@pytest.mark.django_db
def test_document_sort_title_asc(auth_client, category):
    a = Document.objects.create(title="Acte", category=category)
    z = Document.objects.create(title="Zone", category=category)
    response = auth_client.get(reverse("document-list"), {"sort": "title_asc"})
    documents = list(response.context["documents"])
    assert documents.index(a) < documents.index(z)


@pytest.mark.django_db
def test_document_sort_title_desc(auth_client, category):
    a = Document.objects.create(title="Acte", category=category)
    z = Document.objects.create(title="Zone", category=category)
    response = auth_client.get(reverse("document-list"), {"sort": "title_desc"})
    documents = list(response.context["documents"])
    assert documents.index(z) < documents.index(a)


@pytest.mark.django_db
def test_document_sort_redactor_asc_puts_null_redactor_last(auth_client, category, person):
    with_redactor = Document.objects.create(title="Avec rédacteur", category=category, redactor=person)
    without_redactor = Document.objects.create(title="Sans rédacteur", category=category)
    response = auth_client.get(reverse("document-list"), {"sort": "redactor_asc"})
    documents = list(response.context["documents"])
    assert documents.index(with_redactor) < documents.index(without_redactor)


@pytest.mark.django_db
def test_document_sort_date_asc_puts_null_document_date_last(auth_client, category):
    with_date = Document.objects.create(title="Avec date", category=category, document_date=datetime.date(1990, 1, 1))
    without_date = Document.objects.create(title="Sans date", category=category)
    response = auth_client.get(reverse("document-list"), {"sort": "date_asc"})
    documents = list(response.context["documents"])
    assert documents.index(with_date) < documents.index(without_date)


@pytest.mark.django_db
def test_document_sort_unknown_value_falls_back_to_default(auth_client):
    response = auth_client.get(reverse("document-list"), {"sort": "bogus"})
    assert response.status_code == 200
    assert response.context["sort"] == "recent"


@pytest.mark.django_db
def test_document_sort_context_reflects_selected_value(auth_client):
    response = auth_client.get(reverse("document-list"), {"sort": "title_asc"})
    assert response.context["sort"] == "title_asc"


@pytest.mark.django_db
def test_document_sort_combines_with_search_query(auth_client, category):
    a = Document.objects.create(title="Acte de Busson", category=category)
    z = Document.objects.create(title="Zone de Busson", category=category)
    response = auth_client.get(reverse("document-list"), {"q": "Busson", "sort": "title_asc"})
    documents = list(response.context["documents"])
    assert a in documents
    assert z in documents
    assert documents.index(a) < documents.index(z)


@pytest.mark.django_db
def test_document_sort_select_marks_current_option_selected(auth_client):
    response = auth_client.get(reverse("document-list"), {"sort": "title_desc"})
    content = response.content.decode()
    assert 'value="title_desc" selected' in content


# ---------------------------------------------------------------------------
# Filtering by redactor and year
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_document_filter_by_redactor(auth_client, category, person, other_person):
    mine = Document.objects.create(title="Mien", category=category, redactor=person)
    other = Document.objects.create(title="Autre", category=category, redactor=other_person)
    response = auth_client.get(reverse("document-list"), {"redactor": str(person.pk)})
    documents = list(response.context["documents"])
    assert mine in documents
    assert other not in documents


@pytest.mark.django_db
def test_document_filter_by_year(auth_client, category):
    this_year = Document.objects.create(
        title="Cette année", category=category, document_date=datetime.date(2020, 6, 1)
    )
    other_year = Document.objects.create(
        title="Autre année", category=category, document_date=datetime.date(2019, 6, 1)
    )
    response = auth_client.get(reverse("document-list"), {"year": "2020"})
    documents = list(response.context["documents"])
    assert this_year in documents
    assert other_year not in documents


@pytest.mark.django_db
def test_document_filter_redactors_list_is_scoped_to_accessible_documents(auth_client, category, person):
    Document.objects.create(title="Acte", category=category, redactor=person)
    response = auth_client.get(reverse("document-list"))
    assert person in list(response.context["filter_redactors"])


@pytest.mark.django_db
def test_document_filter_years_list_is_scoped_to_accessible_documents(auth_client, category):
    Document.objects.create(title="Acte", category=category, document_date=datetime.date(2021, 1, 1))
    response = auth_client.get(reverse("document-list"))
    years = [d.year for d in response.context["filter_years"]]
    assert 2021 in years
