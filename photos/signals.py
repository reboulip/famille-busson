from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django_q.tasks import async_task

from annuaire.file_cleanup import register_file_cleanup

from .models import Photo
from .tasks import generate_photo_derivatives


@receiver(pre_save, sender=Photo)
def reset_derivatives_on_file_change(sender, instance, **kwargs):
    """Replacing a photo's original file must invalidate whatever was derived
    from the old one -- otherwise a replaced photo keeps a stale thumbnail/web
    rendition forever. Connected before register_file_cleanup() below so its
    own pre_save handler sees the derivative fields already cleared here and
    schedules the old derivative files for deletion too (signal receivers on
    the same sender fire in connection order)."""
    if instance.pk is None:
        return
    try:
        old = Photo.objects.get(pk=instance.pk)
    except Photo.DoesNotExist:
        return
    if old.file.name != instance.file.name:
        instance.thumbnail = None
        instance.web = None
        instance.derivative_status = "pending"
        instance.derivative_error = ""
        instance.derivatives_generated_at = None


@receiver(post_save, sender=Photo)
def enqueue_derivative_generation(sender, instance, created, **kwargs):
    """Enqueued from post_save/on_commit -- never called from PhotoUploadView
    directly, which is what keeps the upload endpoint and derivative
    generation fully file-disjoint. Deferred to after commit so the worker
    (which may run on a separate process/connection) is guaranteed to see the
    row; only on creation, since nothing yet lets a photo's file be replaced."""
    if not created:
        return

    def _enqueue():
        async_task(generate_photo_derivatives, instance.pk)

    transaction.on_commit(_enqueue)


register_file_cleanup(Photo, "file", "thumbnail", "web")
