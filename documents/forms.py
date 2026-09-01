from django import forms

from annuaire.widgets import MarkdownEditorWidget

from .access import accessible_categories
from .models import Category, Document, DocumentFile, ancestor_has_groups, descendant_has_groups
from .widgets import DocumentFileInput


def category_tree_choices(queryset, empty_label=None):
    """Depth-first, name-ordered `(pk, indented_name)` choices for a Category
    `<select>`, each level indented by 4 non-breaking spaces. A category whose parent
    isn't in `queryset` is treated as a root -- defensive, since access-scoping can
    make an ancestor invisible while a descendant stays visible. Overriding a
    ModelChoiceField's `.choices` drops its automatic empty option, so callers that
    want one back must pass `empty_label` explicitly."""
    categories = list(queryset)
    visible_ids = {c.id for c in categories}
    children_by_parent = {}
    for category in categories:
        parent_id = category.parent_id if category.parent_id in visible_ids else None
        children_by_parent.setdefault(parent_id, []).append(category)
    for siblings in children_by_parent.values():
        siblings.sort(key=lambda c: c.name)

    choices = []
    if empty_label is not None:
        choices.append(("", empty_label))

    def _walk(parent_id, depth, visited):
        for category in children_by_parent.get(parent_id, []):
            if category.id in visited:
                continue
            visited.add(category.id)
            indent = " " * 4 * depth
            choices.append((category.pk, f"{indent}{category.name}"))
            _walk(category.id, depth + 1, visited)

    _walk(None, 0, set())
    return choices


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description", "parent", "groups"]
        widgets = {
            "description": MarkdownEditorWidget,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].choices = category_tree_choices(
            self.fields["parent"].queryset, self.fields["parent"].empty_label
        )

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
        fields = ["title", "category", "document_date", "redactor", "description"]
        widgets = {
            "document_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "redactor": forms.HiddenInput,
            "description": MarkdownEditorWidget,
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None and not (user.is_staff or user.is_superuser):
            self.fields["category"].queryset = accessible_categories(user)
        self.fields["category"].choices = category_tree_choices(
            self.fields["category"].queryset, self.fields["category"].empty_label
        )


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
