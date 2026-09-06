"""Send a birthday reminder email to every subscribed member for each person whose
birthday is today.

Usage (from the repo root):
    uv run python manage.py send_birthday_reminders

Meant to be run once a day via cron/systemd timer, e.g.:
    0 8 * * * cd /app && uv run python manage.py send_birthday_reminders
"""

from __future__ import annotations

import calendar
import datetime

from django.core.management.base import BaseCommand
from django.db.models import Q

from annuaire import emails
from annuaire.email_utils import send_bulk_emails
from annuaire.models import Person
from annuaire.models import Settings as NotificationSettings

HELP_TEXT = __doc__ or ""


class Command(BaseCommand):
    help = HELP_TEXT

    def handle(self, *args, **options):
        today = datetime.date.today()
        birthday_filter = Q(birth_date__month=today.month, birth_date__day=today.day)
        # Feb 29 people have no real birthday on a non-leap year -- observe it on
        # Feb 28 instead, same as most real-world "next birthday" logic.
        if today.month == 2 and today.day == 28 and not calendar.isleap(today.year):
            birthday_filter |= Q(birth_date__month=2, birth_date__day=29)
        birthday_people = list(Person.objects.filter(birthday_filter).exclude(deceased=True))
        if not birthday_people:
            self.stdout.write("Aucun anniversaire aujourd'hui.")
            return

        subscribers = (
            NotificationSettings.objects.filter(notify_on_birthday=True)
            .exclude(person__email__isnull=True)
            .exclude(person__email="")
            .exclude(person__deceased=True)
            .select_related("person")
        )
        if not subscribers:
            self.stdout.write("Aucun abonné aux rappels d'anniversaire.")
            return

        messages = []
        for birthday_person in birthday_people:
            # Read the photo once per birthday person, not once per subscriber: the
            # same bytes are attached to every copy of that person's message.
            photo = emails.birthday_photo(birthday_person)
            for subscriber in subscribers:
                messages.append(
                    emails.birthday_reminder(
                        birthday_person, subscriber.person.email, photo, recipient=subscriber.person
                    )
                )

        sent, failed = send_bulk_emails(messages)
        self.stdout.write(f"{len(sent)} email(s) envoyé(s), {len(failed)} échec(s).")
