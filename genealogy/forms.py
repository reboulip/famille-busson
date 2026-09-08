from django import forms

from annuaire.widgets import MarkdownEditorWidget

from .models import Story


class FormStory(forms.ModelForm):
    class Meta:
        model = Story
        fields = ["title", "body", "date", "end_date"]
        widgets = {
            "body": MarkdownEditorWidget,
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }
