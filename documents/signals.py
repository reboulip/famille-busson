from django.db.models.signals import pre_save
from django.dispatch import receiver

from annuaire.file_cleanup import register_file_cleanup

from .models import DocumentFile


@receiver(pre_save, sender=DocumentFile)
def reset_extraction_on_file_change(sender, instance, **kwargs):
    """Replacing a file must invalidate whatever was extracted from the old
    one -- otherwise a replaced scan stays searchable by its old content, an
    access-control-adjacent leak, not just staleness. Connected before
    register_file_cleanup() below so its own pre_save handler sees the
    thumbnail already cleared here and schedules the old thumbnail file for
    deletion too (signal receivers on the same sender fire in connection
    order)."""
    if instance.pk is None:
        return
    try:
        old = DocumentFile.objects.get(pk=instance.pk)
    except DocumentFile.DoesNotExist:
        return
    if old.file.name != instance.file.name:
        instance.extraction_status = "pending"
        instance.extracted_text = ""
        instance.extraction_error = ""
        instance.extracted_at = None
        instance.ocr_used = False
        instance.thumbnail = None


register_file_cleanup(DocumentFile, "file", "thumbnail")
