import pytest

from annuaire.models import SiteConfig
from annuaire.theming import brand_css_overrides


@pytest.mark.django_db
def test_unconfigured_site_emits_no_override_css():
    config = SiteConfig()
    assert brand_css_overrides(config) == ""


@pytest.mark.django_db
def test_value_matching_theme_default_emits_no_override():
    config = SiteConfig(brand_primary_light="#9C4A22")
    assert brand_css_overrides(config) == ""


@pytest.mark.django_db
def test_custom_light_primary_emits_root_override():
    config = SiteConfig(brand_primary_light="#123456")
    css = brand_css_overrides(config)
    assert ":root{--fb-ember:#123456;}" in css
    assert "@media" not in css


@pytest.mark.django_db
def test_custom_dark_accent_emits_dark_overrides_only():
    config = SiteConfig(brand_accent_dark="#654321")
    css = brand_css_overrides(config)
    assert ":root{" not in css
    assert '@media (prefers-color-scheme: dark){:root:not([data-bs-theme="light"]){--fb-alpenglow:#654321;}}' in css
    assert '[data-bs-theme="dark"]{--fb-alpenglow:#654321;}' in css
