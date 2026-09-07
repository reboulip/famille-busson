"""Idempotently register this project's django-q2 Schedule rows.

Safe to run on every deploy: existing schedules are updated in place (matched by
`name`), never duplicated. `next_run` is only set when a schedule is first created --
a re-run must never push an already-ticking schedule's next occurrence back out, or a
routine deploy would perpetually delay it.

Usage (from the repo root):
    uv run python manage.py sync_scheduled_tasks

Run once per deploy, from the `web` service only -- never from the `worker` service,
which would race with `web` to create the same rows (see docker-entrypoint.sh's
RUN_STARTUP_TASKS guard).
"""

from __future__ import annotations

import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_q.models import Schedule

HELP_TEXT = __doc__ or ""

# 07:00 UTC -- 08:00-09:00 Paris depending on DST, closest match to the crontab entry
# this schedule replaces (0 8 * * *, which ran in the web container's UTC clock).
BIRTHDAY_REMINDER_HOUR_UTC = 7


def _next_occurrence_at(hour: int) -> datetime.datetime:
    now = timezone.now()
    candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if candidate <= now:
        candidate += datetime.timedelta(days=1)
    return candidate


class Command(BaseCommand):
    help = HELP_TEXT

    def handle(self, *args, **options):
        schedules = [
            {
                "name": "send_daily_birthday_reminders",
                "func": "annuaire.tasks.send_daily_birthday_reminders",
                "schedule_type": Schedule.DAILY,
                "initial_next_run": _next_occurrence_at(BIRTHDAY_REMINDER_HOUR_UTC),
            },
            {
                "name": "extract_pending_documents",
                "func": "documents.tasks.process_pending_document_files",
                "schedule_type": Schedule.MINUTES,
                "minutes": 15,
                "initial_next_run": timezone.now(),
            },
        ]

        for entry in schedules:
            initial_next_run = entry.pop("initial_next_run")
            defaults = {"func": entry["func"], "schedule_type": entry["schedule_type"]}
            if "minutes" in entry:
                defaults["minutes"] = entry["minutes"]

            schedule, created = Schedule.objects.update_or_create(name=entry["name"], defaults=defaults)
            if created:
                schedule.next_run = initial_next_run
                schedule.save(update_fields=["next_run"])
            self.stdout.write(f"{'created' if created else 'updated'} schedule: {entry['name']}")
