from django import forms

from .models import Attachment, BlogPost, Comment


class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ['title', 'post_type', 'body', 'authors']

    def __init__(self, *args, current_person=None, **kwargs):
        super().__init__(*args, **kwargs)
        if current_person is not None and not self.is_bound and not self.initial.get('authors'):
            self.fields['authors'].initial = [current_person.pk]


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Votre commentaire…'}),
        }
        labels = {'body': ''}


AttachmentFormSet = forms.inlineformset_factory(
    BlogPost,
    Attachment,
    fields=['file', 'caption'],
    extra=0,
    can_delete=True,
)
