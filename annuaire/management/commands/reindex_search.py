"""Rebuild every model's search index from scratch.

Thin wrapper around the same callable each app's own migration backfill calls
(see annuaire.search.indexing.backfill_search_indexes) and the one the nightly
`reindex_all_search_indexes` task runs -- all three share this single
implementation so they can't drift apart.

Usage (from the repo root):
    uv run python manage.py reindex_search
"""

from django.core.management.base import BaseCommand

from annuaire.search.indexing import backfill_search_indexes

HELP_TEXT = __doc__ or ""


class Command(BaseCommand):
    help = HELP_TEXT

    def handle(self, *args, **options):
        count = backfill_search_indexes()
        self.stdout.write(f"Reindexed {count} row(s).")
