import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from annuaire.forms import BRANDING_IMAGE_MAX_SIZE_MB, FormSiteConfig
from annuaire.models import SiteConfig


def _png_bytes(size: int = 64) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (4, 4), (217, 121, 63)).save(buf, format="PNG")
    data = buf.getvalue()
    return data + b"\0" * max(0, size - len(data))


def _valid_form_data(**overrides):
    data = {
        "site_name": "Ma Famille",
        "wordmark": "",
        "tagline": "",
        "sender_address": "",
        "feedback_url": "",
        "timezone": "Europe/Paris",
        "default_language": "",
        "theme": "alpenglow",
        "brand_primary_light": "",
        "brand_primary_dark": "",
        "brand_accent_light": "",
        "brand_accent_dark": "",
    }
    data.update(overrides)
    return data


# --- Colour validation -------------------------------------------------------


@pytest.mark.django_db
def test_blank_colours_are_accepted():
    form = FormSiteConfig(data=_valid_form_data())
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_theme_default_colour_is_accepted_even_if_submitted_explicitly():
    form = FormSiteConfig(data=_valid_form_data(brand_accent_light="#D9793F"))
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_primary_colour_failing_aa_text_is_rejected():
    # A pale colour close to the card surface fails 4.5:1 easily.
    form = FormSiteConfig(data=_valid_form_data(brand_primary_light="#FFEECC"))
    assert not form.is_valid()
    assert "brand_primary_light" in form.errors
    assert "Contraste" in form.errors["brand_primary_light"][0]


@pytest.mark.django_db
def test_primary_colour_clearing_aa_text_is_accepted():
    # Near-black clears 4.5:1 against both card and parchment easily.
    form = FormSiteConfig(data=_valid_form_data(brand_primary_light="#101010"))
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_invalid_hex_format_is_rejected():
    form = FormSiteConfig(data=_valid_form_data(brand_primary_light="not-a-color"))
    assert not form.is_valid()
    assert "brand_primary_light" in form.errors


@pytest.mark.django_db
def test_valid_hex_is_normalised_to_uppercase():
    form = FormSiteConfig(data=_valid_form_data(brand_primary_light="#101010"))
    assert form.is_valid(), form.errors
    assert form.cleaned_data["brand_primary_light"] == "#101010"


# --- Logo/favicon size validation --------------------------------------------


@pytest.mark.django_db
def test_oversized_logo_is_rejected():
    oversized = SimpleUploadedFile(
        "logo.png", _png_bytes(BRANDING_IMAGE_MAX_SIZE_MB * 1024 * 1024 + 1), content_type="image/png"
    )
    form = FormSiteConfig(data=_valid_form_data(), files={"logo": oversized})
    assert not form.is_valid()
    assert "logo" in form.errors


@pytest.mark.django_db
def test_small_logo_is_accepted():
    small = SimpleUploadedFile("logo.png", _png_bytes(), content_type="image/png")
    form = FormSiteConfig(data=_valid_form_data(), files={"logo": small})
    assert form.is_valid(), form.errors


# --- branding_asset view -----------------------------------------------------


@pytest.mark.django_db
def test_branding_asset_404s_when_logo_unset(client):
    response = client.get(reverse("branding-asset", kwargs={"kind": "logo"}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_branding_asset_404s_for_unknown_kind(client):
    response = client.get(reverse("branding-asset", kwargs={"kind": "banner"}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_branding_asset_serves_logo_to_anonymous_visitor(client):
    SiteConfig.objects.create(logo=SimpleUploadedFile("logo.png", _png_bytes(), content_type="image/png"))
    response = client.get(reverse("branding-asset", kwargs={"kind": "logo"}))
    assert response.status_code == 200
    assert b"".join(response.streaming_content)


@pytest.mark.django_db
def test_branding_asset_serves_favicon_to_anonymous_visitor(client):
    SiteConfig.objects.create(favicon=SimpleUploadedFile("f.png", _png_bytes(), content_type="image/png"))
    response = client.get(reverse("branding-asset", kwargs={"kind": "favicon"}))
    assert response.status_code == 200
