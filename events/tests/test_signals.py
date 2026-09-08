import datetime

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from events.models import Event, Rsvp
from events.tasks import EVENT_REMINDER_LEAD_DAYS, send_event_reminders


def _aware(*args):
    return timezone.make_aware(datetime.datetime(*args), datetime.UTC)


@pytest.mark.django_db
def test_group_restricted_event_created_via_view_only_notifies_group_member(
    auth_client, person, other_person, group, django_capture_on_commit_callbacks
):
    """Regression: post_save fires before form.save_m2m() adds the groups, so
    computing the audience too early would see zero groups and mail a
    restricted event to the whole family. `person` is in `group`, `other_person`
    is not; both are opted in to notify_on_event."""
    person.account.groups.add(group)
    person.settings.notify_on_event = True
    person.settings.save()
    other_person.settings.notify_on_event = True
    other_person.settings.save()

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.post(
            reverse("event-create"),
            {
                "title": "Réunion privée",
                "description": "",
                "start": "2026-07-14T12:00",
                "end": "2026-07-14T18:00",
                "location": "",
                "groups": [str(group.pk)],
            },
        )
        assert response.status_code == 302

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [person.email]


@pytest.mark.django_db
def test_announcement_enqueued_on_creation(person, django_capture_on_commit_callbacks):
    person.settings.notify_on_event = True
    person.settings.save()

    with django_capture_on_commit_callbacks(execute=True):
        Event.objects.create(title="Barbecue", start=_aware(2026, 7, 1, 12, 0))

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [person.email]


@pytest.mark.django_db
def test_announcement_respects_notify_on_event_preference(person, django_capture_on_commit_callbacks):
    person.settings.notify_on_event = False
    person.settings.save()

    with django_capture_on_commit_callbacks(execute=True):
        Event.objects.create(title="Barbecue", start=_aware(2026, 7, 1, 12, 0))

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_announcement_excludes_deceased(person, django_capture_on_commit_callbacks):
    person.deceased = True
    person.save()
    person.settings.notify_on_event = True
    person.settings.save()

    with django_capture_on_commit_callbacks(execute=True):
        Event.objects.create(title="Barbecue", start=_aware(2026, 7, 1, 12, 0))

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_announcement_excludes_empty_email(person, django_capture_on_commit_callbacks):
    person.email = ""
    person.save()
    person.settings.notify_on_event = True
    person.settings.save()

    with django_capture_on_commit_callbacks(execute=True):
        Event.objects.create(title="Barbecue", start=_aware(2026, 7, 1, 12, 0))

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_event_update_does_not_resend_announcement(person, django_capture_on_commit_callbacks):
    person.settings.notify_on_event = True
    person.settings.save()

    with django_capture_on_commit_callbacks(execute=True):
        event = Event.objects.create(title="Barbecue", start=_aware(2026, 7, 1, 12, 0))
    assert len(mail.outbox) == 1

    with django_capture_on_commit_callbacks(execute=True):
        event.title = "Barbecue (modifié)"
        event.save()
    assert len(mail.outbox) == 1


# ---------------------------------------------------------------------------
# send_event_reminders
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_reminder_selects_events_in_lead_window(person):
    person.settings.notify_on_event = True
    person.settings.save()
    now = timezone.now()
    event = Event.objects.create(title="Bientôt", start=now + datetime.timedelta(days=1))

    send_event_reminders()

    event.refresh_from_db()
    assert event.reminder_sent_at is not None
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_reminder_excludes_events_outside_lead_window(person):
    person.settings.notify_on_event = True
    person.settings.save()
    now = timezone.now()
    event = Event.objects.create(title="Trop loin", start=now + datetime.timedelta(days=EVENT_REMINDER_LEAD_DAYS + 5))

    send_event_reminders()

    event.refresh_from_db()
    assert event.reminder_sent_at is None
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_reminder_excludes_past_events(person):
    person.settings.notify_on_event = True
    person.settings.save()
    Event.objects.create(title="Passé", start=timezone.now() - datetime.timedelta(days=1))

    send_event_reminders()

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_reminder_excludes_already_reminded_events(person):
    person.settings.notify_on_event = True
    person.settings.save()
    now = timezone.now()
    event = Event.objects.create(title="Déjà rappelé", start=now + datetime.timedelta(hours=12))
    event.reminder_sent_at = now
    event.save(update_fields=["reminder_sent_at"])

    send_event_reminders()

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_reminder_excludes_rsvp_no(person):
    person.settings.notify_on_event = True
    person.settings.save()
    event = Event.objects.create(title="Bientôt", start=timezone.now() + datetime.timedelta(hours=12))
    Rsvp.objects.create(event=event, person=person, response="no")

    send_event_reminders()

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_reminder_includes_rsvp_yes(person):
    person.settings.notify_on_event = True
    person.settings.save()
    event = Event.objects.create(title="Bientôt", start=timezone.now() + datetime.timedelta(hours=12))
    Rsvp.objects.create(event=event, person=person, response="yes")

    send_event_reminders()

    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_reminder_stamps_reminder_sent_at_before_running_twice(person):
    person.settings.notify_on_event = True
    person.settings.save()
    Event.objects.create(title="Bientôt", start=timezone.now() + datetime.timedelta(hours=12))

    send_event_reminders()
    assert len(mail.outbox) == 1

    send_event_reminders()
    assert len(mail.outbox) == 1  # unchanged -- not sent a second time
