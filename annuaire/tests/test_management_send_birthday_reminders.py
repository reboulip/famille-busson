import datetime
from io import StringIO

import pytest
from django.core import mail
from django.core.management import call_command


def run_command():
    out = StringIO()
    call_command("send_birthday_reminders", stdout=out)
    return out.getvalue()


@pytest.mark.django_db
def test_sends_reminder_to_subscribed_users_for_todays_birthday(person, other_person):
    today = datetime.date.today()
    other_person.birth_date = today.replace(year=1990)
    other_person.save()
    person.settings.notify_on_birthday = True
    person.settings.save()

    run_command()

    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.to == [person.email]
    assert other_person.first_name in sent.subject


@pytest.mark.django_db
def test_no_email_when_nobody_has_a_birthday_today(person):
    person.settings.notify_on_birthday = True
    person.settings.save()

    run_command()

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_no_email_when_nobody_is_subscribed(person, other_person):
    today = datetime.date.today()
    other_person.birth_date = today.replace(year=1990)
    other_person.save()

    run_command()

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_feb_29_birthday_observed_on_feb_28_in_non_leap_years(person, other_person, monkeypatch):
    import annuaire.management.commands.send_birthday_reminders as command_module

    class FixedDate(datetime.date):
        @classmethod
        def today(cls):
            return cls(2026, 2, 28)  # 2026 is not a leap year

    monkeypatch.setattr(command_module.datetime, "date", FixedDate)

    other_person.birth_date = datetime.date(1992, 2, 29)  # 1992 was a leap year
    other_person.save()
    person.settings.notify_on_birthday = True
    person.settings.save()

    run_command()

    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_every_subscriber_is_notified_including_the_birthday_person(person, other_person):
    today = datetime.date.today()
    other_person.birth_date = today.replace(year=1990)
    other_person.save()
    person.settings.notify_on_birthday = True
    person.settings.save()
    other_person.settings.notify_on_birthday = True
    other_person.settings.save()

    run_command()

    assert len(mail.outbox) == 2
    recipients = {sent.to[0] for sent in mail.outbox}
    assert recipients == {person.email, other_person.email}
