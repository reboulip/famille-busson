import json

import pytest
from django.contrib.auth.models import Group

from publications.bulletin_access import accessible_bulletins, user_can_access_bulletin
from publications.bulletin_import import apply_bulletin_import, partial_date_to_date
from publications.models import Bulletin, BulletinImport
from publications.tests.conftest import DEMO_BULLETIN_DIR
from publications.tests.conftest import add_bulletin_import_image as _add_image


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1995", "1995-01-01"),
        ("1995-04", "1995-04-01"),
        ("2014-04-29", "2014-04-29"),
    ],
)
def test_partial_date_to_date(value, expected):
    assert partial_date_to_date(value).isoformat() == expected


@pytest.fixture
def demo_bulletin_data():
    return json.loads((DEMO_BULLETIN_DIR / "bulletin.json").read_text(encoding="utf-8"))


@pytest.fixture
def demo_bulletin_import(db, demo_bulletin_data):
    return BulletinImport.objects.create(
        original_filename="demo-001.zip",
        document_id=demo_bulletin_data["id"],
        data=demo_bulletin_data,
        validation_report={"errors": [], "warnings": [], "stats": {}},
    )


@pytest.mark.django_db
def test_apply_bulletin_import_creates_bulletin(demo_bulletin_import, demo_bulletin_data, person):
    for img in demo_bulletin_data["images"]:
        _add_image(demo_bulletin_import, img["id"])

    bulletin = apply_bulletin_import(demo_bulletin_import, person)

    assert bulletin.document_id == demo_bulletin_data["id"]
    assert bulletin.title == demo_bulletin_data["title"]
    assert bulletin.images.count() == len(demo_bulletin_data["images"])
    demo_bulletin_import.refresh_from_db()
    assert demo_bulletin_import.status == "applied"


@pytest.mark.django_db
def test_reimporting_same_document_id_updates_in_place(demo_bulletin_import, demo_bulletin_data, person):
    for img in demo_bulletin_data["images"]:
        _add_image(demo_bulletin_import, img["id"])
    first = apply_bulletin_import(demo_bulletin_import, person)

    second_import = BulletinImport.objects.create(
        original_filename="demo-001-v2.zip",
        document_id=demo_bulletin_data["id"],
        data={**demo_bulletin_data, "title": "Titre corrigé"},
        validation_report={"errors": [], "warnings": [], "stats": {}},
    )
    for img in demo_bulletin_data["images"]:
        _add_image(second_import, img["id"])

    second = apply_bulletin_import(second_import, person)

    assert second.pk == first.pk
    assert second.title == "Titre corrigé"
    assert Bulletin.objects.count() == 1
    assert second.images.count() == len(demo_bulletin_data["images"])


@pytest.mark.django_db
def test_bulletin_import_cannot_publish_with_errors(demo_bulletin_import):
    demo_bulletin_import.validation_report = {"errors": ["something is wrong"], "warnings": [], "stats": {}}
    demo_bulletin_import.save()
    assert demo_bulletin_import.can_publish is False


@pytest.mark.django_db
def test_bulletin_group_access(demo_bulletin_import, demo_bulletin_data, person, other_person):
    for img in demo_bulletin_data["images"]:
        _add_image(demo_bulletin_import, img["id"])
    bulletin = apply_bulletin_import(demo_bulletin_import, person)

    family = Group.objects.create(name="Famille restreinte")
    bulletin.groups.add(family)

    assert not user_can_access_bulletin(other_person.account, bulletin)
    other_person.account.groups.add(family)
    assert user_can_access_bulletin(other_person.account, bulletin)
    assert bulletin in accessible_bulletins(other_person.account)


@pytest.mark.django_db
def test_bulletin_without_groups_is_public(demo_bulletin_import, demo_bulletin_data, person, other_person):
    for img in demo_bulletin_data["images"]:
        _add_image(demo_bulletin_import, img["id"])
    bulletin = apply_bulletin_import(demo_bulletin_import, person)
    assert user_can_access_bulletin(other_person.account, bulletin)
