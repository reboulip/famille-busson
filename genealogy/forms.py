from django import forms

from annuaire.widgets import MarkdownEditorWidget

from .gedcom.importer import MAX_FILE_BYTES
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


class FormGedcomUpload(forms.Form):
    file = forms.FileField(label="Fichier GEDCOM (.ged)")

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        if uploaded.size > MAX_FILE_BYTES:
            raise forms.ValidationError(f"Fichier trop volumineux (max {MAX_FILE_BYTES // (1024 * 1024)} Mo).")
        return uploaded
