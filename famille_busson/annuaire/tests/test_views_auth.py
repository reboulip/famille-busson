import pytest
from django.urls import reverse
from annuaire.models import Account, Person


# ---------------------------------------------------------------------------
# home
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_home_accessible_unauthenticated(client):
    response = client.get(reverse("home"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_home_uses_correct_template(client):
    response = client.get(reverse("home"))
    assert "annuaire/home.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_home_context_has_recent_persons(client, person):
    response = client.get(reverse("home"))
    assert "recent_persons" in response.context
    assert person in response.context["recent_persons"]


# ---------------------------------------------------------------------------
# CustomLoginView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_login_get_returns_200(client):
    response = client.get(reverse("login"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_post_valid_redirects_to_home(client, person):
    response = client.post(reverse("login"), {"username": "alice@example.com", "password": "testpass123!"})
    assert response.status_code == 302
    assert response["Location"] == reverse("home")


@pytest.mark.django_db
def test_login_post_invalid_credentials_returns_200(client, account):
    response = client.post(reverse("login"), {"username": "alice@example.com", "password": "wrongpassword"})
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_post_account_without_profile_shows_error(client, account):
    # Account exists but has no linked Person — login should fail with error message
    response = client.post(
        reverse("login"),
        {"username": "alice@example.com", "password": "testpass123!"},
        follow=True,
    )
    assert response.status_code == 200
    messages = list(response.context["messages"])
    assert any("profil" in str(m).lower() for m in messages)


@pytest.mark.django_db
def test_already_authenticated_user_redirected(auth_client):
    response = auth_client.get(reverse("login"))
    assert response.status_code == 302


# ---------------------------------------------------------------------------
# SignupView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_signup_get_returns_200(client):
    response = client.get(reverse("signup"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_signup_unknown_email_shows_error(client, db):
    # Email not in Person table — cannot create account
    response = client.post(
        reverse("signup"),
        {"email": "unknown@example.com", "password": "StrongP@ss1!", "password_confirm": "StrongP@ss1!"},
        follow=True,
    )
    assert response.status_code == 200
    messages = list(response.context["messages"])
    assert any("email" in str(m).lower() or "reconnue" in str(m).lower() for m in messages)


@pytest.mark.django_db
def test_signup_existing_account_shows_form_error(client, account, person):
    # Person exists and already has an Account — clean_email raises ValidationError → 200 with form error
    response = client.post(
        reverse("signup"),
        {"email": "alice@example.com", "password": "StrongP@ss1!", "password_confirm": "StrongP@ss1!"},
    )
    assert response.status_code == 200
    assert response.context["form"].errors


@pytest.mark.django_db
def test_signup_valid_creates_account_and_logs_in(client, db):
    Person.objects.create(first_name="Carol", last_name="Busson", email="carol@example.com")
    response = client.post(
        reverse("signup"),
        {"email": "carol@example.com", "password": "StrongP@ss1!", "password_confirm": "StrongP@ss1!"},
    )
    assert Account.objects.filter(email="carol@example.com").exists()
    assert response.status_code == 302
