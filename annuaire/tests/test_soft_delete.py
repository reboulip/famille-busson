import pytest

from annuaire.models import AuditEvent
from documents.models import Category, Document


@pytest.fixture
def category(db):
    return Category.objects.create(name="Actes de famille")


@pytest.fixture
def document(db, category):
    return Document.objects.create(title="Acte de naissance", category=category)


@pytest.mark.django_db
def test_soft_delete_excludes_from_default_manager_but_not_all_objects(document, account):
    document.soft_delete(account)
    assert not Document.objects.filter(pk=document.pk).exists()
    assert Document.all_objects.filter(pk=document.pk).exists()


@pytest.mark.django_db
def test_soft_delete_stamps_deleted_at_and_deleted_by(document, account):
    document.soft_delete(account)
    document.refresh_from_db()
    assert document.deleted_at is not None
    assert document.deleted_by_id == account.pk


@pytest.mark.django_db
def test_soft_delete_logs_audit_event(document, account):
    AuditEvent.objects.all().delete()
    document.soft_delete(account)
    event = AuditEvent.objects.get(content_type__model="document", object_id=str(document.pk))
    assert event.action == AuditEvent.Action.DELETE
    assert event.actor_id == account.pk


@pytest.mark.django_db
def test_restore_reincludes_in_default_manager_and_logs_restore(document, account):
    document.soft_delete(account)
    AuditEvent.objects.all().delete()
    document.restore()
    assert Document.objects.filter(pk=document.pk).exists()
    document.refresh_from_db()
    assert document.deleted_at is None
    assert document.deleted_by_id is None
    event = AuditEvent.objects.get(content_type__model="document", object_id=str(document.pk))
    assert event.action == AuditEvent.Action.RESTORE


@pytest.mark.django_db
def test_purge_permanently_deletes_and_logs_purge(document, account):
    pk = document.pk
    document.soft_delete(account)
    AuditEvent.objects.all().delete()
    document.purge()
    assert not Document.all_objects.filter(pk=pk).exists()
    event = AuditEvent.objects.get(content_type__model="document", object_id=str(pk), action=AuditEvent.Action.PURGE)
    assert event.object_repr
