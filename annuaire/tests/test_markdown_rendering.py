import pytest
from django.template import Context, Template
from django.urls import reverse

from annuaire.markdown_utils import markdown_to_text, render_markdown

LOGIN_URL = "/annuaire/login/"


# ---------------------------------------------------------------------------
# render_markdown
# ---------------------------------------------------------------------------


def test_render_markdown_none_and_empty():
    assert render_markdown(None) == ""
    assert render_markdown("") == ""


def test_render_markdown_bold_and_italic():
    html = render_markdown("**gras** et *italique*")
    assert "<strong>gras</strong>" in html
    assert "<em>italique</em>" in html


def test_render_markdown_nl2br_preserves_single_newlines():
    html = render_markdown("Ligne 1\nLigne 2")
    assert "<br" in html


def test_render_markdown_link():
    html = render_markdown("[lien](https://example.com)")
    assert '<a href="https://example.com"' in html


def test_render_markdown_allows_images():
    html = render_markdown("![alt](https://example.com/photo.png)")
    assert "<img" in html
    assert 'src="https://example.com/photo.png"' in html


def test_render_markdown_fenced_code():
    html = render_markdown("```\ncode ici\n```")
    assert "<code>" in html


def test_render_markdown_tables():
    html = render_markdown("| A | B |\n|---|---|\n| 1 | 2 |")
    assert "<table>" in html


def test_render_markdown_strips_script_tags():
    html = render_markdown("<script>alert('xss')</script>texte")
    assert "<script" not in html
    assert "alert" not in html


def test_render_markdown_strips_event_handlers():
    html = render_markdown('<img src="x.png" onerror="alert(1)">')
    assert "onerror" not in html


def test_render_markdown_blocks_javascript_scheme():
    html = render_markdown("[clic](javascript:alert(1))")
    assert "javascript:" not in html


def test_render_markdown_allows_mailto_scheme():
    html = render_markdown("[mail](mailto:test@example.com)")
    assert 'href="mailto:test@example.com"' in html


def test_render_markdown_strips_style_and_iframe():
    html = render_markdown("<style>body{display:none}</style><iframe src='x'></iframe>texte")
    assert "<style" not in html
    assert "<iframe" not in html


# ---------------------------------------------------------------------------
# markdown_to_text
# ---------------------------------------------------------------------------


def test_markdown_to_text_none_and_empty():
    assert markdown_to_text(None) == ""
    assert markdown_to_text("") == ""


def test_markdown_to_text_strips_markup():
    text = markdown_to_text("**gras** et [lien](https://example.com)")
    assert "<" not in text
    assert "gras" in text
    assert "lien" in text


def test_markdown_to_text_collapses_whitespace():
    text = markdown_to_text("- item 1\n- item 2")
    assert "\n" not in text


# ---------------------------------------------------------------------------
# Template filters
# ---------------------------------------------------------------------------


def test_markdown_filter_renders_html():
    tpl = Template("{% load markdown_extras %}{{ text|markdown }}")
    rendered = tpl.render(Context({"text": "**gras**"}))
    assert "<strong>gras</strong>" in rendered


def test_markdown_plain_filter_strips_html():
    tpl = Template("{% load markdown_extras %}{{ text|markdown_plain }}")
    rendered = tpl.render(Context({"text": "**gras**"}))
    assert "<" not in rendered
    assert "gras" in rendered


# ---------------------------------------------------------------------------
# markdown_preview view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_markdown_preview_requires_login(client):
    response = client.post(reverse("markdown-preview"), {"text": "**gras**"})
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_markdown_preview_renders_sanitized_html(auth_client):
    response = auth_client.post(reverse("markdown-preview"), {"text": "**gras**"})
    assert response.status_code == 200
    assert response["Content-Type"] == "text/html; charset=utf-8"
    assert "<strong>gras</strong>" in response.content.decode()


@pytest.mark.django_db
def test_markdown_preview_rejects_get(auth_client):
    response = auth_client.get(reverse("markdown-preview"))
    assert response.status_code == 405


@pytest.mark.django_db
def test_markdown_preview_rejects_oversized_input(auth_client):
    response = auth_client.post(reverse("markdown-preview"), {"text": "a" * 100_001})
    assert response.status_code == 400


@pytest.mark.django_db
def test_markdown_preview_empty_input_returns_empty_body(auth_client):
    response = auth_client.post(reverse("markdown-preview"), {"text": ""})
    assert response.status_code == 200
    assert response.content == b""
