"""Regression guards for the photothèque lightbox (10.5), mirroring
documents/tests/test_document_viewer_layout.py's source-text-assertion approach --
there's no JS test runner in this project."""

import re
from pathlib import Path

import pytest
from django.urls import reverse

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MAIN_CSS = REPO_ROOT / "annuaire" / "static" / "css" / "main.css"
DOCUMENT_VIEWER_JS = REPO_ROOT / "documents" / "static" / "js" / "document_viewer.js"


def _strip_comments(css_text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)


def _rule_body(css_text: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", _strip_comments(css_text))
    assert match, f"No {selector!r} rule found in {MAIN_CSS}"
    return match.group(1)


def _declared_value(body: str, prop: str) -> str | None:
    match = re.search(rf"{prop}\s*:\s*([^;]+);", body)
    return match.group(1).strip() if match else None


def test_gallery_grid_is_a_grid_when_not_fullscreen():
    body = _rule_body(
        MAIN_CSS.read_text(encoding="utf-8"),
        ".document-viewer--gallery:not(.document-viewer--fullscreen) .document-viewer-stage.document-viewer-strip",
    )
    assert _declared_value(body, "display") == "grid"


def test_document_viewer_js_swaps_to_full_resolution_on_fullscreen_entry():
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert "data-full-src" in content
    assert "swapToFullResolution" in content


def test_document_viewer_js_never_references_field_file_url():
    # Still true after the gallery/resolution-swap additions -- photo URLs always go
    # through the access-checked endpoints, never a raw .file.url.
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert ".file.url" not in content


def test_document_viewer_js_sets_aria_modal_on_fullscreen_entry():
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert "aria-modal" in content
    assert "role" in content


@pytest.mark.django_db
def test_photo_tile_carries_thumbnail_and_full_src(auth_client, photo):
    response = auth_client.get(reverse("album-detail", kwargs={"pk": photo.album_id}))
    content = response.content.decode()
    assert "data-full-src=" in content
    assert reverse("photo-file-thumbnail", kwargs={"pk": photo.pk}) in content
    assert reverse("photo-file-web", kwargs={"pk": photo.pk}) in content


@pytest.mark.django_db
def test_album_detail_loads_document_viewer_js(auth_client, album, photo):
    response = auth_client.get(reverse("album-detail", kwargs={"pk": album.pk}))
    assert "js/document_viewer.js" in response.content.decode()


@pytest.mark.django_db
def test_locked_album_does_not_load_document_viewer_js(auth_client, restricted_album):
    response = auth_client.get(reverse("album-detail", kwargs={"pk": restricted_album.pk}))
    assert "js/document_viewer.js" not in response.content.decode()
