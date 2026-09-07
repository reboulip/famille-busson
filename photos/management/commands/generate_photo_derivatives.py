"""Backfill Photo.thumbnail/web/taken_at for photos whose derivative
generation was never enqueued (e.g. worker down at upload time) or is still
pending.

Usage (from the repo root):
    uv run python manage.py generate_photo_derivatives

Runs every 15 minutes via the background task queue (see
docs/background_tasks.md) -- still hand-runnable for ad-hoc/manual use.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from photos.models import Photo
from photos.tasks import DEFAULT_LIMIT, process_pending_photos


class Command(BaseCommand):
    help = __doc__ or ""

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)

    def handle(self, *args, **options):
        if not Photo.objects.filter(derivative_status="pending").exists():
            self.stdout.write("Aucune photo à traiter.")
            return

        processed, error_count, error_messages = process_pending_photos(limit=options["limit"])
        for message in error_messages:
            self.stdout.write(message)
        self.stdout.write(f"{processed} photo(s) traitée(s), {error_count} erreur(s).")
