from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django_q.tasks import async_task

from annuaire.file_cleanup import register_file_cleanup
from annuaire.markdown_utils import markdown_to_text
from annuaire.search.indexing import register_search_index
from annuaire.search.registry import SearchSpec

from .access import accessible_albums, accessible_photos
from .models import Album, Photo
from .tasks import generate_photo_derivatives

register_search_index(
    Album,
    SearchSpec(
        weights={"A": lambda a: a.title, "B": lambda a: markdown_to_text(a.description)},
        source_fields=frozenset({"title", "description"}),
        accessible=accessible_albums,
        label="Albums",
        card_template="photos/_album_card.html",
        order=["-created_at"],
    ),
)

register_search_index(
    Photo,
    SearchSpec(
        weights={"A": lambda p: p.caption or "", "B": lambda p: markdown_to_text(p.album.description)},
        source_fields=frozenset({"caption"}),
        accessible=accessible_photos,
        label="Photos",
        # Not _photo_card.html: that partial is coupled to the document-viewer
        # lightbox strip (document_viewer.js expects the surrounding markup a
        # search results page doesn't have) -- a plain tile instead.
        card_template="photos/_photo_search_card.html",
        order=["uploaded_at"],
    ),
)


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
