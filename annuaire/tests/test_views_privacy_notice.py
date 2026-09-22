import pytest
from django.urls import reverse

from annuaire.privacy_notice import PRIVACY_NOTICE_VERSION, has_accepted, record_acceptance

LOGIN_URL = "/annuaire/login/"


@pytest.mark.django_db
def test_privacy_notice_is_public(client):
    response = client.get(reverse("privacy-notice"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_privacy_notice_lists_personal_data_categories(client):
    response = client.get(reverse("privacy-notice"))
    content = response.content.decode()
    assert "Profil" in content
    assert "Consentements" in content


@pytest.mark.django_db
def test_privacy_notice_link_visible_to_anonymous_visitor(client):
    content = client.get(reverse("magic-link-help")).content.decode()
    assert reverse("privacy-notice") in content


@pytest.mark.django_db
def test_signup_without_consent_is_rejected(client, db):
    response = client.post(
        reverse("signup"),
        {"email": "unknown@example.com", "password": "StrongP@ss1!", "password_confirm": "StrongP@ss1!"},
    )
    assert response.status_code == 200
    assert response.context["form"].errors.get("accept_privacy_notice")


@pytest.mark.django_db
def test_signup_with_consent_records_acceptance(client, db):
    from annuaire.models import Account, Person

    Person.objects.create(first_name="Carol", last_name="Busson", email="carol@example.com")
    client.post(
        reverse("signup"),
        {
            "email": "carol@example.com",
            "password": "StrongP@ss1!",
            "password_confirm": "StrongP@ss1!",
            "accept_privacy_notice": "on",
        },
    )
    account = Account.objects.get(email="carol@example.com")
    assert has_accepted(account)


@pytest.mark.django_db
def test_accept_privacy_notice_requires_login(client):
    response = client.post(reverse("privacy-notice-accept"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_accept_privacy_notice_requires_post(auth_client):
    response = auth_client.get(reverse("privacy-notice-accept"))
    assert response.status_code == 405


@pytest.mark.django_db
def test_accept_privacy_notice_records_acceptance(auth_client, account):
    assert not has_accepted(account)
    response = auth_client.post(reverse("privacy-notice-accept"))
    assert response.status_code == 302
    account.refresh_from_db()
    assert has_accepted(account)
    assert account.privacy_notice_version == PRIVACY_NOTICE_VERSION


@pytest.mark.django_db
def test_banner_shown_when_not_accepted(auth_client):
    content = auth_client.get(reverse("directory")).content.decode()
    assert reverse("privacy-notice-accept") in content


@pytest.mark.django_db
def test_banner_hidden_after_accepting(auth_client, account):
    record_acceptance(account)
    content = auth_client.get(reverse("directory")).content.decode()
    assert reverse("privacy-notice-accept") not in content


@pytest.mark.django_db
def test_personal_data_export_includes_consent_once_accepted(auth_client, person, account):
    from annuaire.personal_data import collect_personal_data

    assert collect_personal_data(person, account)["consentements"] == []
    record_acceptance(account)
    (row,) = collect_personal_data(person, account)["consentements"]
    assert row["version"] == PRIVACY_NOTICE_VERSION
