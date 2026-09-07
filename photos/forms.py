from django import forms

from annuaire.widgets import MarkdownEditorWidget

from .models import Album, Photo


class AlbumForm(forms.ModelForm):
    class Meta:
        model = Album
        fields = ["title", "description", "date_start", "date_end", "cover", "groups"]
        widgets = {
            "description": MarkdownEditorWidget,
            "date_start": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "date_end": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A cover can only be one of the album's own photos -- on create there
        # are none yet (photos are added afterwards), so hide the field rather
        # than offer an empty/misleading choice list.
        if self.instance.pk is not None:
            self.fields["cover"].queryset = self.instance.photos.all()
        else:
            self.fields["cover"].queryset = self.fields["cover"].queryset.none()
            self.fields["cover"].widget = forms.HiddenInput()


class PhotoUploadForm(forms.ModelForm):
    """One instantiation per uploaded file -- PhotoUploadView's per-file XHR
    endpoint validates and saves exactly one Photo per POST. `album` and
    `uploaded_by` aren't form fields: the view sets them (and they're excluded
    from ModelForm's instance validation as a result), same shape as
    DocumentCreateView setting `uploaded_by` before calling form.save()."""

    class Meta:
        model = Photo
        fields = ["file"]
