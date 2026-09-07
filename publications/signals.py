from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_q.tasks import async_task

from annuaire.file_cleanup import register_file_cleanup
from annuaire.models import Settings as NotificationSettings

from .models import Attachment, BlogPost
from .tasks import send_blog_post_notification

register_file_cleanup(Attachment, "file")


@receiver(post_save, sender=BlogPost)
def notify_subscribers_of_new_post(sender, instance, created, **kwargs):
    if not created:
        return

    def _enqueue():
        # Deferred to after commit: post_save fires before form.save_m2m() adds the
        # authors, and the task re-queries the post fresh -- enqueueing before commit
        # could have it run (on a fast worker) against a row whose authors aren't
        # attached yet, or that isn't visible to the worker's own transaction at all.
        subscribers = (
            NotificationSettings.objects.filter(notify_on_new_blog_post=True)
            .exclude(person__email__isnull=True)
            .exclude(person__email="")
            .exclude(person__deceased=True)
            .select_related("person")
        )
        for subscriber in subscribers:
            async_task(send_blog_post_notification, instance.pk, subscriber.person.email)

    transaction.on_commit(_enqueue)
