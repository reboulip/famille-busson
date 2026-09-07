from django.db.models.signals import pre_save
from django.dispatch import receiver

from annuaire.file_cleanup import register_file_cleanup

from .models import Photo


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


register_file_cleanup(Photo, "file", "thumbnail", "web")
