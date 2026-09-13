"""UserLanguageMiddleware -- activates resolve_language()'s precedence for the
duration of a request, overriding LocaleMiddleware's own guess (Phase 15.5)."""


def test_a_page_renders_in_english_for_the_django_language_cookie(db, client):
    client.cookies["django_language"] = "en"
    response = client.get("/annuaire/login/")
    assert response.status_code == 200
    assert "Log in" in response.content.decode()
    assert "Se connecter" not in response.content.decode()


def test_a_page_renders_in_the_authenticated_accounts_saved_language(auth_client, account, person):
    account.language = "en"
    account.save(update_fields=["language"])
    response = auth_client.get(f"/annuaire/personne/{person.pk}/")
    assert response.status_code == 200
    assert "Edit profile" in response.content.decode()
    assert "Modifier le profil" not in response.content.decode()


def test_defaults_to_french_with_no_preference_anywhere(db, client):
    response = client.get("/annuaire/login/")
    assert response.status_code == 200
    assert "Se connecter" in response.content.decode()
