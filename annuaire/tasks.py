"""Background-queue task wrappers (9.6).

django-q2 calls these directly by import path (e.g.
`annuaire.tasks.send_daily_birthday_reminders`) -- each is a plain, argument-free
function so a `Schedule` row can name it without a payload.
"""

from __future__ import annotations

import logging

from django.core.cache import cache
from django.utils import timezone

from annuaire.birthdays import send_birthday_reminders

logger = logging.getLogger("django")

# A day-long lock, keyed by date, so a catch_up run (the cluster processes a missed
# schedule on the next tick rather than skipping it) can never re-send the same day's
# reminders twice -- also covers the overlap window during a deploy where the old
# crontab entry and the new schedule might briefly both be active.
_DAY_LOCK_SECONDS = 60 * 60 * 26  # a little over a day, so a slow clock never expires early


def send_daily_birthday_reminders() -> None:
    today = timezone.localdate()
    lock_key = f"birthday-reminders:{today.isoformat()}"
    if not cache.add(lock_key, True, _DAY_LOCK_SECONDS):
        logger.info("send_daily_birthday_reminders: already sent for %s, skipping", today)
        return

    sent, failed = send_birthday_reminders(today)
    if failed:
        logger.error("send_daily_birthday_reminders: %d failure(s) for %s: %s", len(failed), today, failed)
    else:
        logger.info("send_daily_birthday_reminders: %d email(s) sent for %s", len(sent), today)


def reindex_search_object(app_label: str, model_name: str, pk: int) -> None:
    """Re-derive one row's search index from its current state. Called with a
    plain (app_label, model_name, pk) payload rather than the instance itself,
    so the worker (a separate process/connection) always re-queries fresh."""
    from django.apps import apps

    from annuaire.search.indexing import apply_index, build_index_payload
    from annuaire.search.registry import get_spec

    model = apps.get_model(app_label, model_name)
    try:
        instance = model.objects.get(pk=pk)
    except model.DoesNotExist:
        logger.info("reindex_search_object: %s.%s pk=%s no longer exists, skipping", app_label, model_name, pk)
        return
    spec = get_spec(model)
    apply_index(model, pk, build_index_payload(instance, spec))


def reindex_all_search_indexes() -> None:
    """Nightly safety net for a reindex that never got enqueued (e.g. a worker
    down at save time) -- mirrors the existing lost-enqueue safety nets for
    photo derivatives and document extraction."""
    from annuaire.search.indexing import backfill_search_indexes

    count = backfill_search_indexes()
    logger.info("reindex_all_search_indexes: reindexed %d row(s)", count)
