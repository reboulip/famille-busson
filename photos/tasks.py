"""Background-queue task wrappers (see docs/background_tasks.md).

`process_pending_photos` is the same batch logic the
`generate_photo_derivatives` management command runs by hand -- both call
this, so there is exactly one place that owns it, mirroring
documents/tasks.py's relationship to extract_document_content.
"""

from __future__ import annotations

from django.core.files.base import ContentFile
from django.utils import timezone

from .derivatives import generate_derivatives
from .models import Photo

DEFAULT_LIMIT = 20


def generate_photo_derivatives(photo_pk: int) -> None:
    """django-q2 task, enqueued once per newly-created Photo (see
    photos/signals.py's post_save/on_commit receiver). Re-queries fresh so it
    never operates on stale in-memory state; logs and skips if the photo was
    deleted before the task ran -- retrying can't make it exist again."""
    try:
        photo = Photo.objects.get(pk=photo_pk)
    except Photo.DoesNotExist:
        return
    _apply_derivatives(photo)


def process_pending_photos(limit: int = DEFAULT_LIMIT) -> tuple[int, int, list[str]]:
    """Batch safety net for photos whose enqueue was lost (worker down at
    upload time). Returns (processed, error_count, error_messages) -- the
    shape convention of documents.tasks.process_pending_document_files minus
    the OCR count, which has no photo equivalent."""
    candidates = Photo.objects.filter(derivative_status="pending")[:limit]
    processed = 0
    error_count = 0
    error_messages = []
    for photo in candidates:
        try:
            status = _apply_derivatives(photo)
        except Exception as exc:
            error_count += 1
            error_messages.append(f"Erreur sur {photo} : {exc}")
            continue
        processed += 1
        if status == "error":
            error_count += 1
    return processed, error_count, error_messages


def _apply_derivatives(photo: Photo) -> str:
    result = generate_derivatives(photo)
    photo.derivative_status = result.status
    photo.derivative_error = result.error
    photo.derivatives_generated_at = timezone.now()
    if result.status == "done":
        photo.thumbnail.save("thumbnail.webp", ContentFile(result.thumbnail_bytes), save=False)
        photo.web.save("web.webp", ContentFile(result.web_bytes), save=False)
        if result.taken_at is not None:
            photo.taken_at = result.taken_at
        if result.width is not None:
            photo.width = result.width
        if result.height is not None:
            photo.height = result.height
    photo.save()
    return result.status
