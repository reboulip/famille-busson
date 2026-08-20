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
def test_bulk_create_does_not_force_password_change(staff_client, db):
    staff_client.post(reverse("bulk-account-create"), {"emails": "new@example.com"})
    account = Account.objects.get(email="new@example.com")
    assert account.must_change_password is False


@pytest.mark.django_db
def test_bulk_create_password_is_usable_but_undisclosed(staff_client, db):
    staff_client.post(reverse("bulk-account-create"), {"emails": "new@example.com"})
    account = Account.objects.get(email="new@example.com")
    assert account.has_usable_password()


@pytest.mark.django_db
def test_bulk_create_reset_existing_account(staff_client, account):
    old_hash = account.password
    staff_client.post(reverse("bulk-account-create"), {"emails": account.email})
    account.refresh_from_db()
    assert account.password != old_hash


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
def test_bulk_create_sends_reset_link_email_for_new_account(staff_client, db):
    response = staff_client.post(reverse("bulk-account-create"), {"emails": "new@example.com"})
    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.to == ["new@example.com"]
    reset_url = response.context["results"][0]["reset_url"]
    assert reset_url in sent.body


@pytest.mark.django_db
def test_bulk_create_never_puts_a_password_in_the_email(staff_client, db):
    staff_client.post(reverse("bulk-account-create"), {"emails": "new@example.com"})
    account = Account.objects.get(email="new@example.com")
    sent = mail.outbox[0]
    assert account.password not in sent.body
    assert "Mot de passe" not in sent.body


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
def test_bulk_create_email_failure_still_creates_account_and_shows_reset_link(staff_client, db, monkeypatch):
    import annuaire.views as annuaire_views

    def _raise(*args, **kwargs):
        raise Exception("SMTP down")

    monkeypatch.setattr(annuaire_views, "send_mail", _raise)
    response = staff_client.post(reverse("bulk-account-create"), {"emails": "new@example.com"})

    assert Account.objects.filter(email="new@example.com").exists()
    result = response.context["results"][0]
    assert result["email_sent"] is False
    assert result["reset_url"]  # still shown on screen as a fallback
    msgs = [str(m) for m in response.context["messages"]]
    assert any("Échec de l'envoi" in m for m in msgs)


@pytest.mark.django_db
def test_bulk_create_handles_more_than_thirty_accounts(staff_client, db):
    emails = [f"bulk{i}@example.com" for i in range(35)]
    response = staff_client.post(reverse("bulk-account-create"), {"emails": "\n".join(emails)})

    assert response.status_code == 200
    assert Account.objects.filter(email__in=emails).count() == 35
    assert len(mail.outbox) == 35
    assert all(r["email_sent"] for r in response.context["results"])


@pytest.mark.django_db
def test_bulk_create_isolates_account_creation_failure(staff_client, db, monkeypatch):
    from annuaire.models import Account as AccountModel

    original_save = AccountModel.save

    def _save(self, *args, **kwargs):
        if self.email == "bad@example.com":
            raise Exception("DB down")
        return original_save(self, *args, **kwargs)

    monkeypatch.setattr(AccountModel, "save", _save)

    response = staff_client.post(
        reverse("bulk-account-create"),
        {"emails": "good1@example.com\nbad@example.com\ngood2@example.com"},
    )

    assert Account.objects.filter(email="good1@example.com").exists()
    assert Account.objects.filter(email="good2@example.com").exists()
    assert not Account.objects.filter(email="bad@example.com").exists()

    results = {r["email"]: r for r in response.context["results"]}
    assert results["bad@example.com"]["status"] == "error"
    assert results["bad@example.com"]["email_sent"] is False
    assert results["good1@example.com"]["email_sent"] is True
    assert results["good2@example.com"]["email_sent"] is True

    msgs = [str(m) for m in response.context["messages"]]
    assert any("Échec de la création du compte" in m for m in msgs)


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
