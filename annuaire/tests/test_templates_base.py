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
    # magic-link-help, not login: login is a *threshold* page and deliberately has no
    # sidebar (see test_threshold_pages_have_no_sidebar below). This is the public
    # page that still uses the full app shell.
    response = client.get(reverse("magic-link-help"))
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


@pytest.mark.django_db
def test_base_includes_documents_nav_link(auth_client):
    response = auth_client.get(reverse("directory"))
    assert reverse("document-list") in response.content.decode()


@pytest.mark.django_db
def test_base_includes_events_nav_link(auth_client):
    response = auth_client.get(reverse("directory"))
    assert reverse("event-list") in response.content.decode()


@pytest.mark.django_db
def test_base_includes_calendrier_nav_link(auth_client):
    response = auth_client.get(reverse("directory"))
    assert reverse("calendrier") in response.content.decode()


@pytest.mark.django_db
def test_base_includes_group_list_nav_link_for_staff(staff_client):
    response = staff_client.get(reverse("directory"))
    assert reverse("group-list") in response.content.decode()


@pytest.mark.django_db
def test_base_excludes_group_list_nav_link_for_non_staff(auth_client):
    response = auth_client.get(reverse("directory"))
    assert reverse("group-list") not in response.content.decode()


@pytest.mark.django_db
def test_base_includes_magic_link_help_nav_link(client):
    response = client.get(reverse("login"))
    assert reverse("magic-link-help") in response.content.decode()


@pytest.mark.django_db
def test_base_includes_home_nav_link(auth_client):
    response = auth_client.get(reverse("directory"))
    assert response.status_code == 200
    assert f'href="{reverse("home")}"' in response.content.decode()


@pytest.mark.django_db
def test_anonymous_sidebar_hides_the_login_required_sections(client):
    """The public help page still uses the app shell, but everything below Aide is
    login-required -- showing it to a logged-out visitor is a menu whose every link
    bounces back to the form they just came from."""
    content = client.get(reverse("magic-link-help")).content.decode()
    assert reverse("magic-link-help") in content
    assert "Se connecter" in content
    for hidden in (
        "directory",
        "genealogie",
        "carte",
        "chalet-list",
        "blogpost-list",
        "document-list",
        "activity-feed",
        "event-list",
        "calendrier",
    ):
        assert f'href="{reverse(hidden)}"' not in content, hidden


@pytest.mark.django_db
def test_authenticated_sidebar_shows_the_app_sections(auth_client):
    content = auth_client.get(reverse("directory")).content.decode()
    assert f'href="{reverse("home")}"' in content
    assert f'href="{reverse("carte")}"' in content


@pytest.mark.django_db
def test_base_includes_feedback_link(auth_client):
    response = auth_client.get(reverse("directory"))
    content = response.content.decode()
    assert "https://github.com/reboulip/famille-busson/issues/new" in content
    assert 'target="_blank"' in content
    assert 'rel="noopener"' in content
    assert "Signaler un bug ou proposer une évolution" in content


@pytest.mark.django_db
def test_base_includes_feedback_link_for_anonymous_user(client):
    response = client.get(reverse("login"))
    content = response.content.decode()
    assert "https://github.com/reboulip/famille-busson/issues/new" in content
    assert "Signaler un bug ou proposer une évolution" in content


# ---------------------------------------------------------------------------
# Archetype H — the threshold (Alpenglow design pass)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name",
    ["login", "signup", "magic-link-request", "magic-link-sent", "password-reset", "password-reset-done"],
)
def test_threshold_pages_have_no_sidebar(client, url_name):
    """Pages a visitor sees *before* they are in render base_threshold.html, which has
    no nav at all. Extending base.html here meant a logged-out visitor stared at a menu
    -- Annuaire, Généalogie, Carte, Chalets -- whose every link bounced back to login."""
    content = client.get(reverse(url_name)).content.decode()
    assert 'data-bs-toggle="offcanvas"' not in content
    assert 'class="fb-sidebar"' not in content


@pytest.mark.django_db
def test_threshold_pages_still_carry_the_brand_and_favicon(client):
    content = client.get(reverse("login")).content.decode()
    assert 'rel="icon"' in content
    assert "Famille Busson" in content
    assert "fb-wordmark" in content


@pytest.mark.django_db
def test_login_offers_the_magic_link_and_password_reset_routes(client):
    content = client.get(reverse("login")).content.decode()
    assert reverse("magic-link-request") in content
    assert reverse("password-reset") in content
    assert reverse("magic-link-help") in content


@pytest.mark.django_db
def test_credential_flows_use_the_restrained_horizon_not_the_full_ridge(client):
    """The emails split full vs. restrained treatment the same way: a credential email
    that looks understated reads as more trustworthy. The site mirrors it."""
    restrained = client.get(reverse("password-reset")).content.decode()
    assert "fb-horizon" in restrained
    assert "fb-ridge__pine" not in restrained

    full = client.get(reverse("login")).content.decode()
    assert "fb-ridge__pine" in full


@pytest.mark.django_db
def test_base_applies_the_stored_theme_before_the_stylesheets(auth_client):
    """The theme has to be set on <html> before the CSS paints, or the page flashes
    Alpenglow on its way to Nightfall."""
    content = auth_client.get(reverse("directory")).content.decode()
    theme_script = content.index("localStorage.getItem('fb-theme')")
    first_stylesheet = content.index('rel="stylesheet"')
    assert theme_script < first_stylesheet


@pytest.mark.django_db
def test_base_marks_the_current_nav_item(auth_client):
    """The sidebar had no active state at all before the design pass -- you could not
    tell which page you were on."""
    content = auth_client.get(reverse("directory")).content.decode()
    assert f'href="{reverse("directory")}" aria-current="page"' in content
    assert f'href="{reverse("carte")}" aria-current="page"' not in content


@pytest.mark.django_db
def test_stylesheets_load_tokens_and_components_after_bootstrap_and_main_last(auth_client):
    """tokens.css re-points Bootstrap's own --bs-* variables, so it must come after
    bootstrap.css; main.css has to win against the per-page vendor sheets, so it comes
    last. Getting this order wrong is silent -- the page just looks like stock Bootstrap."""
    content = auth_client.get(reverse("directory")).content.decode()
    order = [content.index(f"css/{name}.css") for name in ("bootstrap", "tokens", "components", "main")]
    assert order == sorted(order)


@pytest.mark.django_db
def test_sidebar_chalet_entry_names_presences_too(auth_client):
    # #127: the section covers the presence calendar as well as the chalets.
    content = auth_client.get(reverse("directory")).content.decode()
    assert "Chalets et Présences" in content
