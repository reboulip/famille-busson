"""Soft delete for the corbeille (14.5) -- publications, documents, photos.

`.delete()` keeps meaning "really, permanently delete" everywhere: person_merge.py's
`loser.delete()`, the file-cleanup `post_delete` receivers in annuaire/file_cleanup.py,
documents/signals.py, photos/signals.py, and Relation's own inverse-delete signal in
annuaire/signals.py all fire correctly ONLY at real deletion time. This module never
overrides `Model.delete()` -- soft-delete is a separate, explicit `soft_delete()` method,
so every one of those receivers keeps firing exactly once, at the moment the bytes/rows
actually need to go away (purge time), not at trash time.

No cascade marking: soft-deleting an Album does not soft-delete its Photos. Every photo
read path is already album-scoped (photos.access.accessible_photos), so a trashed
album's photos simply become unreachable through normal browsing.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from .audit import record_audit_event
from .models import AuditEvent


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)


class SoftDeleteManager(models.Manager):
    """Declared FIRST on every model using SoftDeleteModelMixin, so it becomes
    the default manager -- reverse relations and the admin changelist see only
    live rows. `all_objects = models.Manager()` (declared second) is the
    unfiltered escape hatch for the corbeille listing and the purge job."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteModelMixin(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="Supprimé le")
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Supprimé par",
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()  # noqa: DJ012 -- order matches the Django style guide; false positive

    class Meta:
        abstract = True

    def soft_delete(self, actor) -> None:
        self.deleted_at = timezone.now()
        self.deleted_by = actor
        self.save(update_fields=["deleted_at", "deleted_by"])
        record_audit_event(
            self, action=AuditEvent.Action.DELETE, changes={"corbeille": {"to": "supprimé"}}, actor=actor
        )

    def restore(self) -> None:
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["deleted_at", "deleted_by"])
        record_audit_event(self, action=AuditEvent.Action.RESTORE, changes={"corbeille": {"to": "restauré"}})

    def purge(self) -> None:
        """Permanent deletion of an already-trashed row -- logged explicitly
        as PURGE (distinct from the DELETE recorded at soft_delete() time),
        then the real .delete(), which fires every normal post_delete
        receiver (file cleanup, etc.) exactly as a direct hard delete would."""
        record_audit_event(self, action=AuditEvent.Action.PURGE, changes={"corbeille": {"to": "purgé définitivement"}})
        self.delete()
