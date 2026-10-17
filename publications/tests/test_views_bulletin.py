import io
import json

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from publications.bulletin_import import apply_bulletin_import
from publications.models import Bulletin, BulletinImport
from publications.tests.conftest import DEMO_BULLETIN_DIR
from publications.tests.conftest import add_bulletin_import_image as _add_image


@pytest.fixture
def demo_bulletin_data():
    return json.loads((DEMO_BULLETIN_DIR / "bulletin.json").read_text(encoding="utf-8"))


@pytest.fixture
def bulletin(db, demo_bulletin_data, person):
    bulletin_import = BulletinImport.objects.create(
        original_filename="demo-001.zip",
        document_id=demo_bulletin_data["id"],
        data=demo_bulletin_data,
        validation_report={"errors": [], "warnings": [], "stats": {}},
    )
    for img in demo_bulletin_data["images"]:
        _add_image(bulletin_import, img["id"])
    return apply_bulletin_import(bulletin_import, person)


@pytest.mark.django_db
def test_bulletin_list_requires_login(client):
    response = client.get(reverse("bulletin-list"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_bulletin_list_shows_published_bulletin(auth_client, bulletin):
    response = auth_client.get(reverse("bulletin-list"))
    assert response.status_code == 200
    assert bulletin.title in response.content.decode()


@pytest.mark.django_db
def test_bulletin_list_hides_restricted_bulletin_from_outsider(auth_client, bulletin):
    family = Group.objects.create(name="Cercle restreint")
    bulletin.groups.add(family)
    response = auth_client.get(reverse("bulletin-list"))
    assert bulletin.title not in response.content.decode()


@pytest.mark.django_db
def test_bulletin_detail_renders(auth_client, bulletin):
    response = auth_client.get(reverse("bulletin-detail", kwargs={"pk": bulletin.pk}))
    assert response.status_code == 200
    assert bulletin.title in response.content.decode()


@pytest.mark.django_db
def test_bulletin_detail_denies_outsider(auth_client, bulletin):
    family = Group.objects.create(name="Cercle restreint")
    bulletin.groups.add(family)
    response = auth_client.get(reverse("bulletin-detail", kwargs={"pk": bulletin.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_bulletin_detail_allows_member(auth_client, person, bulletin):
    family = Group.objects.create(name="Cercle restreint")
    bulletin.groups.add(family)
    person.account.groups.add(family)
    response = auth_client.get(reverse("bulletin-detail", kwargs={"pk": bulletin.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_bulletin_import_upload_requires_staff(auth_client):
    response = auth_client.get(reverse("bulletin-import-upload"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_bulletin_import_upload_get(staff_client):
    response = staff_client.get(reverse("bulletin-import-upload"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_bulletin_import_upload_valid_package_redirects_to_preview(staff_client, demo_bulletin_zip):
    response = staff_client.post(reverse("bulletin-import-upload"), {"package": demo_bulletin_zip})
    assert response.status_code == 302
    bulletin_import = BulletinImport.objects.get()
    assert bulletin_import.document_id == "demo-001"
    assert bulletin_import.images.count() > 0
    assert response.url == reverse("bulletin-import-preview", kwargs={"pk": bulletin_import.pk})


@pytest.mark.django_db
def test_bulletin_import_upload_bad_zip_shows_form_error(staff_client):
    bad_zip = io.BytesIO(b"not a zip")
    bad_zip.name = "bad.zip"
    response = staff_client.post(reverse("bulletin-import-upload"), {"package": bad_zip})
    assert response.status_code == 200
    assert not BulletinImport.objects.exists()
    assert "package" in response.context["form"].errors


@pytest.mark.django_db
def test_bulletin_import_preview_shows_validation_report(staff_client, demo_bulletin_data):
    bulletin_import = BulletinImport.objects.create(
        original_filename="demo-001.zip",
        document_id=demo_bulletin_data["id"],
        data=demo_bulletin_data,
        validation_report={"errors": ["quelque chose ne va pas"], "warnings": [], "stats": {}},
    )
    response = staff_client.get(reverse("bulletin-import-preview", kwargs={"pk": bulletin_import.pk}))
    assert response.status_code == 200
    assert "quelque chose ne va pas" in response.content.decode()


@pytest.mark.django_db
def test_bulletin_import_apply_publishes_bulletin(staff_client, demo_bulletin_data):
    bulletin_import = BulletinImport.objects.create(
        original_filename="demo-001.zip",
        document_id=demo_bulletin_data["id"],
        data=demo_bulletin_data,
        validation_report={"errors": [], "warnings": [], "stats": {}},
    )
    for img in demo_bulletin_data["images"]:
        _add_image(bulletin_import, img["id"])

    response = staff_client.post(reverse("bulletin-import-apply", kwargs={"pk": bulletin_import.pk}))

    assert response.status_code == 302
    assert Bulletin.objects.filter(document_id="demo-001").exists()
    bulletin_import.refresh_from_db()
    assert bulletin_import.status == "applied"


@pytest.mark.django_db
def test_bulletin_import_apply_blocked_when_errors(staff_client, demo_bulletin_data):
    bulletin_import = BulletinImport.objects.create(
        original_filename="demo-001.zip",
        document_id=demo_bulletin_data["id"],
        data=demo_bulletin_data,
        validation_report={"errors": ["cassé"], "warnings": [], "stats": {}},
    )
    response = staff_client.post(reverse("bulletin-import-apply", kwargs={"pk": bulletin_import.pk}))
    assert response.status_code == 302
    assert not Bulletin.objects.exists()


@pytest.mark.django_db
def test_bulletin_import_discard_deletes_import(staff_client, demo_bulletin_data):
    bulletin_import = BulletinImport.objects.create(
        original_filename="demo-001.zip",
        document_id=demo_bulletin_data["id"],
        data=demo_bulletin_data,
        validation_report={"errors": [], "warnings": [], "stats": {}},
    )
    response = staff_client.post(reverse("bulletin-import-discard", kwargs={"pk": bulletin_import.pk}))
    assert response.status_code == 302
    assert not BulletinImport.objects.exists()


@pytest.mark.django_db
def test_reimport_updates_existing_bulletin_via_views(staff_client, bulletin, demo_bulletin_zip_bytes):
    upload = SimpleUploadedFile("demo-001-v2.zip", demo_bulletin_zip_bytes, content_type="application/zip")
    response = staff_client.post(reverse("bulletin-import-upload"), {"package": upload})
    assert response.status_code == 302
    new_import = BulletinImport.objects.latest("uploaded_at")

    apply_response = staff_client.post(reverse("bulletin-import-apply", kwargs={"pk": new_import.pk}))
    assert apply_response.status_code == 302
    assert Bulletin.objects.count() == 1
