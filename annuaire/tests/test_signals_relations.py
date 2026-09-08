import datetime

import pytest

from annuaire.models import Relation


@pytest.mark.django_db
def test_marriage_fields_mirrored_onto_inverse_relation(person, other_person):
    Relation.objects.create(
        person1=person,
        person2=other_person,
        relationship_type=0,
        start_date=datetime.date(1990, 5, 12),
        marriage_place="Lyon",
        end_date=datetime.date(2010, 1, 1),
    )
    inverse = Relation.objects.get(person1=other_person, person2=person)
    assert inverse.start_date == datetime.date(1990, 5, 12)
    assert inverse.marriage_place == "Lyon"
    assert inverse.end_date == datetime.date(2010, 1, 1)


@pytest.mark.django_db
def test_marriage_fields_edited_from_either_side_stay_in_sync(person, other_person):
    relation = Relation.objects.create(
        person1=person, person2=other_person, relationship_type=1, start_date=datetime.date(1990, 5, 12)
    )
    relation.marriage_place = "Annecy"
    relation.end_date = datetime.date(2020, 6, 1)
    relation.save()

    inverse = Relation.objects.get(person1=other_person, person2=person)
    assert inverse.marriage_place == "Annecy"
    assert inverse.end_date == datetime.date(2020, 6, 1)


@pytest.mark.django_db
def test_marriage_fields_not_mirrored_for_parent_child_relation(person, other_person):
    Relation.objects.create(
        person1=other_person,
        person2=person,
        relationship_type=2,
        marriage_place="Should not appear",
        end_date=datetime.date(2000, 1, 1),
    )
    inverse = Relation.objects.get(person1=person, person2=other_person)
    assert inverse.relationship_type == 3
    assert inverse.marriage_place == ""
    assert inverse.end_date is None
