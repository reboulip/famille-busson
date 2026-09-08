"""Phase 8.6 — a discreet version number in the site footer (#138)."""

import tomllib

import pytest
from django.urls import reverse

from famille_busson.settings import BASE_DIR, _read_app_version


def _pyproject_version() -> str:
    with open(BASE_DIR / "pyproject.toml", "rb") as f:
        return tomllib.load(f)["project"]["version"]


def test_read_app_version_matches_pyproject_toml():
    """Drift guard: catches both a broken read and a hand-edited second copy."""
    assert _read_app_version() == _pyproject_version()


def test_read_app_version_is_empty_when_the_file_is_missing(tmp_path, monkeypatch):
    import famille_busson.settings as settings_module

    monkeypatch.setattr(settings_module, "BASE_DIR", tmp_path)
    assert _read_app_version() == ""


def test_read_app_version_is_empty_on_malformed_toml(tmp_path, monkeypatch):
    import famille_busson.settings as settings_module

    (tmp_path / "pyproject.toml").write_text("not valid toml [[[")
    monkeypatch.setattr(settings_module, "BASE_DIR", tmp_path)
    assert _read_app_version() == ""


@pytest.mark.django_db
def test_footer_shows_the_version_for_authenticated_users(auth_client):
    response = auth_client.get(reverse("directory"))
    assert f"v{_pyproject_version()}" in response.content.decode()


@pytest.mark.django_db
def test_footer_shows_the_version_on_the_threshold_page(client):
    response = client.get(reverse("login"))
    assert f"v{_pyproject_version()}" in response.content.decode()


@pytest.mark.django_db
def test_footer_shows_the_version_for_anonymous_users_on_the_app_shell(client):
    response = client.get(reverse("magic-link-help"))
    assert f"v{_pyproject_version()}" in response.content.decode()


@pytest.mark.django_db
def test_footer_renders_nothing_when_the_version_is_empty(auth_client, settings):
    settings.APP_VERSION = ""
    response = auth_client.get(reverse("directory"))
    assert "fb-footer" not in response.content.decode()
