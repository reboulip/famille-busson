import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_base_renders_offcanvas_toggle_for_authenticated_user(auth_client):
    response = auth_client.get(reverse("directory"))
    assert response.status_code == 200
    content = response.content.decode()
    assert 'data-bs-toggle="offcanvas"' in content
    assert 'id="sidebarNav"' in content


@pytest.mark.django_db
def test_base_renders_nav_for_anonymous_user(client):
    response = client.get(reverse("login"))
    assert response.status_code == 200
    content = response.content.decode()
    assert 'data-bs-toggle="offcanvas"' in content
    assert reverse("login") in content or "Se connecter" in content


@pytest.mark.django_db
def test_base_includes_favicon_link(client):
    response = client.get(reverse("login"))
    assert 'rel="icon"' in response.content.decode()


@pytest.mark.django_db
def test_base_vendors_bootstrap_bundle_js(client):
    response = client.get(reverse("login"))
    assert "js/bootstrap.bundle.min.js" in response.content.decode()


@pytest.mark.django_db
def test_base_includes_genealogie_nav_link(auth_client):
    response = auth_client.get(reverse("directory"))
    assert response.status_code == 200
    assert reverse("genealogie") in response.content.decode()
