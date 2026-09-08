"""Collects a GEDCOM export set from Person/Relation and builds the file.

Family (FAM) synthesis is the real work here: Relation is pairwise, but GEDCOM
needs family units. One FAM per spouse pair; children grouped by their exact
parent-pk-set and attached to the matching couple, or given their own FAM when
the parent-set isn't a recognized couple (single parent, or a parent outside
the export set).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any, cast

from annuaire.models import Person, Relation

from .writer import format_date, pointer_line, render_gedcom, tag_lines

_SPOUSE_TYPES = (0, 1)
_PARENT = 2


def collect_export_set(person_ids: list[int] | None) -> tuple[list[Person], list[Relation]]:
    """`person_ids` empty/None exports the whole directory; otherwise exactly
    the given set. A Relation with either endpoint outside the set is dropped
    -- no FAM record may point at a missing INDI."""
    if person_ids:
        persons = list(Person.objects.filter(pk__in=person_ids))
    else:
        persons = list(Person.objects.all())
    ids = {p.pk for p in persons}
    relations = list(Relation.objects.filter(person1__in=ids, person2__in=ids))
    return persons, relations


def _build_families(persons: list[Person], relations: list[Relation]) -> list[dict[str, Any]]:
    person_ids = {p.pk for p in persons}

    families_by_spouses: dict[frozenset[int], dict[str, Any]] = {}
    for rel in relations:
        if rel.relationship_type in _SPOUSE_TYPES:
            pair = frozenset({rel.person1_id, rel.person2_id})
            if pair not in families_by_spouses:
                families_by_spouses[pair] = {
                    "spouses": tuple(sorted(pair)),
                    "start_date": rel.start_date,
                    "marriage_place": rel.marriage_place,
                    "end_date": rel.end_date,
                    "children": [],
                }

    parents_of: dict[int, set[int]] = {}
    for rel in relations:
        if rel.relationship_type == _PARENT:
            parents_of.setdefault(rel.person1_id, set()).add(rel.person2_id)

    children_by_parents: dict[frozenset[int], list[int]] = {}
    for child_id, parents in parents_of.items():
        known_parents = frozenset(p for p in parents if p in person_ids)
        if not known_parents:
            continue
        children_by_parents.setdefault(known_parents, []).append(child_id)

    for parents, children in children_by_parents.items():
        if parents in families_by_spouses:
            families_by_spouses[parents]["children"] = sorted(children)

    families = list(families_by_spouses.values())
    matched = set(families_by_spouses.keys())
    for parents, children in children_by_parents.items():
        if parents not in matched:
            families.append(
                {
                    "spouses": tuple(sorted(parents)),
                    "start_date": None,
                    "marriage_place": "",
                    "end_date": None,
                    "children": sorted(children),
                }
            )

    families.sort(key=lambda f: (f["spouses"][0], f["spouses"][-1]))
    return families


def _individual_lines(
    person: Person, families_as_spouse: list[int], families_as_child: list[int], redact: Callable[[Person], bool]
) -> list[str]:
    xref = f"@I{person.pk}@"
    is_redacted = redact(person)
    given_name = "Vivant" if is_redacted else person.first_name
    lines = [f"0 {xref} INDI"]
    lines.extend(tag_lines(1, "NAME", f"{given_name} /{person.last_name}/"))
    if not is_redacted:
        if person.birth_date or person.birth_place:
            lines.append("1 BIRT")
            if person.birth_date:
                lines.extend(tag_lines(2, "DATE", format_date(cast(date, person.birth_date))))
            if person.birth_place:
                lines.extend(tag_lines(2, "PLAC", cast(str, person.birth_place)))
        if person.death_date or person.death_place or person.deceased:
            lines.append("1 DEAT")
            if person.death_date:
                lines.extend(tag_lines(2, "DATE", format_date(cast(date, person.death_date))))
            if person.death_place:
                lines.extend(tag_lines(2, "PLAC", cast(str, person.death_place)))
    for fam_idx in families_as_spouse:
        lines.append(pointer_line(1, "FAMS", f"@F{fam_idx}@"))
    for fam_idx in families_as_child:
        lines.append(pointer_line(1, "FAMC", f"@F{fam_idx}@"))
    return lines


def _family_lines(
    fam_idx: int, family: dict[str, Any], by_pk: dict[int, Person], redact: Callable[[Person], bool]
) -> list[str]:
    xref = f"@F{fam_idx}@"
    lines = [f"0 {xref} FAM"]
    spouses = family["spouses"]
    any_redacted = any(redact(by_pk[pk]) for pk in spouses if pk in by_pk)

    if len(spouses) == 2:
        # HUSB/WIFE is a pure GEDCOM-file formatting detail -- lower pk always
        # gets HUSB. Never surfaced in the app, never stored; Person carries no
        # sex/gender field (deliberately removed, see migration 0007).
        husb_id, wife_id = spouses
        lines.append(pointer_line(1, "HUSB", f"@I{husb_id}@"))
        lines.append(pointer_line(1, "WIFE", f"@I{wife_id}@"))
    elif len(spouses) == 1:
        lines.append(pointer_line(1, "HUSB", f"@I{spouses[0]}@"))

    if not any_redacted:
        if family["start_date"] or family["marriage_place"]:
            lines.append("1 MARR")
            if family["start_date"]:
                lines.extend(tag_lines(2, "DATE", format_date(family["start_date"])))
            if family["marriage_place"]:
                lines.extend(tag_lines(2, "PLAC", family["marriage_place"]))
        if family["end_date"]:
            spouse_people = [by_pk[pk] for pk in spouses if pk in by_pk]
            already_widowed = any(p.death_date and p.death_date <= family["end_date"] for p in spouse_people)
            if not already_widowed:
                lines.append("1 DIV")
                lines.extend(tag_lines(2, "DATE", format_date(family["end_date"])))

    for child_id in family["children"]:
        lines.append(pointer_line(1, "CHIL", f"@I{child_id}@"))
    return lines


def build_gedcom(
    persons: list[Person], relations: list[Relation], *, redact: Callable[[Person], bool] = lambda p: False
) -> bytes:
    persons = sorted(persons, key=lambda p: p.pk)
    by_pk = {p.pk: p for p in persons}
    families = _build_families(persons, relations)

    families_as_spouse: dict[int, list[int]] = {}
    families_as_child: dict[int, list[int]] = {}
    for idx, family in enumerate(families, start=1):
        for spouse_id in family["spouses"]:
            families_as_spouse.setdefault(spouse_id, []).append(idx)
        for child_id in family["children"]:
            families_as_child.setdefault(child_id, []).append(idx)

    record_lines: list[str] = []
    for person in persons:
        record_lines.extend(
            _individual_lines(
                person, families_as_spouse.get(person.pk, []), families_as_child.get(person.pk, []), redact
            )
        )
    for idx, family in enumerate(families, start=1):
        record_lines.extend(_family_lines(idx, family, by_pk, redact))

    return render_gedcom(record_lines)
