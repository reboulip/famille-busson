from django import forms


class MarkdownEditorWidget(forms.Textarea):
    template_name = "annuaire/widgets/markdown_editor.html"

    class Media:
        js = ["js/markdown_editor.js"]
