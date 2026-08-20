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

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.urls import reverse

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
        birthday_people = list(Person.objects.filter(birthday_filter))
        if not birthday_people:
            self.stdout.write("Aucun anniversaire aujourd'hui.")
            return

        subscribers = (
            NotificationSettings.objects.filter(notify_on_birthday=True)
            .exclude(person__email__isnull=True)
            .exclude(person__email="")
            .select_related("person")
        )
        if not subscribers:
            self.stdout.write("Aucun abonné aux rappels d'anniversaire.")
            return

        messages = []
        for birthday_person in birthday_people:
            profile_url = settings.SITE_BASE_URL.rstrip("/") + reverse(
                "personne-detail", kwargs={"pk": birthday_person.pk}
            )
            subject = f"Anniversaire de {birthday_person.first_name} {birthday_person.last_name}"
            body = (
                f"C'est aujourd'hui l'anniversaire de {birthday_person.first_name} "
                f"{birthday_person.last_name} !\n\n{profile_url}"
            )
            for subscriber in subscribers:
                messages.append((subscriber.person.email, subject, body))

        sent, failed = send_bulk_emails(messages)
        self.stdout.write(f"{len(sent)} email(s) envoyé(s), {len(failed)} échec(s).")
