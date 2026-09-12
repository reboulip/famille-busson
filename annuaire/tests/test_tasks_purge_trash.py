import datetime

import pytest
from django.utils import timezone

from annuaire.tasks import purge_expired_trash
from documents.models import Category, Document


@pytest.mark.django_db
def test_purge_expired_trash_deletes_only_rows_past_retention(account, settings):
    settings.TRASH_RETENTION_DAYS = 30
    category = Category.objects.create(name="Actes")

    old = Document.objects.create(title="Ancien", category=category)
    old.soft_delete(account)
    Document.all_objects.filter(pk=old.pk).update(deleted_at=timezone.now() - datetime.timedelta(days=31))

    recent = Document.objects.create(title="Récent", category=category)
    recent.soft_delete(account)

    kept = Document.objects.create(title="Conservé", category=category)

    purge_expired_trash()

    assert not Document.all_objects.filter(pk=old.pk).exists()
    assert Document.all_objects.filter(pk=recent.pk).exists()
    assert Document.objects.filter(pk=kept.pk).exists()
