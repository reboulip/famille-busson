import io
import json
import zipfile

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from annuaire.models import Person
from annuaire.personal_data import PERSONAL_DATA_CATEGORIES, PERSONAL_DATA_HIDDEN_RELATIONS, PERSONAL_DATA_RELATIONS
from documents.models import Category, Document
from photos.models import Album, Photo

LOGIN_URL = "/annuaire/login/"


@pytest.fixture(autouse=True)
def use_tmp_media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    settings.DOCUMENTS_ROOT = tmp_path / "documents_data"
    settings.PHOTOS_ROOT = tmp_path / "documents_data" / "photos"


def _uploaded_image(name="photo.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="blue").save(buffer, format="PNG")
    return SimpleUploadedFile(name=name, content=buffer.getvalue(), content_type="image/png")


# --- Meta-guard: fails if a future FK/M2M onto Person escapes the export ----


def test_personal_data_meta_guard_covers_every_relation():
    for f in Person._meta.get_fields(include_hidden=True):
        if not (f.is_relation and f.auto_created and not f.concrete):
            continue
        if f.related_model._meta.auto_created:
            continue  # the auto-created through table of a plain M2M
        if getattr(f, "hidden", False):
            key = (f.related_model._meta.app_label, f.related_model._meta.model_name, f.field.name)
            assert key in PERSONAL_DATA_HIDDEN_RELATIONS, f"unhandled hidden relation: {key}"
        else:
            accessor = f.get_accessor_name()
            assert accessor in PERSONAL_DATA_RELATIONS, f"unhandled relation: {accessor}"

    for f in Person._meta.many_to_many:
        assert f.name in PERSONAL_DATA_RELATIONS, f"unhandled forward M2M: {f.name}"


def test_every_category_key_is_unique():
    keys = [category.key for category in PERSONAL_DATA_CATEGORIES]
    assert len(keys) == len(set(keys))


# --- View permissions ---------------------------------------------------


@pytest.mark.django_db
def test_export_requires_login(client, person):
    response = client.get(reverse("person-data-export", args=[person.pk]))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_self_can_export_own_data(auth_client, person):
    response = auth_client.get(reverse("person-data-export", args=[person.pk]))
    assert response.status_code == 200
    assert response["Content-Type"] == "application/zip"
    assert response["Content-Disposition"].startswith("attachment;")
    assert f"mes-donnees-{person.pk}-" in response["Content-Disposition"]


@pytest.mark.django_db
def test_unrelated_member_cannot_export_someone_elses_data(auth_client, other_person):
    response = auth_client.get(reverse("person-data-export", args=[other_person.pk]))
    assert response.status_code == 403


@pytest.mark.django_db
def test_staff_can_export_anyones_data(staff_client, person):
    response = staff_client.get(reverse("person-data-export", args=[person.pk]))
    assert response.status_code == 200


@pytest.mark.django_db
def test_owner_of_accountless_profile_can_export_its_data(auth_client, owned_person):
    response = auth_client.get(reverse("person-data-export", args=[owned_person.pk]))
    assert response.status_code == 200


# --- Archive contents -----------------------------------------------------


@pytest.mark.django_db
def test_archive_contains_json_and_readme(auth_client, person):
    response = auth_client.get(reverse("person-data-export", args=[person.pk]))
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = archive.namelist()
    assert "donnees.json" in names
    assert "LISEZ-MOI.txt" in names

    payload = json.loads(archive.read("donnees.json"))
    assert payload["personne"]["pk"] == person.pk
    assert set(payload["categories"]) == {category.key for category in PERSONAL_DATA_CATEGORIES}


@pytest.mark.django_db
def test_archive_profile_category_reflects_person_fields(auth_client, person):
    person.phone_number = "0600000000"
    person.save(update_fields=["phone_number"])
    response = auth_client.get(reverse("person-data-export", args=[person.pk]))
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    payload = json.loads(archive.read("donnees.json"))
    (profil,) = payload["categories"]["profil"]
    assert profil["prenom"] == "Alice"
    assert profil["nom"] == "Busson"
    assert profil["telephone"] == "0600000000"


@pytest.mark.django_db
def test_archive_includes_presences(auth_client, person, presence):
    response = auth_client.get(reverse("person-data-export", args=[person.pk]))
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    payload = json.loads(archive.read("donnees.json"))
    (row,) = payload["categories"]["presences"]
    assert row["lieu"] == presence.place.name
    assert row["arrivee"] == presence.start_date.isoformat()


@pytest.mark.django_db
def test_archive_documents_are_scoped_to_viewer_access(auth_client, person, owned_person):
    group = Group.objects.create(name="SCI grand chalet")
    restricted_category = Category.objects.create(name="Documents SCI")
    restricted_category.groups.add(group)
    Document.objects.create(title="Acte restreint", category=restricted_category, uploaded_by=owned_person)

    # `person` owns `owned_person` but isn't in the restricting group, so the
    # export -- scoped to the *viewer's* access, not the subject's -- must not
    # leak the restricted document's existence.
    response = auth_client.get(reverse("person-data-export", args=[owned_person.pk]))
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    payload = json.loads(archive.read("donnees.json"))
    assert payload["categories"]["documents"] == []


@pytest.mark.django_db
def test_archive_includes_accessible_photo_person_is_tagged_in(auth_client, person):
    from photos.models import PersonTag

    album = Album.objects.create(title="Vacances")
    photo = Photo.objects.create(album=album, file=_uploaded_image())
    PersonTag.objects.create(photo=photo, person=person)

    response = auth_client.get(reverse("person-data-export", args=[person.pk]))
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    payload = json.loads(archive.read("donnees.json"))
    roles = [row["role"] for row in payload["categories"]["photos"]]
    assert "identifié·e sur une photo" in roles


@pytest.mark.django_db
def test_archive_embeds_profile_photo_bytes(auth_client, person):
    person.profile_photo = _uploaded_image()
    person.save(update_fields=["profile_photo"])

    response = auth_client.get(reverse("person-data-export", args=[person.pk]))
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    assert any(name.startswith("photo-profil.") for name in archive.namelist())


@pytest.mark.django_db
def test_export_button_shown_only_to_people_who_can_edit(auth_client, other_person):
    response = auth_client.get(reverse("personne-detail", args=[other_person.pk]))
    assert reverse("person-data-export", args=[other_person.pk]) not in response.content.decode()


@pytest.mark.django_db
def test_export_button_shown_on_own_profile(auth_client, person):
    response = auth_client.get(reverse("personne-detail", args=[person.pk]))
    assert reverse("person-data-export", args=[person.pk]) in response.content.decode()
