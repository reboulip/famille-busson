import datetime

import pytest

from annuaire.models import Person, Relation
from genealogy.gedcom.importer import (
    MAX_INDIVIDUALS,
    apply_gedcom_import,
    parse_gedcom_date,
    stage_gedcom_import,
)
from genealogy.gedcom.parser import GedcomParseError
from genealogy.models import GedcomImport, StagedFamily, StagedIndividual


def _import_with(content: str) -> GedcomImport:
    gedcom_import = GedcomImport.objects.create(original_filename="test.ged", raw_content=content)
    stage_gedcom_import(gedcom_import)
    return gedcom_import


def test_parse_gedcom_date_valid():
    assert parse_gedcom_date("12 MAY 1990") == datetime.date(1990, 5, 12)


def test_parse_gedcom_date_returns_none_for_a_range():
    assert parse_gedcom_date("ABT 1990") is None


def test_parse_gedcom_date_returns_none_for_invalid_day():
    assert parse_gedcom_date("31 FEB 1990") is None


SIMPLE_GEDCOM = """0 HEAD
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Jean /Busson/
1 BIRT
2 DATE 12 MAY 1950
2 PLAC Lyon
1 FAMS @F1@
0 @I2@ INDI
1 NAME Marie /Dupont/
1 BIRT
2 DATE 3 MAR 1952
1 FAMS @F1@
0 @I3@ INDI
1 NAME Paul /Busson/
1 BIRT
2 DATE 1 JAN 1980
1 FAMC @F1@
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 MARR
2 DATE 10 JUN 1975
2 PLAC Paris
1 CHIL @I3@
0 TRLR
"""


@pytest.mark.django_db
def test_stage_gedcom_import_creates_staged_individuals():
    gedcom_import = _import_with(SIMPLE_GEDCOM)
    assert gedcom_import.staged_individuals.count() == 3
    jean = gedcom_import.staged_individuals.get(source_xref="@I1@")
    assert jean.first_name == "Jean"
    assert jean.last_name == "Busson"
    assert jean.birth_date == datetime.date(1950, 5, 12)
    assert jean.birth_place == "Lyon"


@pytest.mark.django_db
def test_stage_gedcom_import_creates_staged_families():
    gedcom_import = _import_with(SIMPLE_GEDCOM)
    assert gedcom_import.staged_families.count() == 1
    family = gedcom_import.staged_families.first()
    assert family.husband_xref == "@I1@"
    assert family.wife_xref == "@I2@"
    assert family.children_xrefs == ["@I3@"]
    assert family.marriage_date == datetime.date(1975, 6, 10)
    assert family.marriage_place == "Paris"


@pytest.mark.django_db
def test_stage_gedcom_import_rejects_files_over_the_individual_cap():
    lines = ["0 HEAD", "1 CHAR UTF-8"]
    for i in range(MAX_INDIVIDUALS + 1):
        lines.append(f"0 @I{i}@ INDI")
        lines.append(f"1 NAME Person{i} /Test/")
    content = "\n".join(lines) + "\n"
    gedcom_import = GedcomImport.objects.create(original_filename="huge.ged", raw_content=content)
    with pytest.raises(GedcomParseError):
        stage_gedcom_import(gedcom_import)


@pytest.mark.django_db
def test_apply_gedcom_import_creates_persons_and_relations():
    gedcom_import = _import_with(SIMPLE_GEDCOM)
    summary = apply_gedcom_import(gedcom_import)
    assert summary == {"created": 3, "merged": 0, "skipped": 0}

    jean = Person.objects.get(first_name="Jean", last_name="Busson")
    marie = Person.objects.get(first_name="Marie", last_name="Dupont")
    paul = Person.objects.get(first_name="Paul", last_name="Busson")

    assert Relation.objects.filter(person1=jean, person2=marie, relationship_type=1).exists()
    assert Relation.objects.filter(person1=paul, person2=jean, relationship_type=2).exists()
    assert Relation.objects.filter(person1=paul, person2=marie, relationship_type=2).exists()

    gedcom_import.refresh_from_db()
    assert gedcom_import.status == "applied"


@pytest.mark.django_db
def test_apply_gedcom_import_respects_skip_decision():
    gedcom_import = _import_with(SIMPLE_GEDCOM)
    staged = gedcom_import.staged_individuals.get(source_xref="@I3@")
    staged.decision = "skip"
    staged.save(update_fields=["decision"])

    summary = apply_gedcom_import(gedcom_import)
    assert summary["skipped"] == 1
    assert not Person.objects.filter(first_name="Paul", last_name="Busson").exists()


@pytest.mark.django_db
def test_apply_gedcom_import_merge_decision_uses_person_merge(person):
    gedcom_import = _import_with(SIMPLE_GEDCOM)
    staged = gedcom_import.staged_individuals.get(source_xref="@I1@")
    staged.decision = "merge"
    staged.match_person = person
    staged.save(update_fields=["decision", "match_person"])

    summary = apply_gedcom_import(gedcom_import)
    assert summary["merged"] == 1

    person.refresh_from_db()
    assert person.birth_date == datetime.date(1950, 5, 12)
    assert person.birth_place == "Lyon"


@pytest.mark.django_db
def test_apply_gedcom_import_drops_relation_for_a_skipped_parent():
    gedcom_import = _import_with(SIMPLE_GEDCOM)
    husband = gedcom_import.staged_individuals.get(source_xref="@I1@")
    husband.decision = "skip"
    husband.save(update_fields=["decision"])

    apply_gedcom_import(gedcom_import)

    marie = Person.objects.get(first_name="Marie")
    paul = Person.objects.get(first_name="Paul")
    assert Relation.objects.filter(person1=paul, person2=marie, relationship_type=2).exists()
    assert not Person.objects.filter(first_name="Jean", last_name="Busson").exists()


@pytest.mark.django_db
def test_stage_gedcom_import_single_parent_family_has_no_spouse():
    content = (
        "0 HEAD\n1 CHAR UTF-8\n"
        "0 @I1@ INDI\n1 NAME Jean /Busson/\n"
        "0 @I2@ INDI\n1 NAME Paul /Busson/\n"
        "0 @F1@ FAM\n1 HUSB @I1@\n1 CHIL @I2@\n0 TRLR\n"
    )
    gedcom_import = _import_with(content)
    family = gedcom_import.staged_families.first()
    assert family.husband_xref == "@I1@"
    assert family.wife_xref == ""


@pytest.mark.django_db
def test_stage_gedcom_import_handles_no_families(other_person):
    content = "0 HEAD\n1 CHAR UTF-8\n0 @I1@ INDI\n1 NAME Jean /Busson/\n0 TRLR\n"
    gedcom_import = _import_with(content)
    assert gedcom_import.staged_individuals.count() == 1
    assert gedcom_import.staged_families.count() == 0


def test_staged_individual_str():
    individual = StagedIndividual(first_name="Jean", last_name="Busson", source_xref="@I1@")
    assert str(individual) == "Jean Busson (@I1@)"


def test_staged_family_str():
    family = StagedFamily(source_xref="@F1@")
    assert str(family) == "Famille @F1@"


@pytest.mark.django_db
def test_gedcom_import_str_falls_back_to_pk():
    gedcom_import = GedcomImport.objects.create(raw_content="0 HEAD\n0 TRLR\n")
    assert str(gedcom_import) == f"Import #{gedcom_import.pk}"
