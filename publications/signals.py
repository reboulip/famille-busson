from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from annuaire import emails
from annuaire.email_utils import send_bulk_emails
from annuaire.file_cleanup import register_file_cleanup
from annuaire.models import Settings as NotificationSettings

from .models import Attachment, BlogPost

register_file_cleanup(Attachment, "file")


@receiver(post_save, sender=BlogPost)
def notify_subscribers_of_new_post(sender, instance, created, **kwargs):
    if not created:
        return

    def _send():
        # Deferred to after commit: post_save fires before form.save_m2m() adds the
        # authors, so building the messages here (not just sending them) is what
        # keeps the byline populated -- a stopgap until Phase 9.7's queue replaces
        # this signal-based send entirely.
        subscribers = (
            NotificationSettings.objects.filter(notify_on_new_blog_post=True)
            .exclude(person__email__isnull=True)
            .exclude(person__email="")
            .exclude(person__deceased=True)
            .select_related("person")
        )
        if not subscribers:
            return
        messages = [
            emails.new_blog_post(instance, subscriber.person.email, recipient=subscriber.person)
            for subscriber in subscribers
        ]
        send_bulk_emails(messages)

    transaction.on_commit(_send)
