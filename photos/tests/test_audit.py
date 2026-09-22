import pytest

from annuaire.models import AuditEvent
from photos.models import Album


@pytest.mark.django_db
def test_album_create_logs_audit_event():
    album = Album.objects.create(title="Été 2025")
    event = AuditEvent.objects.get(content_type__model="album", object_id=str(album.pk))
    assert event.action == AuditEvent.Action.CREATE


@pytest.mark.django_db
def test_album_update_logs_tracked_field_change(album):
    AuditEvent.objects.all().delete()
    album.title = "Été 2025 (renommé)"
    album.save()
    event = AuditEvent.objects.get(
        content_type__model="album", object_id=str(album.pk), action=AuditEvent.Action.UPDATE
    )
    assert event.changes["title"] == {"from": "Été 2025", "to": "Été 2025 (renommé)"}


@pytest.mark.django_db
def test_photo_create_logs_audit_event(photo):
    event = AuditEvent.objects.get(content_type__model="photo", object_id=str(photo.pk))
    assert event.action == AuditEvent.Action.CREATE


@pytest.mark.django_db
def test_photo_delete_logs_audit_event(photo):
    pk = photo.pk
    photo.delete()
    assert AuditEvent.objects.filter(
        content_type__model="photo", object_id=str(pk), action=AuditEvent.Action.DELETE
    ).exists()
