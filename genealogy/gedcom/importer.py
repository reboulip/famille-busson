"""Maps a parsed GEDCOM record tree to staged rows, and later applies a
reviewed import to the real directory. GEDCOM semantics (INDI/FAM/BIRT/DEAT/
MARR/DIV) live here; parser.py knows nothing about them.
"""

from __future__ import annotations

import datetime
from typing import cast

from ..models import GedcomImport, StagedFamily, StagedIndividual
from .parser import GedcomParseError, GedcomRecord, parse_gedcom

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_INDIVIDUALS = 2000

_MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


def parse_gedcom_date(value: str) -> datetime.date | None:
    """Best-effort parse of a plain "12 MAY 1990" GEDCOM date. Anything else
    (a range, "ABT 1990", "BEF 1990"...) is left unparsed -- staff can fill
    the field in by hand after import if it matters. Never raises."""
    parts = value.strip().upper().split()
    if len(parts) == 3 and parts[1] in _MONTHS and parts[0].isdigit() and parts[2].isdigit():
        try:
            return datetime.date(int(parts[2]), _MONTHS[parts[1]], int(parts[0]))
        except ValueError:
            return None
    return None


def _parse_name(value: str) -> tuple[str, str]:
    """ "Jean /Busson/" -> ("Jean", "Busson")."""
    if "/" in value:
        given, _, rest = value.partition("/")
        surname = rest.split("/")[0]
        return given.strip(), surname.strip()
    return value.strip(), ""


def stage_gedcom_import(gedcom_import: GedcomImport) -> None:
    """Parses `gedcom_import.raw_content` and creates its StagedIndividual/
    StagedFamily rows. Raises GedcomParseError on a structural problem or if
    the file exceeds MAX_INDIVIDUALS -- the caller is responsible for not
    leaving a half-staged import behind (wrap in a transaction)."""
    records = parse_gedcom(cast(str, gedcom_import.raw_content))

    individuals = [r for r in records if r.tag == "INDI"]
    if len(individuals) > MAX_INDIVIDUALS:
        raise GedcomParseError(f"Ce fichier contient plus de {MAX_INDIVIDUALS} individus ; import refusé.")

    for record in individuals:
        _stage_individual(gedcom_import, record)

    for record in records:
        if record.tag == "FAM":
            _stage_family(gedcom_import, record)


def _stage_individual(gedcom_import: GedcomImport, record: GedcomRecord) -> None:
    name_rec = record.child("NAME")
    first_name, last_name = _parse_name(name_rec.value) if name_rec else ("", "")
    birt = record.child("BIRT")
    deat = record.child("DEAT")
    birth_date_rec = birt.child("DATE") if birt else None
    birth_place_rec = birt.child("PLAC") if birt else None
    death_date_rec = deat.child("DATE") if deat else None
    death_place_rec = deat.child("PLAC") if deat else None
    StagedIndividual.objects.create(
        gedcom_import=gedcom_import,
        source_xref=record.xref or "",
        first_name=first_name,
        last_name=last_name,
        birth_date=parse_gedcom_date(birth_date_rec.value) if birth_date_rec else None,
        birth_place=birth_place_rec.value if birth_place_rec else "",
        death_date=parse_gedcom_date(death_date_rec.value) if death_date_rec else None,
        death_place=death_place_rec.value if death_place_rec else "",
    )


def _stage_family(gedcom_import: GedcomImport, record: GedcomRecord) -> None:
    husb = record.child("HUSB")
    wife = record.child("WIFE")
    marr = record.child("MARR")
    div = record.child("DIV")
    marr_date_rec = marr.child("DATE") if marr else None
    marr_place_rec = marr.child("PLAC") if marr else None
    div_date_rec = div.child("DATE") if div else None
    children = [c.value for c in record.children if c.tag == "CHIL"]
    StagedFamily.objects.create(
        gedcom_import=gedcom_import,
        source_xref=record.xref or "",
        husband_xref=husb.value if husb else "",
        wife_xref=wife.value if wife else "",
        children_xrefs=children,
        marriage_date=parse_gedcom_date(marr_date_rec.value) if marr_date_rec else None,
        marriage_place=marr_place_rec.value if marr_place_rec else "",
        divorce_date=parse_gedcom_date(div_date_rec.value) if div_date_rec else None,
    )


def apply_gedcom_import(gedcom_import: GedcomImport) -> dict[str, int]:
    """Creates real Person/Relation rows from the staged, reviewed data.
    Only ever called after explicit staff approval -- nothing before this
    point writes to annuaire.Person/Relation. Returns a small summary for
    the confirmation message."""
    from annuaire.models import Person, Relation
    from annuaire.person_merge import merge_persons

    summary = {"created": 0, "merged": 0, "skipped": 0}
    individuals = list(gedcom_import.staged_individuals.all())

    for staged in individuals:
        if staged.decision == "skip":
            summary["skipped"] += 1
            continue

        new_person = Person.objects.create(
            first_name=staged.first_name,
            last_name=staged.last_name,
            birth_date=staged.birth_date,
            birth_place=staged.birth_place,
            death_date=staged.death_date,
            death_place=staged.death_place,
            deceased=bool(staged.death_date),
        )
        if staged.decision == "merge" and staged.match_person_id:
            merge_persons(staged.match_person, new_person)
            staged.created_person_id = staged.match_person_id
            summary["merged"] += 1
        else:
            staged.created_person = new_person
            summary["created"] += 1
        staged.save(update_fields=["created_person"])

    by_xref = {s.source_xref: s.created_person_id for s in individuals if s.created_person_id}

    for family in gedcom_import.staged_families.all():
        husband_id = by_xref.get(family.husband_xref)
        wife_id = by_xref.get(family.wife_xref)
        parents = [pk for pk in (husband_id, wife_id) if pk]
        if husband_id and wife_id:
            Relation.objects.create(
                person1_id=husband_id,
                person2_id=wife_id,
                relationship_type=1,
                start_date=family.marriage_date,
                marriage_place=family.marriage_place,
                end_date=family.divorce_date,
            )
        for child_xref in family.children_xrefs:
            child_id = by_xref.get(child_xref)
            if not child_id:
                continue
            for parent_id in parents:
                Relation.objects.create(person1_id=child_id, person2_id=parent_id, relationship_type=2)

    gedcom_import.status = "applied"
    gedcom_import.save(update_fields=["status"])
    return summary
