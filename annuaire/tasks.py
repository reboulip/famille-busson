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


def purge_expired_trash() -> None:
    """Permanently delete every soft-deleted (corbeille, 14.5) row past its
    retention window. One object per transaction -- deliberately NOT one
    atomic() block around the whole batch, so a mid-batch failure never rolls
    back an already-committed purge, and each object's post_delete file
    cleanup (deferred via transaction.on_commit) fires at the right moment."""
    from django.conf import settings
    from django.db import transaction

    from documents.models import Document
    from photos.models import Album, Photo
    from publications.models import BlogPost

    cutoff = timezone.now() - timezone.timedelta(days=settings.TRASH_RETENTION_DAYS)
    purged = 0
    for model in (BlogPost, Document, Album, Photo):
        for pk in list(model.all_objects.filter(deleted_at__lt=cutoff).values_list("pk", flat=True)):
            with transaction.atomic():
                try:
                    instance = model.all_objects.get(pk=pk)
                except model.DoesNotExist:
                    continue
                instance.purge()
            purged += 1
    logger.info("purge_expired_trash: permanently deleted %d row(s)", purged)
