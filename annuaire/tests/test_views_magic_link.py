from datetime import datetime, timedelta

import pytest
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import Client
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from annuaire.tokens import magic_link_token_generator

LOGIN_URL = "/annuaire/login/"
CHANGE_URL = "/annuaire/password/change/"


def _magic_link_confirm_url(account):
    uid = urlsafe_base64_encode(force_bytes(account.pk))
    token = magic_link_token_generator.make_token(account)
    return reverse("magic-link-confirm-token", kwargs={"uidb64": uid, "token": token})


# ---------------------------------------------------------------------------
# MagicLinkRequestView / MagicLinkSentView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_magic_link_request_get_returns_200(client):
    response = client.get(reverse("magic-link-request"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_magic_link_request_post_valid_email_sends_link_and_redirects(client, account):
    response = client.post(reverse("magic-link-request"), {"email": account.email})
    assert response.status_code == 302
    assert response["Location"] == reverse("magic-link-sent")
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [account.email]
    # never hardcode "15 minutes" in the email -- assert against the actual setting
    assert f"{settings.MAGIC_LINK_TIMEOUT // 60} minutes" in mail.outbox[0].body


@pytest.mark.django_db
def test_magic_link_request_post_unknown_email_still_redirects_no_email_sent(client, db):
    response = client.post(reverse("magic-link-request"), {"email": "nobody@example.com"})
    assert response.status_code == 302
    assert response["Location"] == reverse("magic-link-sent")
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_magic_link_sent_get_returns_200(client):
    response = client.get(reverse("magic-link-sent"))
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Happy path -- request -> emailed link -> two-step confirm -> logged in
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_magic_link_full_round_trip_via_emailed_link(client, account, person):
    client.post(reverse("magic-link-request"), {"email": account.email})
    assert len(mail.outbox) == 1
    body = mail.outbox[0].body

    import re

    match = re.search(r"https?://[^\s]+(/annuaire/login/magic/\S+/\S+/)", body)
    assert match is not None, f"magic link not found in email body:\n{body}"
    confirm_token_path = match.group(1)

    c = Client()
    get_response = c.get(confirm_token_path)
    assert get_response.status_code == 302
    confirm_url = get_response["Location"]

    show_response = c.get(confirm_url)
    assert show_response.status_code == 200
    assert show_response.context["validlink"] is True

    post_response = c.post(confirm_url)
    assert post_response.status_code == 302
    # `account` has never logged in before -- this is a first connection.
    assert post_response["Location"] == reverse("person-edit", kwargs={"pk": person.pk})

    account.refresh_from_db()
    assert account.last_login is not None

    protected_response = c.get(reverse("directory"))
    assert protected_response.status_code == 200


@pytest.mark.django_db
def test_magic_link_first_login_redirects_to_person_edit(account, person):
    url = _magic_link_confirm_url(account)
    c = Client()
    get_response = c.get(url)
    assert get_response.status_code == 302
    confirm_url = get_response["Location"]

    post_response = c.post(confirm_url)
    assert post_response.status_code == 302
    assert post_response["Location"] == reverse("person-edit", kwargs={"pk": person.pk})


@pytest.mark.django_db
def test_magic_link_routine_login_by_existing_member_redirects_home(account, person):
    # Existing member (already logged in before) -- routine magic-link login
    # must land on home, not the first-login edit page.
    login_client = Client()
    login_client.login(username=account.email, password="testpass123!")
    login_client.logout()
    account.refresh_from_db()
    assert account.last_login is not None

    url = _magic_link_confirm_url(account)
    c = Client()
    get_response = c.get(url)
    confirm_url = get_response["Location"]
    post_response = c.post(confirm_url)
    assert post_response.status_code == 302
    assert post_response["Location"] == reverse("home")


@pytest.mark.django_db
def test_magic_link_must_change_password_redirects_forced(account, person):
    account.must_change_password = True
    account.save()

    url = _magic_link_confirm_url(account)
    c = Client()
    get_response = c.get(url)
    confirm_url = get_response["Location"]
    post_response = c.post(confirm_url)
    assert post_response.status_code == 302
    assert post_response["Location"] == reverse("password-change-forced")


@pytest.mark.django_db
def test_magic_link_confirm_get_shows_button_and_does_not_log_in(account, person):
    url = _magic_link_confirm_url(account)
    c = Client()
    get_response = c.get(url)
    confirm_url = get_response["Location"]
    show_response = c.get(confirm_url)
    assert show_response.status_code == 200
    assert show_response.context["validlink"] is True
    # GET must never itself log the user in -- only POST does.
    protected_response = c.get(reverse("directory"))
    assert protected_response.status_code == 302
    assert LOGIN_URL in protected_response["Location"]


# ---------------------------------------------------------------------------
# Invalid-link branches -- must all render validlink=False, never crash
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_magic_link_confirm_bad_uidb64_invalid(client, db):
    bad_url = reverse("magic-link-confirm-token", kwargs={"uidb64": "not-valid-b64!!", "token": "abc-def"})
    response = client.get(bad_url)
    assert response.status_code == 200
    assert response.context["validlink"] is False


@pytest.mark.django_db
def test_magic_link_confirm_unknown_account_pk_invalid(client, db):
    uid = urlsafe_base64_encode(force_bytes(999999))
    bad_url = reverse("magic-link-confirm-token", kwargs={"uidb64": uid, "token": "abc-def"})
    response = client.get(bad_url)
    assert response.status_code == 200
    assert response.context["validlink"] is False


@pytest.mark.django_db
def test_magic_link_confirm_tampered_token_invalid(client, account):
    uid = urlsafe_base64_encode(force_bytes(account.pk))
    token = magic_link_token_generator.make_token(account)
    last_char = token[-1]
    tampered = token[:-1] + ("a" if last_char != "a" else "b")
    bad_url = reverse("magic-link-confirm-token", kwargs={"uidb64": uid, "token": tampered})
    response = client.get(bad_url)
    assert response.status_code == 200
    assert response.context["validlink"] is False


@pytest.mark.django_db
def test_magic_link_confirm_expired_token_invalid(client, account, monkeypatch):
    url = _magic_link_confirm_url(account)
    future = datetime.now() + timedelta(seconds=settings.MAGIC_LINK_TIMEOUT + 60)
    monkeypatch.setattr(magic_link_token_generator, "_now", lambda: future)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["validlink"] is False


@pytest.mark.django_db
def test_password_reset_token_rejected_by_magic_link_endpoint(client, account):
    # Critical salt-isolation check: bulk_account_create.html shows live
    # password-reset URLs on screen to staff -- without a distinct key_salt,
    # that URL could be replayed here to silently log in as another member.
    uid = urlsafe_base64_encode(force_bytes(account.pk))
    token = default_token_generator.make_token(account)
    url = reverse("magic-link-confirm-token", kwargs={"uidb64": uid, "token": token})
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["validlink"] is False


@pytest.mark.django_db
def test_magic_link_token_rejected_by_password_reset_endpoint(client, account):
    uid = urlsafe_base64_encode(force_bytes(account.pk))
    token = magic_link_token_generator.make_token(account)
    url = reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token})
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["validlink"] is False


@pytest.mark.django_db
def test_magic_link_reused_token_after_login_is_invalid(account, person):
    url = _magic_link_confirm_url(account)
    c = Client()
    get_response = c.get(url)
    confirm_url = get_response["Location"]
    post_response = c.post(confirm_url)
    assert post_response.status_code == 302

    # Same emailed link, fresh (unauthenticated) client: last_login has since
    # changed, which the token's own hash is sensitive to, so it's invalidated.
    fresh_client = Client()
    reuse_response = fresh_client.get(url)
    assert reuse_response.status_code == 200
    assert reuse_response.context["validlink"] is False


@pytest.mark.django_db
def test_magic_link_inactive_account_rejected_at_post(account, person):
    account.is_active = False
    account.save()

    url = _magic_link_confirm_url(account)
    c = Client()
    get_response = c.get(url)
    confirm_url = get_response["Location"]
    post_response = c.post(confirm_url)
    assert post_response.status_code == 200
    assert post_response.context["validlink"] is False
    assert "_auth_user_id" not in c.session


@pytest.mark.django_db
def test_magic_link_confirm_no_token_no_session_invalid(client, account):
    uid = urlsafe_base64_encode(force_bytes(account.pk))
    url = reverse("magic-link-confirm", kwargs={"uidb64": uid})
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["validlink"] is False


# ---------------------------------------------------------------------------
# login_not_required / ForcePasswordChangeMiddleware exemption
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_magic_link_urls_accessible_when_anonymous(client, account):
    uid = urlsafe_base64_encode(force_bytes(account.pk))
    urls = [
        reverse("magic-link-request"),
        reverse("magic-link-sent"),
        reverse("magic-link-confirm", kwargs={"uidb64": uid}),
    ]
    for url in urls:
        response = client.get(url)
        assert response.status_code == 200
        assert LOGIN_URL not in response.get("Location", "")


@pytest.mark.django_db
def test_magic_link_confirm_token_url_accessible_when_anonymous(client, account):
    url = _magic_link_confirm_url(account)
    response = client.get(url)
    assert response.status_code == 302
    assert response["Location"] != LOGIN_URL
    assert not response["Location"].startswith(LOGIN_URL + "?")


@pytest.mark.django_db
def test_magic_link_confirm_url_is_exempt_from_forced_password_change_redirect(account, person):
    account.must_change_password = True
    account.save()
    c = Client()
    c.login(username=account.email, password="testpass123!")
    account.refresh_from_db()
    url = _magic_link_confirm_url(account)
    response = c.get(url)
    assert response.status_code in (200, 302)
    assert CHANGE_URL not in response.get("Location", "")
