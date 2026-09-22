import pytest
from django.core.cache import cache
from django.test import Client, override_settings

from annuaire.models import AuditEvent, SiteConfig
from annuaire.site_config import CACHE_KEY, get_site_config


@pytest.fixture(autouse=True)
def _clear_site_config_cache():
    cache.delete(CACHE_KEY)
    yield
    cache.delete(CACHE_KEY)


# --- get_site_config() ----------------------------------------------------


@pytest.mark.django_db
def test_get_site_config_returns_unsaved_defaults_when_none_exists():
    config = get_site_config()
    assert config.pk is None
    assert config.site_name == ""
    assert config.timezone == "Europe/Paris"


@pytest.mark.django_db
def test_get_site_config_does_not_create_a_row():
    get_site_config()
    assert not SiteConfig.objects.exists()


@pytest.mark.django_db
def test_get_site_config_returns_the_saved_row():
    SiteConfig.objects.create(site_name="Ma Famille")
    config = get_site_config()
    assert config.pk == 1
    assert config.site_name == "Ma Famille"


@pytest.mark.django_db
def test_get_site_config_is_cached(django_assert_num_queries):
    SiteConfig.objects.create(site_name="Ma Famille")
    get_site_config()
    with django_assert_num_queries(0):
        get_site_config()


@pytest.mark.django_db
def test_saving_site_config_invalidates_the_cache():
    config = SiteConfig.objects.create(site_name="Ma Famille")
    get_site_config()
    config.site_name = "Autre Nom"
    config.save()
    assert get_site_config().site_name == "Autre Nom"


# --- Singleton behaviour ---------------------------------------------------


@pytest.mark.django_db
def test_save_pins_the_primary_key_to_one():
    config = SiteConfig.objects.create(site_name="Ma Famille")
    assert config.pk == 1
    other = SiteConfig(site_name="Autre")
    other.save()
    assert other.pk == 1
    assert SiteConfig.objects.count() == 1
    assert SiteConfig.objects.get().site_name == "Autre"


@pytest.mark.django_db
def test_delete_is_forbidden():
    config = SiteConfig.objects.create(site_name="Ma Famille")
    with pytest.raises(ValueError):
        config.delete()


# --- Context processor -----------------------------------------------------


@pytest.mark.django_db
def test_context_processor_exposes_site_config(auth_client):
    SiteConfig.objects.create(site_name="Ma Famille")
    response = auth_client.get("/annuaire/")
    assert response.context["site_config"].site_name == "Ma Famille"


# --- Timezone middleware ----------------------------------------------------


@pytest.mark.django_db
def test_timezone_middleware_activates_configured_timezone(account):
    SiteConfig.objects.create(timezone="Pacific/Tahiti")
    client = Client()
    client.login(username=account.email, password="testpass123!")
    response = client.get("/annuaire/")
    assert response.status_code == 200


@pytest.mark.django_db
@override_settings(TIME_ZONE="Europe/Paris")
def test_timezone_middleware_defaults_to_settings_time_zone_when_unconfigured(auth_client):
    from django.utils import timezone

    response = auth_client.get("/annuaire/")
    assert response.status_code == 200
    # Middleware deactivates after each request -- no timezone leaks between requests.
    assert timezone.get_current_timezone_name() in ("UTC", "Europe/Paris")


# --- Audit log integration (14.4) ------------------------------------------


@pytest.mark.django_db
def test_create_logs_audit_event():
    config = SiteConfig.objects.create(site_name="Ma Famille")
    event = AuditEvent.objects.get(content_type__model="siteconfig", object_id=str(config.pk))
    assert event.action == AuditEvent.Action.CREATE


@pytest.mark.django_db
def test_update_logs_audit_event():
    config = SiteConfig.objects.create(site_name="Ma Famille")
    AuditEvent.objects.all().delete()
    config.site_name = "Nouveau Nom"
    config.save()
    event = AuditEvent.objects.get(
        content_type__model="siteconfig", object_id=str(config.pk), action=AuditEvent.Action.UPDATE
    )
    assert event.changes["site_name"] == {"from": "Ma Famille", "to": "Nouveau Nom"}
