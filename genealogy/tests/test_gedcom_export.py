import datetime

import pytest

from annuaire.models import Person, Relation
from genealogy.gedcom.export import build_gedcom, collect_export_set


@pytest.mark.django_db
def test_collect_export_set_with_no_ids_returns_everyone(person, other_person):
    persons, relations = collect_export_set(None)
    assert {p.pk for p in persons} == {person.pk, other_person.pk}


@pytest.mark.django_db
def test_collect_export_set_scopes_to_given_ids(person, other_person):
    persons, _relations = collect_export_set([person.pk])
    assert [p.pk for p in persons] == [person.pk]


@pytest.mark.django_db
def test_collect_export_set_drops_relations_with_endpoint_outside_set(person, other_person):
    third = Person.objects.create(first_name="Charlie", last_name="Busson")
    Relation.objects.create(person1=person, person2=other_person, relationship_type=1)
    Relation.objects.create(person1=person, person2=third, relationship_type=2)
    _persons, relations = collect_export_set([person.pk, other_person.pk])
    assert all(r.person1_id != third.pk and r.person2_id != third.pk for r in relations)


@pytest.mark.django_db
def test_build_gedcom_emits_one_indi_per_person(person, other_person):
    persons, relations = collect_export_set(None)
    payload = build_gedcom(persons, relations)
    text = payload.decode("utf-8")
    assert f"0 @I{person.pk}@ INDI" in text
    assert f"0 @I{other_person.pk}@ INDI" in text


@pytest.mark.django_db
def test_build_gedcom_never_emits_sex_tag(person, other_person):
    Relation.objects.create(person1=person, person2=other_person, relationship_type=0)
    persons, relations = collect_export_set(None)
    payload = build_gedcom(persons, relations)
    assert "SEX" not in payload.decode("utf-8")


@pytest.mark.django_db
def test_build_gedcom_emits_birth_and_death_data(person):
    person.birth_date = datetime.date(1950, 3, 4)
    person.birth_place = "Lyon"
    person.death_date = datetime.date(2020, 1, 1)
    person.death_place = "Paris"
    person.save()
    persons, relations = collect_export_set([person.pk])
    text = build_gedcom(persons, relations).decode("utf-8")
    assert "2 DATE 4 MAR 1950" in text
    assert "2 PLAC Lyon" in text
    assert "2 DATE 1 JAN 2020" in text
    assert "2 PLAC Paris" in text


@pytest.mark.django_db
def test_build_gedcom_creates_one_fam_per_spouse_pair(person, other_person):
    Relation.objects.create(
        person1=person,
        person2=other_person,
        relationship_type=0,
        start_date=datetime.date(1990, 5, 12),
        marriage_place="Lyon",
    )
    persons, relations = collect_export_set(None)
    text = build_gedcom(persons, relations).decode("utf-8")
    assert text.count(" FAM\r\n") == 1
    assert "1 MARR" in text
    assert "2 DATE 12 MAY 1990" in text
    assert "2 PLAC Lyon" in text


@pytest.mark.django_db
def test_build_gedcom_husband_is_lower_pk(person, other_person):
    Relation.objects.create(person1=person, person2=other_person, relationship_type=1)
    persons, relations = collect_export_set(None)
    text = build_gedcom(persons, relations).decode("utf-8")
    lower, higher = sorted([person.pk, other_person.pk])
    assert f"1 HUSB @I{lower}@" in text
    assert f"1 WIFE @I{higher}@" in text


@pytest.mark.django_db
def test_build_gedcom_groups_children_under_the_couples_fam(person, other_person):
    child = Person.objects.create(first_name="Charlie", last_name="Busson")
    Relation.objects.create(person1=person, person2=other_person, relationship_type=1)
    Relation.objects.create(person1=child, person2=person, relationship_type=2)
    Relation.objects.create(person1=child, person2=other_person, relationship_type=2)
    persons, relations = collect_export_set(None)
    text = build_gedcom(persons, relations).decode("utf-8")
    assert text.count(" FAM\r\n") == 1
    assert f"1 CHIL @I{child.pk}@" in text
    assert "1 FAMC @F1@" in text
    assert "1 FAMS @F1@" in text


@pytest.mark.django_db
def test_build_gedcom_single_parent_gets_own_fam(person):
    child = Person.objects.create(first_name="Charlie", last_name="Busson")
    Relation.objects.create(person1=child, person2=person, relationship_type=2)
    persons, relations = collect_export_set(None)
    text = build_gedcom(persons, relations).decode("utf-8")
    assert text.count(" FAM\r\n") == 1
    assert f"1 HUSB @I{person.pk}@" in text
    assert "1 WIFE" not in text


@pytest.mark.django_db
def test_build_gedcom_div_omitted_when_a_spouse_already_widowed(person, other_person):
    person.death_date = datetime.date(2000, 1, 1)
    person.save()
    Relation.objects.create(
        person1=person, person2=other_person, relationship_type=1, end_date=datetime.date(2005, 1, 1)
    )
    persons, relations = collect_export_set(None)
    text = build_gedcom(persons, relations).decode("utf-8")
    assert "1 DIV" not in text


@pytest.mark.django_db
def test_build_gedcom_div_emitted_when_no_spouse_widowed(person, other_person):
    Relation.objects.create(
        person1=person, person2=other_person, relationship_type=1, end_date=datetime.date(2005, 1, 1)
    )
    persons, relations = collect_export_set(None)
    text = build_gedcom(persons, relations).decode("utf-8")
    assert "1 DIV" in text
    assert "2 DATE 1 JAN 2005" in text


@pytest.mark.django_db
def test_build_gedcom_redact_hook_defaults_to_no_redaction(person):
    person.email = "person@example.com"
    person.save()
    persons, relations = collect_export_set([person.pk])
    text = build_gedcom(persons, relations).decode("utf-8")
    assert person.first_name in text
    assert "Vivant" not in text


@pytest.mark.django_db
def test_build_gedcom_redact_hook_replaces_given_name_and_drops_details(person):
    person.birth_date = datetime.date(1990, 1, 1)
    person.birth_place = "Lyon"
    person.save()
    persons, relations = collect_export_set([person.pk])
    text = build_gedcom(persons, relations, redact=lambda p: True).decode("utf-8")
    assert f"1 NAME Vivant /{person.last_name}/" in text
    assert "1990" not in text
    assert "Lyon" not in text


@pytest.mark.django_db
def test_build_gedcom_redact_drops_marriage_data_when_either_spouse_redacted(person, other_person):
    Relation.objects.create(
        person1=person,
        person2=other_person,
        relationship_type=1,
        start_date=datetime.date(1990, 5, 12),
        marriage_place="Lyon",
    )
    persons, relations = collect_export_set(None)
    text = build_gedcom(persons, relations, redact=lambda p: p.pk == person.pk).decode("utf-8")
    assert "1 MARR" not in text


@pytest.mark.django_db
def test_build_gedcom_is_byte_deterministic_across_runs(person, other_person):
    Relation.objects.create(person1=person, person2=other_person, relationship_type=0)
    persons, relations = collect_export_set(None)
    first = build_gedcom(persons, relations)
    second = build_gedcom(persons, relations)
    assert first == second
