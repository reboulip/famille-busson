import pytest
from django.urls import reverse

from annuaire.models import Relation


@pytest.mark.django_db
def test_gedcom_export_requires_login(client, person):
    response = client.get(reverse("gedcom-export"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_gedcom_export_returns_gedcom_content_type(auth_client, person):
    response = auth_client.get(reverse("gedcom-export"))
    assert response.status_code == 200
    assert response["Content-Type"] == "application/x-gedcom"
    assert response["Content-Disposition"].startswith("attachment;")
    assert response["Content-Disposition"].endswith('.ged"')


@pytest.mark.django_db
def test_gedcom_export_with_no_ids_exports_everyone(auth_client, person, other_person):
    response = auth_client.get(reverse("gedcom-export"))
    content = response.content.decode()
    assert f"@I{person.pk}@" in content
    assert f"@I{other_person.pk}@" in content


@pytest.mark.django_db
def test_gedcom_export_scopes_to_given_ids(auth_client, person, other_person):
    response = auth_client.get(reverse("gedcom-export"), {"ids": [person.pk]})
    content = response.content.decode()
    assert f"@I{person.pk}@" in content
    assert f"@I{other_person.pk}@" not in content


@pytest.mark.django_db
def test_gedcom_export_ignores_invalid_ids(auth_client, person):
    response = auth_client.get(reverse("gedcom-export"), {"ids": ["not-a-number", str(person.pk)]})
    assert response.status_code == 200
    assert f"@I{person.pk}@" in response.content.decode()


@pytest.mark.django_db
def test_gedcom_export_includes_marriage_data(auth_client, person, other_person):
    Relation.objects.create(person1=person, person2=other_person, relationship_type=1)
    response = auth_client.get(reverse("gedcom-export"))
    content = response.content.decode()
    assert " FAM\r\n" in content
