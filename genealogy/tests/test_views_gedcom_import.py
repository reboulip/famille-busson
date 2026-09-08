import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from annuaire.models import Person
from genealogy.models import GedcomImport

SIMPLE_GEDCOM = b"0 HEAD\n1 CHAR UTF-8\n0 @I1@ INDI\n1 NAME Jean /Busson/\n1 BIRT\n2 DATE 12 MAY 1950\n0 TRLR\n"


def _uploaded_gedcom(content: bytes = SIMPLE_GEDCOM) -> SimpleUploadedFile:
    return SimpleUploadedFile(name="test.ged", content=content, content_type="text/plain")


@pytest.mark.django_db
def test_upload_requires_staff(auth_client):
    response = auth_client.get(reverse("gedcom-import-upload"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_upload_requires_login(client):
    response = client.get(reverse("gedcom-import-upload"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_upload_get_200(staff_client):
    response = staff_client.get(reverse("gedcom-import-upload"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_upload_post_stages_and_redirects_to_review(staff_client):
    response = staff_client.post(reverse("gedcom-import-upload"), {"file": _uploaded_gedcom()})
    assert response.status_code == 302
    gedcom_import = GedcomImport.objects.get()
    assert gedcom_import.staged_individuals.count() == 1
    assert response.url == reverse("gedcom-import-review", kwargs={"pk": gedcom_import.pk})


@pytest.mark.django_db
def test_upload_post_rejects_ansel_and_stages_nothing(staff_client):
    content = b"0 HEAD\n1 CHAR ANSEL\n0 @I1@ INDI\n0 TRLR\n"
    response = staff_client.post(reverse("gedcom-import-upload"), {"file": _uploaded_gedcom(content)})
    assert response.status_code == 200
    assert not GedcomImport.objects.exists()


@pytest.mark.django_db
def test_upload_post_rejects_oversized_file(staff_client):
    from genealogy.gedcom.importer import MAX_FILE_BYTES

    big_content = b"0 HEAD\n" + b"1 NOTE x\n" * (MAX_FILE_BYTES // 8)
    response = staff_client.post(reverse("gedcom-import-upload"), {"file": _uploaded_gedcom(big_content)})
    assert response.status_code == 200
    assert not GedcomImport.objects.exists()


@pytest.mark.django_db
def test_review_requires_staff(auth_client):
    # Built directly, not via staff_client.post() -- auth_client and
    # staff_client share the same underlying test Client/session, so using
    # both in one test would just leave that one session logged in as
    # whichever fixture ran last.
    gedcom_import = GedcomImport.objects.create(raw_content=SIMPLE_GEDCOM.decode())
    response = auth_client.get(reverse("gedcom-import-review", kwargs={"pk": gedcom_import.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_review_get_shows_staged_individual(staff_client):
    staff_client.post(reverse("gedcom-import-upload"), {"file": _uploaded_gedcom()})
    gedcom_import = GedcomImport.objects.get()
    response = staff_client.get(reverse("gedcom-import-review", kwargs={"pk": gedcom_import.pk}))
    assert response.status_code == 200
    assert "Jean" in response.content.decode()


@pytest.mark.django_db
def test_review_post_saves_decision(staff_client):
    staff_client.post(reverse("gedcom-import-upload"), {"file": _uploaded_gedcom()})
    gedcom_import = GedcomImport.objects.get()
    staged = gedcom_import.staged_individuals.get()
    staff_client.post(
        reverse("gedcom-import-review", kwargs={"pk": gedcom_import.pk}),
        {f"decision_{staged.pk}": "skip"},
    )
    staged.refresh_from_db()
    assert staged.decision == "skip"


@pytest.mark.django_db
def test_review_post_saves_merge_decision(staff_client, person):
    staff_client.post(reverse("gedcom-import-upload"), {"file": _uploaded_gedcom()})
    gedcom_import = GedcomImport.objects.get()
    staged = gedcom_import.staged_individuals.get()
    staff_client.post(
        reverse("gedcom-import-review", kwargs={"pk": gedcom_import.pk}),
        {f"decision_{staged.pk}": f"merge:{person.pk}"},
    )
    staged.refresh_from_db()
    assert staged.decision == "merge"
    assert staged.match_person_id == person.pk


@pytest.mark.django_db
def test_apply_requires_staff(auth_client):
    gedcom_import = GedcomImport.objects.create(raw_content=SIMPLE_GEDCOM.decode())
    response = auth_client.post(reverse("gedcom-import-apply", kwargs={"pk": gedcom_import.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_apply_creates_the_person(staff_client):
    staff_client.post(reverse("gedcom-import-upload"), {"file": _uploaded_gedcom()})
    gedcom_import = GedcomImport.objects.get()
    response = staff_client.post(reverse("gedcom-import-apply", kwargs={"pk": gedcom_import.pk}))
    assert response.status_code == 302
    assert Person.objects.filter(first_name="Jean", last_name="Busson").exists()
    gedcom_import.refresh_from_db()
    assert gedcom_import.status == "applied"


@pytest.mark.django_db
def test_apply_refuses_when_already_applied(staff_client):
    staff_client.post(reverse("gedcom-import-upload"), {"file": _uploaded_gedcom()})
    gedcom_import = GedcomImport.objects.get()
    staff_client.post(reverse("gedcom-import-apply", kwargs={"pk": gedcom_import.pk}))
    person_count = Person.objects.count()
    staff_client.post(reverse("gedcom-import-apply", kwargs={"pk": gedcom_import.pk}))
    assert Person.objects.count() == person_count


@pytest.mark.django_db
def test_discard_requires_staff(auth_client):
    gedcom_import = GedcomImport.objects.create(raw_content=SIMPLE_GEDCOM.decode())
    response = auth_client.post(reverse("gedcom-import-discard", kwargs={"pk": gedcom_import.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_discard_deletes_the_import(staff_client):
    staff_client.post(reverse("gedcom-import-upload"), {"file": _uploaded_gedcom()})
    gedcom_import = GedcomImport.objects.get()
    response = staff_client.post(reverse("gedcom-import-discard", kwargs={"pk": gedcom_import.pk}))
    assert response.status_code == 302
    assert not GedcomImport.objects.filter(pk=gedcom_import.pk).exists()
    assert not Person.objects.filter(first_name="Jean", last_name="Busson").exists()
