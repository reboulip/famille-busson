import pytest

from annuaire.models import AuditEvent
from documents.models import Document


@pytest.mark.django_db
def test_document_create_logs_audit_event(category):
    document = Document.objects.create(title="Acte de naissance", category=category)
    event = AuditEvent.objects.get(content_type__model="document", object_id=str(document.pk))
    assert event.action == AuditEvent.Action.CREATE


@pytest.mark.django_db
def test_document_update_logs_tracked_field_change(document):
    AuditEvent.objects.all().delete()
    document.title = "Acte de naissance (corrigé)"
    document.save()
    event = AuditEvent.objects.get(
        content_type__model="document", object_id=str(document.pk), action=AuditEvent.Action.UPDATE
    )
    assert event.changes["title"] == {"from": "Acte de naissance", "to": "Acte de naissance (corrigé)"}


@pytest.mark.django_db
def test_document_delete_logs_audit_event(document):
    pk = document.pk
    document.delete()
    assert AuditEvent.objects.filter(
        content_type__model="document", object_id=str(pk), action=AuditEvent.Action.DELETE
    ).exists()
