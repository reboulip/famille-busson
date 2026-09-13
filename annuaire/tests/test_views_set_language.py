"""annuaire.views.set_language -- the POST-only language switcher (Phase 15.5).

Not django.conf.urls.i18n's stock `set_language` view: that one isn't
@login_not_required-compatible with this project's global LoginRequiredMiddleware.
"""

from django.conf import settings


def test_works_anonymously_and_sets_the_cookie(db, client):
    response = client.post("/annuaire/langue/", {"language": "en", "next": "/annuaire/login/"})
    assert response.status_code == 302
    assert response.url == "/annuaire/login/"
    assert response.cookies[settings.LANGUAGE_COOKIE_NAME].value == "en"


def test_saves_the_preference_on_an_authenticated_account(auth_client, account):
    response = auth_client.post("/annuaire/langue/", {"language": "en", "next": "/"})
    assert response.status_code == 302
    account.refresh_from_db()
    assert account.language == "en"


def test_anonymous_request_does_not_touch_any_account(db, client, account):
    client.post("/annuaire/langue/", {"language": "en", "next": "/"})
    account.refresh_from_db()
    assert account.language == ""


def test_rejects_an_unknown_language_code(db, client):
    response = client.post("/annuaire/langue/", {"language": "xx", "next": "/"})
    assert response.status_code == 400


def test_rejects_get(db, client):
    response = client.get("/annuaire/langue/")
    assert response.status_code == 405


def test_rejects_an_open_redirect_next(db, client):
    response = client.post("/annuaire/langue/", {"language": "en", "next": "https://evil.example.com/"})
    assert response.status_code == 302
    assert response.url == "/"


def test_missing_next_falls_back_to_root(db, client):
    response = client.post("/annuaire/langue/", {"language": "en"})
    assert response.status_code == 302
    assert response.url == "/"
