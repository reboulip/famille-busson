from django import forms

from annuaire.widgets import MarkdownEditorWidget
from documents.access import accessible_documents
from documents.models import Document
from photos.access import accessible_albums
from photos.models import Album

from .models import Attachment, BlogPost, Comment


class BlogPostForm(forms.ModelForm):
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
