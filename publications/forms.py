from django import forms

from annuaire.widgets import MarkdownEditorWidget

from .models import Attachment, BlogPost, Comment


class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ["title", "post_type", "body", "authors"]
        widgets = {
            "authors": forms.MultipleHiddenInput,
            "body": MarkdownEditorWidget,
        }

    def __init__(self, *args, current_person=None, **kwargs):
        super().__init__(*args, **kwargs)
        if current_person is not None and not self.is_bound and not self.initial.get("authors"):
            self.fields["authors"].initial = [current_person.pk]


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
