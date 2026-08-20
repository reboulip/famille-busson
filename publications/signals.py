from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from annuaire.email_utils import send_bulk_emails
from annuaire.file_cleanup import register_file_cleanup
from annuaire.models import Settings as NotificationSettings

from .models import Attachment, BlogPost

register_file_cleanup(Attachment, "file")


@receiver(post_save, sender=BlogPost)
def notify_subscribers_of_new_post(sender, instance, created, **kwargs):
    if not created:
        return
    subscribers = (
        NotificationSettings.objects.filter(notify_on_new_blog_post=True)
        .exclude(person__email__isnull=True)
        .exclude(person__email="")
        .select_related("person")
    )
    if not subscribers:
        return
    post_url = settings.SITE_BASE_URL.rstrip("/") + reverse("blogpost-detail", kwargs={"pk": instance.pk})
    subject = f"Nouvel article : {instance.title}"
    body = f"Un nouvel article a été publié sur le site de la famille Busson :\n\n{instance.title}\n\n{post_url}"
    messages = [(subscriber.person.email, subject, body) for subscriber in subscribers]
    send_bulk_emails(messages)
