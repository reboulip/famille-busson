"""One-time backfill: geocode every existing Chalet.address that doesn't already
have coordinates, via the shared annuaire.geocoding module (BAN, France-only,
with a worldwide Photon fallback) -- the same one address_picker.js's
server-side endpoint uses.

Usage (from the repo root):
    uv run python manage.py geocode_chalet_addresses

Meant to be run once after the #54 migration lands, so existing chalets show up on
the "Carte" view immediately rather than only after their next edit. Safe to re-run --
skips any Chalet that already has coordinates.
"""

from __future__ import annotations

import time

from django.core.management.base import BaseCommand
from django.db.models import Q

from annuaire.geocoding import geocode
from annuaire.models import Chalet

# Be a polite client of free public APIs -- no documented rate limit, but there's no
# reason to hammer them either.
DELAY_BETWEEN_REQUESTS_SECONDS = 0.2


class Command(BaseCommand):
    help = __doc__ or ""

    def handle(self, *args, **options):
        candidates = (
            Chalet.objects.exclude(address__isnull=True)
            .exclude(address="")
            .filter(Q(latitude__isnull=True) | Q(longitude__isnull=True))
        )

        if not candidates:
            self.stdout.write("Aucune adresse à géocoder.")
            return

        geocoded = 0
        unresolved = 0
        for chalet in candidates:
            coordinates = geocode(chalet.address)
            if coordinates is None:
                unresolved += 1
                self.stdout.write(f"Non résolu : {chalet} -- {chalet.address!r}")
                continue
            chalet.latitude, chalet.longitude = coordinates
            chalet.save(update_fields=["latitude", "longitude"])
            geocoded += 1
            time.sleep(DELAY_BETWEEN_REQUESTS_SECONDS)

        self.stdout.write(f"{geocoded} adresse(s) géocodée(s), {unresolved} non résolue(s).")
