from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_q.tasks import async_task

from .models import Event
from .tasks import notification_audience, send_event_announcement


@receiver(post_save, sender=Event)
def notify_subscribers_of_new_event(sender, instance, created, **kwargs):
    if not created:
        return

    def _enqueue():
        # Deferred to after commit: post_save fires before form.save_m2m() adds
        # the groups, so computing the audience here would see zero groups and
        # mail a restricted event to the whole family -- this is the sprint's
        # highest-severity risk. The task re-queries the event fresh anyway.
        for subscriber in notification_audience(instance):
            async_task(send_event_announcement, instance.pk, subscriber.person.email)

    transaction.on_commit(_enqueue)
