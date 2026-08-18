import logging

from django.db import models, transaction
from django.db.models.signals import post_delete, pre_save

logger = logging.getLogger(__name__)


def register_file_cleanup(model: type[models.Model], *field_names: str) -> None:
    """Delete the files behind FileField/ImageField columns when a row is
    deleted, and delete the previous file when it's replaced or cleared.

    Django never does this on its own -- a deleted/replaced row otherwise
    leaves an orphaned file under MEDIA_ROOT forever.
    """

    def _delete_file(instance, field_name):
        field_file = getattr(instance, field_name)
        name = field_file.name if field_file else None
        if not name:
            return
        storage = field_file.storage
        if model.objects.filter(**{field_name: name}).exclude(pk=instance.pk).exists():
            return
        try:
            storage.delete(name)
        except OSError:
            logger.warning("Could not delete orphaned file %r for %s", name, model.__name__)

    def _on_post_delete(sender, instance, **kwargs):
        for field_name in field_names:
            transaction.on_commit(lambda instance=instance, field_name=field_name: _delete_file(instance, field_name))

    def _on_pre_save(sender, instance, **kwargs):
        if instance.pk is None:
            return
        try:
            old_instance = model.objects.get(pk=instance.pk)
        except model.DoesNotExist:
            return
        for field_name in field_names:
            old_name = getattr(old_instance, field_name).name if getattr(old_instance, field_name) else None
            new_name = getattr(instance, field_name).name if getattr(instance, field_name) else None
            if old_name and old_name != new_name:
                transaction.on_commit(
                    lambda old_instance=old_instance, field_name=field_name: _delete_file(old_instance, field_name)
                )

    post_delete.connect(_on_post_delete, sender=model, weak=False)
    pre_save.connect(_on_pre_save, sender=model, weak=False)
