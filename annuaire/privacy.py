"""Living-person privacy policy -- who gets redacted from an export, and why.

A small pure-policy module beside the models, mirroring documents/access.py and
events/access.py's shape. Every export surface calls this module rather than
re-deriving "is this person alive" itself.
"""

from __future__ import annotations

import datetime
from typing import cast

from .models import Person

LIVING_MAX_AGE_YEARS = 100


def is_living(person: Person) -> bool:
    """Fail-closed: no birth date and no deceased flag means treated as living.
    `deceased` is staff-only-settable (see ProfileEditForm), so a long-dead
    ancestor entered by an ordinary member is very often unflagged -- the
    100-year rule does the real work here. Year-only arithmetic (no month/day)
    keeps this deterministic across SQLite and Postgres."""
    if person.deceased or person.death_date is not None:
        return False
    if person.birth_date is not None:
        age_years = datetime.date.today().year - person.birth_date.year
        if age_years >= LIVING_MAX_AGE_YEARS:
            return False
    return True


def always_redacted(person: Person) -> bool:
    """The explicit opt-out only -- True iff `redact`, regardless of living
    status. Unlike is_redacted(), this ignores `auto`: it's what the Excel
    export and iCal feed honour (they already show this data to any
    logged-in member, so a living-by-default redaction would gut two shipped
    features for little gain -- only an explicit "always hide me" is
    respected there)."""
    return person.export_privacy == Person.ExportPrivacy.REDACT


def is_redacted(person: Person) -> bool:
    """`share` never redacts, even living. `redact` always redacts, even once
    deceased (a family may want a recently-deceased relative kept off a public
    genealogy site). `auto` (the default) redacts exactly the living."""
    if person.export_privacy == Person.ExportPrivacy.SHARE:
        return False
    if person.export_privacy == Person.ExportPrivacy.REDACT:
        return True
    return is_living(person)


def redacted_person_ids(persons) -> set[int]:
    """Bulk entry point -- avoids an is_redacted() call (and its is_living()
    date arithmetic) per row inside an export loop over the whole tree."""
    return {person.pk for person in persons if is_redacted(person)}


def redacted_display_name(person: Person) -> tuple[str, str]:
    """(given, surname) for a redacted individual. Surname is kept -- on a
    single-family tree it carries near-zero marginal information, and dropping
    it makes the exported tree unreadable/unmergeable in the target tool."""
    return "Vivant", cast(str, person.last_name)
