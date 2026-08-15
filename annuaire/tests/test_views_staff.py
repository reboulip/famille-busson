import json
import pytest
from django.core import mail
from django.urls import reverse
from annuaire.models import Account


LOGIN_URL = "/annuaire/login/"


# ---------------------------------------------------------------------------
# BulkAccountCreateView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_bulk_create_requires_login(client):
    response = client.get(reverse("bulk-account-create"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_bulk_create_requires_staff(auth_client):
    response = auth_client.get(reverse("bulk-account-create"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_bulk_create_get_returns_200(staff_client):
    response = staff_client.get(reverse("bulk-account-create"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_bulk_create_creates_new_accounts(staff_client, db):
    response = staff_client.post(
        reverse("bulk-account-create"),
        {"emails": "new1@example.com\nnew2@example.com"},
    )
    assert response.status_code == 200
    assert Account.objects.filter(email="new1@example.com").exists()
    assert Account.objects.filter(email="new2@example.com").exists()


@pytest.mark.django_db
def test_bulk_create_sets_must_change_password(staff_client, db):
    staff_client.post(reverse("bulk-account-create"), {"emails": "new@example.com"})
    account = Account.objects.get(email="new@example.com")
    assert account.must_change_password is True


@pytest.mark.django_db
def test_bulk_create_temp_password_is_usable(staff_client, db):
    staff_client.post(reverse("bulk-account-create"), {"emails": "new@example.com"})
    account = Account.objects.get(email="new@example.com")
    assert account.has_usable_password()


@pytest.mark.django_db
def test_bulk_create_reset_existing_account(staff_client, account):
    old_hash = account.password
    staff_client.post(reverse("bulk-account-create"), {"emails": account.email})
    account.refresh_from_db()
    assert account.password != old_hash
    assert account.must_change_password is True


@pytest.mark.django_db
def test_bulk_create_results_in_context(staff_client, db):
    response = staff_client.post(reverse("bulk-account-create"), {"emails": "ctx@example.com"})
    assert "results" in response.context
    assert len(response.context["results"]) == 1
    assert response.context["results"][0]["email"] == "ctx@example.com"
    assert response.context["results"][0]["status"] == "created"


@pytest.mark.django_db
def test_bulk_create_shows_warning_message_for_reset(staff_client, account):
    response = staff_client.post(
        reverse("bulk-account-create"),
        {"emails": account.email},
        follow=True,
    )
    msgs = [str(m) for m in response.context["messages"]]
    assert any(account.email in m for m in msgs)


@pytest.mark.django_db
def test_bulk_create_invalid_email_shows_form_error(staff_client, db):
    response = staff_client.post(reverse("bulk-account-create"), {"emails": "notanemail"})
    assert response.status_code == 200
    assert response.context["form"].errors
    assert not Account.objects.filter(email="notanemail").exists()


@pytest.mark.django_db
def test_bulk_create_sends_credentials_email_for_new_account(staff_client, db):
    response = staff_client.post(reverse("bulk-account-create"), {"emails": "new@example.com"})
    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.to == ["new@example.com"]
    temp_password = response.context["results"][0]["temp_password"]
    assert temp_password in sent.body


@pytest.mark.django_db
def test_bulk_create_sends_reset_email_with_distinct_subject(staff_client, account):
    staff_client.post(reverse("bulk-account-create"), {"emails": account.email})
    assert len(mail.outbox) == 1
    assert "réinitialisé" in mail.outbox[0].subject


@pytest.mark.django_db
def test_bulk_create_marks_results_email_sent(staff_client, db):
    response = staff_client.post(reverse("bulk-account-create"), {"emails": "new@example.com"})
    assert response.context["results"][0]["email_sent"] is True


@pytest.mark.django_db
def test_bulk_create_email_failure_still_creates_account_and_shows_password(staff_client, db, monkeypatch):
    import annuaire.views as annuaire_views

    def _raise(*args, **kwargs):
        raise Exception("SMTP down")

    monkeypatch.setattr(annuaire_views, "send_mail", _raise)
    response = staff_client.post(reverse("bulk-account-create"), {"emails": "new@example.com"})

    assert Account.objects.filter(email="new@example.com").exists()
    result = response.context["results"][0]
    assert result["email_sent"] is False
    assert result["temp_password"]  # still shown on screen as a fallback
    msgs = [str(m) for m in response.context["messages"]]
    assert any("Échec de l'envoi" in m for m in msgs)


# ---------------------------------------------------------------------------
# check_emails_ajax
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_check_emails_ajax_returns_existing(staff_client, account):
    response = staff_client.post(
        reverse("check-emails-ajax"),
        data=json.dumps({"emails": [account.email, "nobody@example.com"]}),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.json()
    assert account.email in data["existing"]
    assert "nobody@example.com" not in data["existing"]


@pytest.mark.django_db
def test_check_emails_ajax_requires_staff(auth_client, account):
    response = auth_client.post(
        reverse("check-emails-ajax"),
        data=json.dumps({"emails": [account.email]}),
        content_type="application/json",
    )
    assert response.status_code == 403
