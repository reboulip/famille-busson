from decimal import Decimal

import pytest

from annuaire.map_data import build_chalet_map_groups, build_person_map_groups
from annuaire.models import Chalet


@pytest.mark.django_db
def test_empty_db_returns_no_groups():
    assert build_person_map_groups() == []
    assert build_chalet_map_groups() == []


@pytest.mark.django_db
def test_single_person_group_matches_old_flat_shape(person):
    person.latitude = Decimal("49.031624")
    person.longitude = Decimal("2.062821")
    person.save()
    groups = build_person_map_groups()
    assert len(groups) == 1
    group = groups[0]
    assert group["lat"] == pytest.approx(49.031624)
    assert group["lon"] == pytest.approx(2.062821)
    assert len(group["entries"]) == 1
    entry = group["entries"][0]
    assert entry["name"] == f"{person.first_name} {person.last_name}"
    assert entry["url"]
    assert entry["avatar"]


@pytest.mark.django_db
def test_persons_without_coordinates_are_excluded(person):
    assert build_person_map_groups() == []


@pytest.mark.django_db
def test_two_persons_at_same_address_group_together(person, other_person):
    person.latitude = Decimal("49.031624")
    person.longitude = Decimal("2.062821")
    person.save()
    other_person.latitude = Decimal("49.031624")
    other_person.longitude = Decimal("2.062821")
    other_person.save()
    groups = build_person_map_groups()
    assert len(groups) == 1
    assert len(groups[0]["entries"]) == 2


@pytest.mark.django_db
def test_coordinates_differing_past_5_decimals_do_not_group(person, other_person):
    person.latitude = Decimal("49.031624")
    person.longitude = Decimal("2.062821")
    person.save()
    other_person.latitude = Decimal("49.031699")  # differs at the 5th decimal (~8cm... actually >1.1m)
    other_person.longitude = Decimal("2.062821")
    other_person.save()
    groups = build_person_map_groups()
    assert len(groups) == 2


@pytest.mark.django_db
def test_person_groups_sorted_by_last_name_first_name(person, other_person):
    # person = Alice Busson, other_person = Bob Busson (see conftest.py)
    person.latitude = Decimal("1.0")
    person.longitude = Decimal("1.0")
    person.save()
    other_person.latitude = Decimal("2.0")
    other_person.longitude = Decimal("2.0")
    other_person.save()
    groups = build_person_map_groups()
    assert [g["entries"][0]["name"] for g in groups] == sorted([g["entries"][0]["name"] for g in groups])


@pytest.mark.django_db
def test_chalet_without_photo_uses_emoji_sentinel(chalet):
    chalet.latitude = Decimal("46.096")
    chalet.longitude = Decimal("7.228")
    chalet.save()
    groups = build_chalet_map_groups()
    assert groups[0]["entries"][0]["avatar"] == "emoji::🏔️"


@pytest.mark.django_db
def test_chalets_without_coordinates_are_excluded():
    Chalet.objects.create(name="Sans coordonnées", address="Quelque part")
    assert build_chalet_map_groups() == []


@pytest.mark.django_db
def test_two_chalets_at_same_address_group_together():
    Chalet.objects.create(
        name="Chalet A", address="1 rue de la Montagne", latitude=Decimal("45.9"), longitude=Decimal("6.9")
    )
    Chalet.objects.create(
        name="Chalet B", address="1 rue de la Montagne", latitude=Decimal("45.9"), longitude=Decimal("6.9")
    )
    groups = build_chalet_map_groups()
    assert len(groups) == 1
    assert len(groups[0]["entries"]) == 2
