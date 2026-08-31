from django import forms

from .models import Category, ancestor_has_groups, descendant_has_groups


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
