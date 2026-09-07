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
