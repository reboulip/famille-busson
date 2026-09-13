from io import StringIO

import pytest
from django.contrib.auth.models import Group
from django.core.management import CommandError, call_command

from annuaire.management.commands.bootstrap_site import DEFAULT_GROUPS, STARTER_CATEGORIES
from annuaire.models import Account, Person, SiteConfig
from documents.models import Category

# ------------------------------------------------------------------ helpers


def run_bootstrap(**kwargs):
    out = StringIO()
    defaults = {
        "interactive": False,
        "site_name": "Ma Famille",
        "admin_first_name": "Ada",
        "admin_last_name": "Test",
        "admin_email": "admin@example.com",
        "admin_password": "a-very-strong-password-123",
    }
    call_command("bootstrap_site", stdout=out, **{**defaults, **kwargs})
    return out.getvalue()


# ------------------------------------------------------------------ tests


@pytest.mark.django_db
class TestBootstrapSiteNoInput:
    def test_creates_superuser(self):
        run_bootstrap()
        admin = Account.objects.get(email="admin@example.com")
        assert admin.is_superuser
        assert admin.must_change_password is False

    def test_creates_and_links_person_profile(self):
        run_bootstrap()
        admin = Account.objects.get(email="admin@example.com")
        assert admin.profile.first_name == "Ada"
        assert admin.profile.last_name == "Test"

    def test_creates_default_groups(self):
        run_bootstrap()
        for name in DEFAULT_GROUPS:
            assert Group.objects.filter(name=name).exists()

    def test_creates_starter_categories(self):
        run_bootstrap()
        for name in STARTER_CATEGORIES:
            assert Category.objects.filter(name=name).exists()

    def test_creates_site_config(self):
        run_bootstrap()
        config = SiteConfig.objects.get()
        assert config.site_name == "Ma Famille"
        assert config.wordmark == "Ma Famille"

    def test_missing_required_argument_raises_command_error(self):
        out = StringIO()
        with pytest.raises(CommandError):
            call_command("bootstrap_site", stdout=out, interactive=False, site_name="Ma Famille")


@pytest.mark.django_db
class TestBootstrapSiteIdempotency:
    def test_running_twice_does_not_duplicate_admin(self):
        run_bootstrap()
        run_bootstrap()
        assert Account.objects.filter(email="admin@example.com").count() == 1
        assert Person.objects.filter(email="admin@example.com").count() == 1

    def test_running_twice_does_not_duplicate_groups_or_categories(self):
        run_bootstrap()
        run_bootstrap()
        assert Group.objects.filter(name__in=DEFAULT_GROUPS).count() == len(DEFAULT_GROUPS)
        assert Category.objects.filter(name__in=STARTER_CATEGORIES).count() == len(STARTER_CATEGORIES)

    def test_running_twice_does_not_overwrite_edited_site_config(self):
        run_bootstrap()
        config = SiteConfig.objects.get()
        config.site_name = "Renamed Since"
        config.save()

        run_bootstrap(site_name="Should Be Ignored")

        config.refresh_from_db()
        assert config.site_name == "Renamed Since"
        assert SiteConfig.objects.count() == 1

    def test_second_run_reports_admin_already_exists(self):
        run_bootstrap()
        output = run_bootstrap()
        assert "already exists" in output
