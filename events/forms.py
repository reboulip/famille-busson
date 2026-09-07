from django import forms

from annuaire.forms import ADDRESS_HELP_TEXT, AddressAutocompleteInput
from annuaire.widgets import MarkdownEditorWidget

from .models import Event


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "title",
            "description",
            "start",
            "end",
            "all_day",
            "location",
            "latitude",
            "longitude",
            "organisers",
            "groups",
        ]
        widgets = {
            "description": MarkdownEditorWidget,
            "start": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "end": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "location": AddressAutocompleteInput,
            "latitude": forms.HiddenInput,
            "longitude": forms.HiddenInput,
            "organisers": forms.MultipleHiddenInput,
        }
        help_texts = {
            "location": ADDRESS_HELP_TEXT,
        }

    def __init__(self, *args, current_person=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organisers"].required = False
        self.fields["groups"].required = False
        if current_person is not None and not self.is_bound and not self.initial.get("organisers"):
            self.fields["organisers"].initial = [current_person.pk]
