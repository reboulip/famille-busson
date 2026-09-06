"""Send a birthday reminder email to every subscribed member for each person whose
birthday is today.

Usage (from the repo root):
    uv run python manage.py send_birthday_reminders
    uv run python manage.py send_birthday_reminders --date 2026-06-10 --dry-run

Meant to be run once a day via cron/systemd timer, e.g.:
    0 8 * * * cd /app && uv run python manage.py send_birthday_reminders
"""

from __future__ import annotations

import datetime
import logging

from django.core.management.base import BaseCommand, CommandError, CommandParser

from annuaire import birthdays

HELP_TEXT = __doc__ or ""

logger = logging.getLogger("django")


class Command(BaseCommand):
    help = HELP_TEXT

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--date",
            type=datetime.date.fromisoformat,
            default=None,
            help="Run as if today were this date (ISO 8601, YYYY-MM-DD). Defaults to today.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report who would receive a reminder without sending any email.",
        )

    def handle(self, *args, **options):
        today = options["date"] or datetime.date.today()
        dry_run = options["dry_run"]
        logger.info("send_birthday_reminders starting for %s (dry_run=%s)", today, dry_run)

        if dry_run:
            messages = birthdays.birthday_reminder_messages(today)
            if not messages:
                self.stdout.write("Aucun anniversaire aujourd'hui.")
                logger.info("send_birthday_reminders: nothing to send for %s", today)
                return
            recipients = sorted({message.to for message in messages})
            self.stdout.write(f"{len(recipients)} destinataire(s) recevraient un rappel (dry-run).")
            for recipient in recipients:
                self.stdout.write(f"  - {recipient}")
            logger.info("send_birthday_reminders dry-run: %d recipient(s) for %s", len(recipients), today)
            return

        sent, failed = birthdays.send_birthday_reminders(today)
        if not sent and not failed:
            self.stdout.write("Aucun anniversaire aujourd'hui.")
            logger.info("send_birthday_reminders: nothing to send for %s", today)
            return

        self.stdout.write(f"{len(sent)} email(s) envoyé(s), {len(failed)} échec(s).")
        if failed:
            logger.error("send_birthday_reminders: %d failure(s) for %s: %s", len(failed), today, failed)
            raise CommandError(f"{len(failed)} birthday reminder(s) failed to send: {failed}")
        logger.info("send_birthday_reminders: %d email(s) sent for %s", len(sent), today)
