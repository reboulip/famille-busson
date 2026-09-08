import datetime
from io import StringIO

import pytest
from django.core import mail
from django.core.management import CommandError, call_command


def run_command(*args):
    out = StringIO()
    call_command("send_birthday_reminders", *args, stdout=out)
    return out.getvalue()


@pytest.mark.django_db
def test_sends_reminder_to_subscribed_users_for_todays_birthday(person, other_person):
    today = datetime.date.today()
    other_person.birth_date = today.replace(year=1990)
    other_person.save()
    person.settings.notify_on_birthday = True
    person.settings.save()
    other_person.settings.notify_on_birthday = False
    other_person.settings.save()

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
    person.settings.notify_on_birthday = False
    person.settings.save()
    other_person.settings.notify_on_birthday = False
    other_person.settings.save()

    run_command()

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_feb_29_birthday_observed_on_feb_28_in_non_leap_years(person, other_person):
    other_person.birth_date = datetime.date(1992, 2, 29)  # 1992 was a leap year
    other_person.save()
    person.settings.notify_on_birthday = True
    person.settings.save()
    other_person.settings.notify_on_birthday = False
    other_person.settings.save()

    run_command("--date", "2026-02-28")  # 2026 is not a leap year

    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_date_flag_overrides_todays_clock(person, other_person):
    other_person.birth_date = datetime.date(1990, 6, 10)
    other_person.save()
    person.settings.notify_on_birthday = True
    person.settings.save()
    other_person.settings.notify_on_birthday = False
    other_person.settings.save()

    run_command("--date", "2026-06-10")

    assert len(mail.outbox) == 1
    assert other_person.first_name in mail.outbox[0].subject


@pytest.mark.django_db
def test_dry_run_reports_recipients_without_sending(person, other_person):
    other_person.birth_date = datetime.date(1990, 6, 10)
    other_person.save()
    person.settings.notify_on_birthday = True
    person.settings.save()
    other_person.settings.notify_on_birthday = False
    other_person.settings.save()

    output = run_command("--date", "2026-06-10", "--dry-run")

    assert len(mail.outbox) == 0
    assert "1 destinataire" in output
    assert person.email in output


@pytest.mark.django_db
def test_dry_run_reports_no_birthday_without_sending(person):
    person.settings.notify_on_birthday = True
    person.settings.save()

    output = run_command("--date", "2026-06-10", "--dry-run")

    assert len(mail.outbox) == 0
    assert "Aucun anniversaire" in output


@pytest.mark.django_db
def test_command_raises_and_exits_non_zero_when_a_send_fails(person, other_person, monkeypatch):
    import annuaire.birthdays as birthdays_module

    other_person.birth_date = datetime.date(1990, 6, 10)
    other_person.save()
    person.settings.notify_on_birthday = True
    person.settings.save()

    monkeypatch.setattr(birthdays_module, "send_bulk_emails", lambda messages: ([], [m.to for m in messages]))

    with pytest.raises(CommandError):
        run_command("--date", "2026-06-10")


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


@pytest.mark.django_db
def test_deceased_persons_birthday_is_not_announced(person, other_person):
    today = datetime.date.today()
    other_person.birth_date = today.replace(year=1990)
    other_person.deceased = True
    other_person.save()
    person.settings.notify_on_birthday = True
    person.settings.save()

    run_command()

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_deceased_subscriber_does_not_receive_reminders(person, other_person):
    today = datetime.date.today()
    other_person.birth_date = today.replace(year=1990)
    other_person.save()
    person.deceased = True
    person.save()
    person.settings.notify_on_birthday = True
    person.settings.save()
    # Isolate the deceased-subscriber exclusion: other_person must not itself be a
    # subscriber, or its own (legitimate) birthday reminder would also land in the
    # outbox and mask what this test is actually checking.
    other_person.settings.notify_on_birthday = False
    other_person.settings.save()

    run_command()

    assert len(mail.outbox) == 0
