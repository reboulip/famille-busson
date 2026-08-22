"""One-time backfill: geocode every existing Person.postal_address that doesn't
already have coordinates, via the shared annuaire.geocoding module (BAN,
France-only, with a worldwide Photon fallback) -- the same one
address_picker.js's server-side endpoint uses.

Usage (from the repo root):
    uv run python manage.py geocode_person_addresses

Meant to be run once after the #44 migration lands, so existing profiles show up on
the "Carte" view immediately rather than only after their next edit. Safe to re-run --
skips any Person that already has coordinates.
"""

from __future__ import annotations

import time

from django.core.management.base import BaseCommand
from django.db.models import Q

from annuaire.geocoding import geocode
from annuaire.models import Person

# Be a polite client of free public APIs -- no documented rate limit, but there's no
# reason to hammer them either.
DELAY_BETWEEN_REQUESTS_SECONDS = 0.2


class Command(BaseCommand):
    help = __doc__ or ""

    def handle(self, *args, **options):
        candidates = (
            Person.objects.exclude(postal_address__isnull=True)
            .exclude(postal_address="")
            .filter(Q(latitude__isnull=True) | Q(longitude__isnull=True))
        )

        if not candidates:
            self.stdout.write("Aucune adresse à géocoder.")
            return

        geocoded = 0
        unresolved = 0
        for person in candidates:
            coordinates = geocode(person.postal_address)
            if coordinates is None:
                unresolved += 1
                self.stdout.write(f"Non résolu : {person} -- {person.postal_address!r}")
                continue
            person.latitude, person.longitude = coordinates
            person.save(update_fields=["latitude", "longitude"])
            geocoded += 1
            time.sleep(DELAY_BETWEEN_REQUESTS_SECONDS)

        self.stdout.write(f"{geocoded} adresse(s) géocodée(s), {unresolved} non résolue(s).")
