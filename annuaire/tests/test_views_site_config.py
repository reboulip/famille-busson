import pytest
from django.urls import reverse

from annuaire.models import SiteConfig

LOGIN_URL = "/annuaire/login/"


@pytest.mark.django_db
def test_site_config_requires_login(client):
    response = client.get(reverse("site-config"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_site_config_requires_staff(auth_client):
    response = auth_client.get(reverse("site-config"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_site_config_get_returns_200_with_no_existing_row(staff_client):
    response = staff_client.get(reverse("site-config"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_site_config_get_returns_200_with_existing_row(staff_client):
    SiteConfig.objects.create(site_name="Ma Famille")
    response = staff_client.get(reverse("site-config"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_site_config_post_creates_the_row(staff_client):
    response = staff_client.post(
        reverse("site-config"),
        {
            "site_name": "Ma Famille",
            "wordmark": "Ma Famille",
            "tagline": "",
            "sender_address": "",
            "feedback_url": "",
            "timezone": "Europe/Paris",
            "default_language": "",
        },
    )
    assert response.status_code == 302
    assert SiteConfig.objects.get(pk=1).site_name == "Ma Famille"


@pytest.mark.django_db
def test_site_config_post_updates_the_existing_row(staff_client):
    SiteConfig.objects.create(site_name="Ancien Nom", timezone="Europe/Paris")
    response = staff_client.post(
        reverse("site-config"),
        {
            "site_name": "Nouveau Nom",
            "wordmark": "",
            "tagline": "",
            "sender_address": "",
            "feedback_url": "",
            "timezone": "Europe/Paris",
            "default_language": "",
        },
    )
    assert response.status_code == 302
    assert SiteConfig.objects.count() == 1
    assert SiteConfig.objects.get(pk=1).site_name == "Nouveau Nom"


@pytest.mark.django_db
def test_administration_nav_links_to_site_config(staff_client):
    response = staff_client.get(reverse("home"))
    content = response.content.decode()
    assert reverse("site-config") in content
