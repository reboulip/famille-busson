"""Background-queue task wrappers (9.6) -- annuaire.tasks."""

import datetime

import pytest
from django.core import mail

from annuaire.tasks import send_daily_birthday_reminders


@pytest.mark.django_db
def test_sends_todays_reminders(person, other_person):
    today = datetime.date.today()
    other_person.birth_date = today.replace(year=1990)
    other_person.save()
    person.settings.notify_on_birthday = True
    person.settings.save()
    other_person.settings.notify_on_birthday = False
    other_person.settings.save()

    send_daily_birthday_reminders()

    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_a_second_call_on_the_same_day_is_a_noop(person, other_person):
    # The day-lock exists precisely so a catch_up run (django-q2 processing a missed
    # schedule on the next tick) or an overlap with the old crontab entry during a
    # deploy can never send the same day's reminders twice.
    today = datetime.date.today()
    other_person.birth_date = today.replace(year=1990)
    other_person.save()
    person.settings.notify_on_birthday = True
    person.settings.save()
    other_person.settings.notify_on_birthday = False
    other_person.settings.save()

    send_daily_birthday_reminders()
    send_daily_birthday_reminders()

    assert len(mail.outbox) == 1
