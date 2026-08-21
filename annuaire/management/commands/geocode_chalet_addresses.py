"""One-time backfill: geocode every existing Chalet.address that doesn't already
have coordinates, via the same BAN API address_picker.js uses client-side.

Usage (from the repo root):
    uv run python manage.py geocode_chalet_addresses

Meant to be run once after the #54 migration lands, so existing chalets show up on
the "Carte" view immediately rather than only after their next edit. Safe to re-run --
skips any Chalet that already has coordinates.
"""

from __future__ import annotations

import time
from decimal import Decimal

import requests
from django.core.management.base import BaseCommand
from django.db.models import Q

from annuaire.models import Chalet

BAN_SEARCH_URL = "https://api-adresse.data.gouv.fr/search/"
REQUEST_TIMEOUT_SECONDS = 5
# Be a polite client of a free public API -- no documented rate limit, but there's no
# reason to hammer it either.
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
            coordinates = self._geocode(chalet.address)
            if coordinates is None:
                unresolved += 1
                self.stdout.write(f"Non résolu : {chalet} -- {chalet.address!r}")
                continue
            chalet.longitude = Decimal(str(coordinates[0]))
            chalet.latitude = Decimal(str(coordinates[1]))
            chalet.save(update_fields=["latitude", "longitude"])
            geocoded += 1
            time.sleep(DELAY_BETWEEN_REQUESTS_SECONDS)

        self.stdout.write(f"{geocoded} adresse(s) géocodée(s), {unresolved} non résolue(s).")

    def _geocode(self, address):
        try:
            response = requests.get(BAN_SEARCH_URL, params={"q": address, "limit": 1}, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            features = response.json().get("features", [])
        except (requests.RequestException, ValueError):
            return None
        if not features:
            return None
        return features[0]["geometry"]["coordinates"]
