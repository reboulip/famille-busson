"""Background-queue task wrappers, mirroring publications/tasks.py's shape:
django-q2 calls these directly by import path, with plain values (never a model
instance) so the task re-queries fresh state after the enqueueing transaction
has committed.
"""

from __future__ import annotations

import datetime
import logging

from django.utils import timezone
from django_q.tasks import async_task

from annuaire import emails
from annuaire.email_utils import send_one_email
from annuaire.models import Settings as NotificationSettings

from .models import Event, Rsvp

logger = logging.getLogger("django")

# How many days before an event's start its reminder goes out. One reminder,
# stamped via Event.reminder_sent_at -- promote to a per-event field if a
# second stage is ever needed.
EVENT_REMINDER_LEAD_DAYS = 2


def notification_audience(event):
    """Base audience for both the creation announcement and the reminder:
    opted-in, has an email, not deceased, and -- if the event is
    group-restricted -- a member of one of its groups. Staff/superusers are
    NOT auto-added: access to view an event is not the same as being
    subscribed to mail about it."""
    subscribers = (
        NotificationSettings.objects.filter(notify_on_event=True)
        .exclude(person__email__isnull=True)
        .exclude(person__email="")
        .exclude(person__deceased=True)
        .select_related("person")
    )
    if event.groups.exists():
        subscribers = subscribers.filter(person__account__groups__in=event.groups.all()).distinct()
    return subscribers


def send_event_announcement(event_pk: int, recipient_email: str) -> None:
    try:
        event = Event.objects.get(pk=event_pk)
    except Event.DoesNotExist:
        logger.info("send_event_announcement: event %s no longer exists, skipping", event_pk)
        return

    message = emails.event_announcement(event, recipient_email)
    send_one_email(message)  # raises on failure, so django-q2 retries this recipient


def send_event_reminder(event_pk: int, recipient_email: str) -> None:
    try:
        event = Event.objects.get(pk=event_pk)
    except Event.DoesNotExist:
        logger.info("send_event_reminder: event %s no longer exists, skipping", event_pk)
        return

    message = emails.event_reminder(event, recipient_email)
    send_one_email(message)  # raises on failure, so django-q2 retries this recipient


def send_event_reminders() -> None:
    """Scheduled (DAILY) job -- selects events starting within the lead window
    that haven't been reminded yet, stamps reminder_sent_at BEFORE fan-out (so
    a Q_CLUSTER catch_up re-run can never double-send), then enqueues one task
    per recipient. Audience = the announcement audience, minus anyone who
    RSVP'd "non"."""
    now = timezone.now()
    window_end = now + datetime.timedelta(days=EVENT_REMINDER_LEAD_DAYS)
    upcoming = list(Event.objects.filter(start__gte=now, start__lte=window_end, reminder_sent_at__isnull=True))

    for event in upcoming:
        # Stamped before fan-out, in its own save -- a catch_up re-run that
        # lands after this point sees reminder_sent_at set and skips the event.
        event.reminder_sent_at = now
        event.save(update_fields=["reminder_sent_at"])

        declined_ids = set(Rsvp.objects.filter(event=event, response="no").values_list("person_id", flat=True))
        for subscriber in notification_audience(event):
            if subscriber.person_id not in declined_ids:
                async_task(send_event_reminder, event.pk, subscriber.person.email)

    logger.info("send_event_reminders: processed %d event(s)", len(upcoming))
