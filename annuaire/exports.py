"""Serialize a set of Person records into an Excel workbook for bulk download.

Used by genealogie.html's "Exporter le carnet d'adresses en Excel" button (there is
also an "Exporter en image" button, handled entirely client-side in family_tree.js via
the vendored html-to-image library -- it never reaches this module): the exported
subset is exactly the person cards currently rendered in the centered-tree view
(collected client-side in family_tree.js, since which cards are on screen is
client-layout state family-chart never exposes server-side), not a server-computed
branch. The view just fetches the given ids and shapes them into a spreadsheet.
"""

from __future__ import annotations

import io
from collections.abc import Iterable

from openpyxl import Workbook

from .models import Person
from .privacy import always_redacted

EXPORT_COLUMNS: list[tuple[str, str]] = [
    ("Nom", "last_name"),
    ("Prénom", "first_name"),
    ("Adresse email", "email"),
    ("Numéro de téléphone", "phone_number"),
    ("Adresse postale", "postal_address"),
]


def build_export_rows(person_ids: Iterable[int]) -> list[list[str]]:
    """One row per Person in `person_ids`, ordered deterministically. Unknown ids
    are simply absent from the result (the caller may pass stale/invalid ids).
    A person who explicitly opted for `always_redacted` is skipped entirely --
    living-by-default redaction does NOT apply here, only the explicit opt-out
    (see annuaire/privacy.py)."""
    persons = Person.objects.filter(pk__in=person_ids).order_by("last_name", "first_name", "pk")
    return [
        [getattr(person, attr) or "" for _, attr in EXPORT_COLUMNS]
        for person in persons
        if not always_redacted(person)
    ]


def build_persons_workbook(rows: list[list[str]]) -> bytes:
    """A single-sheet .xlsx: header row from EXPORT_COLUMNS, then one row per entry."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Annuaire"
    sheet.append([header for header, _ in EXPORT_COLUMNS])
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
