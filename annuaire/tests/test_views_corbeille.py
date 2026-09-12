import pytest
from django.urls import reverse

from documents.models import Category, Document

LOGIN_URL = "/annuaire/login/"


@pytest.mark.django_db
def test_corbeille_requires_login(client):
    response = client.get(reverse("corbeille-list"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_corbeille_requires_staff(auth_client):
    response = auth_client.get(reverse("corbeille-list"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_corbeille_lists_trashed_items_only(staff_client, account):
    category = Category.objects.create(name="Actes")
    Document.objects.create(title="Conservé", category=category)
    trashed = Document.objects.create(title="Supprimé", category=category)
    trashed.soft_delete(account)

    response = staff_client.get(reverse("corbeille-list"))
    content = response.content.decode()
    assert "Supprimé" in content
    assert "Conservé" not in content


@pytest.mark.django_db
def test_corbeille_restore_view(staff_client, account):
    category = Category.objects.create(name="Actes")
    document = Document.objects.create(title="À restaurer", category=category)
    document.soft_delete(account)

    response = staff_client.post(reverse("corbeille-restore", args=["documents", "document", document.pk]))
    assert response.status_code == 302
    assert Document.objects.filter(pk=document.pk).exists()


@pytest.mark.django_db
def test_corbeille_purge_view(staff_client, account):
    category = Category.objects.create(name="Actes")
    document = Document.objects.create(title="À purger", category=category)
    document.soft_delete(account)

    response = staff_client.post(reverse("corbeille-purge", args=["documents", "document", document.pk]))
    assert response.status_code == 302
    assert not Document.all_objects.filter(pk=document.pk).exists()


@pytest.mark.django_db
def test_corbeille_rejects_model_outside_allowlist(staff_client, person):
    response = staff_client.post(reverse("corbeille-restore", args=["annuaire", "person", person.pk]))
    assert response.status_code == 404
