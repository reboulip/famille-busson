import pytest
from django.urls import reverse
from django.test import Client
from annuaire.models import Account, Person


LOGIN_URL = "/annuaire/login/"
CHANGE_URL = "/annuaire/password/change/"
STRONG_PASSWORD = "V3ryStr0ng!Pass"


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
