from django import forms

from .access import accessible_categories
from .models import Category, Document, DocumentFile, ancestor_has_groups, descendant_has_groups
from .widgets import DocumentFileInput


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description", "parent", "groups"]

    def clean(self):
        cleaned_data = super().clean()
        groups = cleaned_data.get("groups")
        if not groups:
            return cleaned_data
        parent = cleaned_data.get("parent")
        node = parent
        while node is not None:
            if node.groups.exists():
                raise forms.ValidationError(
                    "Impossible de restreindre cette catégorie : une catégorie parente restreint "
                    "déjà l'accès, et cette restriction s'applique à toute sa descendance."
                )
            node = node.parent
        if self.instance.pk is not None and (
            ancestor_has_groups(self.instance) or descendant_has_groups(self.instance)
        ):
            raise forms.ValidationError(
                "Impossible de restreindre cette catégorie : une catégorie parente ou une "
                "sous-catégorie restreint déjà l'accès."
            )
        return cleaned_data


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["title", "category", "document_date", "description"]
        widgets = {
            "document_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None and not (user.is_staff or user.is_superuser):
            self.fields["category"].queryset = accessible_categories(user)


class BaseDocumentFileFormSet(forms.BaseInlineFormSet):
    """Requires at least one non-deleted file, on both create and edit. Enforced here
    (formset level) rather than as a Document.clean()/DB constraint because
    DocumentCreateView.form_valid() saves the Document before the formset, making a
    model-level "has files" constraint structurally impossible to satisfy at save
    time -- and because the formset is the only place that knows about pending
    deletions on edit."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        has_file = any(
            form.cleaned_data.get("file") and not form.cleaned_data.get("DELETE", False)
            for form in self.forms
            if form.cleaned_data
        )
        if not has_file:
            raise forms.ValidationError("Un document doit contenir au moins un fichier.")


DocumentFileFormSet = forms.inlineformset_factory(
    Document,
    DocumentFile,
    fields=["file", "caption"],
    formset=BaseDocumentFileFormSet,
    extra=0,
    can_delete=True,
    widgets={"file": DocumentFileInput},
)
