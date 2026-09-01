from pathlib import Path

from django import forms

from annuaire.widgets import MarkdownEditorWidget

MARKDOWN_EDITOR_JS = Path(__file__).resolve().parent.parent / "static" / "js" / "markdown_editor.js"


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


def test_widget_renders_toolbar_with_eight_actions():
    form = _DummyForm()
    html = str(form["body"])
    assert "markdown-editor-toolbar" in html
    for action in ("heading", "bold", "italic", "quote", "code", "link", "ul", "ol"):
        assert f'data-md-action="{action}"' in html


def test_widget_toolbar_buttons_are_type_button():
    # The widget renders inside <form method="post"> forms elsewhere -- a bare
    # <button> defaults to type="submit" and would submit the form on every click.
    form = _DummyForm()
    html = str(form["body"])
    button_count = html.count("markdown-editor-toolbar-btn")
    assert button_count == 8
    assert html.count('type="button" class="markdown-editor-toolbar-btn"') == 8


def test_markdown_editor_js_uses_exec_command_not_direct_value_assignment():
    content = MARKDOWN_EDITOR_JS.read_text(encoding="utf-8")
    assert "execCommand('insertText'" in content
    assert "textarea.value =" not in content


def test_markdown_editor_js_dispatches_input_event_after_toolbar_action():
    content = MARKDOWN_EDITOR_JS.read_text(encoding="utf-8")
    assert "dispatchEvent(new Event('input'" in content


def test_markdown_editor_js_hides_toolbar_in_preview_mode():
    content = MARKDOWN_EDITOR_JS.read_text(encoding="utf-8")
    assert "toolbar.hidden = name !== 'write'" in content
