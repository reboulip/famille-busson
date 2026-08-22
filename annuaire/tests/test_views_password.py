import re

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import Client
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

LOGIN_URL = "/annuaire/login/"
CHANGE_URL = "/annuaire/password/change/"
STRONG_PASSWORD = "V3ryStr0ng!Pass"


def _reset_confirm_url(account):
    uid = urlsafe_base64_encode(force_bytes(account.pk))
    token = default_token_generator.make_token(account)
    return reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token})


# ---------------------------------------------------------------------------
# ForcePasswordChangeMiddleware
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_middleware_redirects_must_change_user(account, person):
    account.must_change_password = True
    account.save()
    c = Client()
    c.login(username=account.email, password="testpass123!")
    response = c.get(reverse("directory"))
    assert response.status_code == 302
    assert CHANGE_URL in response["Location"]


@pytest.mark.django_db
def test_middleware_allows_password_change_url(account, person):
    account.must_change_password = True
    account.save()
    c = Client()
    c.login(username=account.email, password="testpass123!")
    response = c.get(reverse("password-change-forced"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_middleware_allows_logout_url(account, person):
    account.must_change_password = True
    account.save()
    c = Client()
    c.login(username=account.email, password="testpass123!")
    response = c.post(reverse("logout"))
    assert response.status_code in (200, 302)
    assert CHANGE_URL not in response.get("Location", "")


@pytest.mark.django_db
def test_middleware_no_effect_on_normal_user(auth_client):
    response = auth_client.get(reverse("directory"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_middleware_no_effect_on_anonymous(client):
    response = client.get(reverse("directory"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


# ---------------------------------------------------------------------------
# ForcedPasswordChangeView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_forced_change_requires_login(client):
    response = client.get(reverse("password-change-forced"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_forced_change_get_returns_200(auth_client):
    response = auth_client.get(reverse("password-change-forced"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_forced_change_page_includes_password_toggle_script(auth_client):
    response = auth_client.get(reverse("password-change-forced"))
    assert "js/password_toggle.js" in response.content.decode()


@pytest.mark.django_db
def test_forced_change_valid_post_clears_flag_and_redirects(account, person):
    account.must_change_password = True
    account.save()
    c = Client()
    c.login(username=account.email, password="testpass123!")
    response = c.post(
        reverse("password-change-forced"),
        {"new_password": STRONG_PASSWORD, "new_password_confirm": STRONG_PASSWORD},
    )
    assert response.status_code == 302
    assert reverse("my-profile") in response["Location"]
    account.refresh_from_db()
    assert account.must_change_password is False


@pytest.mark.django_db
def test_forced_change_keeps_user_logged_in(account, person):
    account.must_change_password = True
    account.save()
    c = Client()
    c.login(username=account.email, password="testpass123!")
    c.post(
        reverse("password-change-forced"),
        {"new_password": STRONG_PASSWORD, "new_password_confirm": STRONG_PASSWORD},
    )
    # User can still access protected views without re-logging in
    response = c.get(reverse("my-profile"))
    assert response.status_code == 302
    assert LOGIN_URL not in response.get("Location", "")


@pytest.mark.django_db
def test_forced_change_weak_password_returns_error(auth_client):
    response = auth_client.post(
        reverse("password-change-forced"),
        {"new_password": "short", "new_password_confirm": "short"},
    )
    assert response.status_code == 200
    assert response.context["form"].errors


@pytest.mark.django_db
def test_forced_change_mismatched_passwords_returns_error(auth_client):
    response = auth_client.post(
        reverse("password-change-forced"),
        {"new_password": STRONG_PASSWORD, "new_password_confirm": STRONG_PASSWORD + "X"},
    )
    assert response.status_code == 200
    assert response.context["form"].errors


# ---------------------------------------------------------------------------
# AccountPasswordResetConfirmView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_reset_confirm_valid_link_sets_password_and_logs_in(account, person):
    url = _reset_confirm_url(account)
    c = Client()
    get_response = c.get(url)
    assert get_response.status_code == 302
    set_password_response = c.post(
        get_response["Location"],
        {"new_password1": STRONG_PASSWORD, "new_password2": STRONG_PASSWORD},
    )
    assert set_password_response.status_code == 302
    assert set_password_response["Location"] == reverse("my-profile")

    account.refresh_from_db()
    assert account.check_password(STRONG_PASSWORD)

    # post_reset_login=True: no further login needed
    protected_response = c.get(reverse("directory"))
    assert protected_response.status_code == 200


@pytest.mark.django_db
def test_reset_confirm_clears_must_change_password_flag(account, person):
    account.must_change_password = True
    account.save()
    url = _reset_confirm_url(account)
    c = Client()
    get_response = c.get(url)
    c.post(
        get_response["Location"],
        {"new_password1": STRONG_PASSWORD, "new_password2": STRONG_PASSWORD},
    )
    account.refresh_from_db()
    assert account.must_change_password is False


@pytest.mark.django_db
def test_reset_confirm_page_includes_password_toggle_script(account, person):
    url = _reset_confirm_url(account)
    c = Client()
    get_response = c.get(url)
    assert get_response.status_code == 302
    response = c.get(get_response["Location"])
    assert "js/password_toggle.js" in response.content.decode()


@pytest.mark.django_db
def test_reset_confirm_invalid_token_shows_expired_message(account):
    bad_url = reverse("password_reset_confirm", kwargs={"uidb64": "invalid", "token": "invalid-token"})
    c = Client()
    response = c.get(bad_url)
    assert response.status_code == 200
    assert not response.context["validlink"]


@pytest.mark.django_db
def test_reset_confirm_url_is_exempt_from_forced_password_change_redirect(account, person):
    # A user who is already logged in and flagged must_change_password (e.g. an
    # admin-reset account) must still be able to follow their own reset link
    # rather than being bounced to /password/change/ by the forced-change
    # middleware.
    account.must_change_password = True
    account.save()
    c = Client()
    c.login(username=account.email, password="testpass123!")
    account.refresh_from_db()
    url = _reset_confirm_url(account)
    response = c.get(url)
    assert response.status_code in (200, 302)
    assert CHANGE_URL not in response.get("Location", "")


# ---------------------------------------------------------------------------
# AccountPasswordResetView / AccountPasswordResetDoneView (self-service)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_password_reset_get_returns_200(client):
    response = client.get(reverse("password-reset"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_password_reset_post_valid_email_sends_link_and_redirects(client, account):
    response = client.post(reverse("password-reset"), {"email": account.email})
    assert response.status_code == 302
    assert response["Location"] == reverse("password-reset-done")
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [account.email]


@pytest.mark.django_db
def test_password_reset_post_unknown_email_still_redirects_no_email_sent(client, db):
    response = client.post(reverse("password-reset"), {"email": "nobody@example.com"})
    assert response.status_code == 302
    assert response["Location"] == reverse("password-reset-done")
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_password_reset_done_get_returns_200(client):
    response = client.get(reverse("password-reset-done"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_password_reset_full_round_trip_lets_user_log_in_with_new_password(client, account, person):
    client.post(reverse("password-reset"), {"email": account.email})
    assert len(mail.outbox) == 1
    body = mail.outbox[0].body

    match = re.search(r"https?://[^\s]+(/annuaire/password/reset/\S+/)", body)
    assert match is not None, f"reset link not found in email body:\n{body}"
    confirm_path = match.group(1)

    c = Client()
    get_response = c.get(confirm_path)
    assert get_response.status_code == 302
    set_password_response = c.post(
        get_response["Location"],
        {"new_password1": STRONG_PASSWORD, "new_password2": STRONG_PASSWORD},
    )
    assert set_password_response.status_code == 302

    fresh_client = Client()
    login_response = fresh_client.post(reverse("login"), {"username": account.email, "password": STRONG_PASSWORD})
    assert login_response.status_code == 302
    assert login_response["Location"] == reverse("home")
