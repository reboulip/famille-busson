from django import forms

from annuaire.widgets import MarkdownEditorWidget
from documents.access import accessible_documents
from documents.models import Document
from photos.access import accessible_albums
from photos.models import Album

from .models import Attachment, BlogPost, Comment, Tag


class BlogPostForm(forms.ModelForm):
    tags = forms.CharField(
        required=False,
        label="Étiquettes",
        help_text="Séparez les étiquettes par des virgules.",
        widget=forms.TextInput(attrs={"list": "tag-suggestions", "placeholder": "photos, réunion, annonce"}),
    )

    class Meta:
        model = BlogPost
        fields = ["title", "post_type", "body", "authors", "documents", "albums"]
        widgets = {
            "authors": forms.MultipleHiddenInput,
            "documents": forms.MultipleHiddenInput,
            "albums": forms.MultipleHiddenInput,
            "body": MarkdownEditorWidget,
        }

    def __init__(self, *args, current_person=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if current_person is not None and not self.is_bound and not self.initial.get("authors"):
            self.fields["authors"].initial = [current_person.pk]
        # Fail closed: a caller that forgets `user` gets an empty queryset, never
        # every document/album -- this is these fields' entire security boundary.
        self.fields["documents"].queryset = accessible_documents(user) if user is not None else Document.objects.none()
        self.fields["albums"].queryset = accessible_albums(user) if user is not None else Album.objects.none()
        if self.instance.pk and not self.is_bound:
            self.fields["tags"].initial = ", ".join(self.instance.tags.values_list("name", flat=True))

    def clean_tags(self):
        raw = self.cleaned_data.get("tags", "")
        # SQLite's LIKE is ASCII-case-insensitive only, so accented-case dedupe
        # ("Été"/"été") isn't guaranteed to match production identically -- .strip()
        # is the only normalization relied upon here.
        names = dict.fromkeys(name.strip() for name in raw.split(",") if name.strip())
        tags = []
        for name in names:
            tag, _ = Tag.objects.get_or_create(name__iexact=name, defaults={"name": name})
            tags.append(tag)
        return tags

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            instance.tags.set(self.cleaned_data["tags"])
        else:
            original_save_m2m = self.save_m2m

            def save_m2m():
                original_save_m2m()
                instance.tags.set(self.cleaned_data["tags"])

            self.save_m2m = save_m2m
        return instance


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["body"]
        widgets = {
            "body": MarkdownEditorWidget(attrs={"rows": 3, "placeholder": "Votre commentaire…"}),
        }
        labels = {"body": ""}


AttachmentFormSet = forms.inlineformset_factory(
    BlogPost,
    Attachment,
    fields=["file", "caption"],
    extra=0,
    can_delete=True,
)
