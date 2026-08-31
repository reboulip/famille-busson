from django import forms

from annuaire.widgets import MarkdownEditorWidget


class _DummyForm(forms.Form):
    body = forms.CharField(widget=MarkdownEditorWidget)


def test_widget_renders_textarea_and_tabs():
    form = _DummyForm()
    html = str(form["body"])
    assert "<textarea" in html
    assert "markdown-editor" in html
    assert "Écrire" in html
    assert "Aperçu" in html


def test_widget_preserves_attrs():
    widget = MarkdownEditorWidget(attrs={"rows": 3, "placeholder": "Votre commentaire…"})

    class DummyForm(forms.Form):
        body = forms.CharField(widget=widget)

    html = str(DummyForm()["body"])
    assert 'rows="3"' in html
    assert "Votre commentaire…" in html


def test_widget_media_includes_js():
    form = _DummyForm()
    media_html = str(form.media)
    assert "js/markdown_editor.js" in media_html


def test_widget_preview_pane_uses_markdown_body_class():
    form = _DummyForm()
    html = str(form["body"])
    assert "markdown-editor-preview markdown-body" in html
