import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from documents.forms import DocumentFileFormSet, category_tree_choices
from documents.models import Category


def _management_data(prefix="files", total=0, initial=0):
    return {
        f"{prefix}-TOTAL_FORMS": str(total),
        f"{prefix}-INITIAL_FORMS": str(initial),
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }


@pytest.mark.django_db
def test_document_file_formset_requires_at_least_one_file(document):
    data = _management_data(total=0)
    formset = DocumentFileFormSet(data, {}, instance=document)
    assert not formset.is_valid()
    assert "Un document doit contenir au moins un fichier." in formset.non_form_errors()


@pytest.mark.django_db
def test_document_file_formset_valid_with_one_file(document):
    uploaded = SimpleUploadedFile("scan.pdf", b"%PDF-fake", content_type="application/pdf")
    data = _management_data(total=1)
    data["files-0-caption"] = ""
    formset = DocumentFileFormSet(data, {"files-0-file": uploaded}, instance=document)
    assert formset.is_valid()


@pytest.mark.django_db
def test_document_file_formset_rejects_a_row_with_only_a_caption(document):
    # A caption with no file is invalid too, but via the row's own required-field
    # error rather than the formset-level message -- that field error already says
    # exactly what's wrong, so clean() skips piling on the generic one.
    data = _management_data(total=1)
    data["files-0-caption"] = "Une légende sans fichier"
    formset = DocumentFileFormSet(data, {}, instance=document)
    assert not formset.is_valid()
    assert formset.forms[0].errors.get("file")


@pytest.mark.django_db
def test_document_file_formset_deleting_the_only_file_is_invalid(document, document_file):
    data = _management_data(total=1, initial=1)
    data["files-0-id"] = str(document_file.pk)
    data["files-0-caption"] = document_file.caption
    data["files-0-DELETE"] = "on"
    formset = DocumentFileFormSet(data, {}, instance=document)
    assert not formset.is_valid()
    assert "Un document doit contenir au moins un fichier." in formset.non_form_errors()


@pytest.mark.django_db
def test_document_file_formset_deleting_one_of_two_files_is_valid(document, document_file):
    second = document.files.create(file=SimpleUploadedFile("second.pdf", b"%PDF-fake"))
    data = _management_data(total=2, initial=2)
    data["files-0-id"] = str(document_file.pk)
    data["files-0-caption"] = document_file.caption
    data["files-0-DELETE"] = "on"
    data["files-1-id"] = str(second.pk)
    data["files-1-caption"] = ""
    formset = DocumentFileFormSet(data, {}, instance=document)
    assert formset.is_valid()


# ---------------------------------------------------------------------------
# category_tree_choices
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_category_tree_choices_indents_children_under_parent(db):
    parent = Category.objects.create(name="Parent")
    child = Category.objects.create(name="Enfant", parent=parent)
    choices = category_tree_choices(Category.objects.all())
    labels = dict(choices)
    assert labels[parent.pk] == "Parent"
    assert labels[child.pk] == " " * 4 + "Enfant"


@pytest.mark.django_db
def test_category_tree_choices_prepends_empty_label(db):
    Category.objects.create(name="Seule")
    choices = category_tree_choices(Category.objects.all(), empty_label="---------")
    assert choices[0] == ("", "---------")


@pytest.mark.django_db
def test_category_tree_choices_omits_empty_label_when_none(db):
    Category.objects.create(name="Seule")
    choices = category_tree_choices(Category.objects.all(), empty_label=None)
    assert choices[0][0] != ""


@pytest.mark.django_db
def test_category_tree_choices_siblings_sorted_by_name(db):
    parent = Category.objects.create(name="Parent")
    Category.objects.create(name="Zoé", parent=parent)
    Category.objects.create(name="Alice", parent=parent)
    choices = category_tree_choices(Category.objects.all())
    names = [label.strip() for _, label in choices]
    assert names.index("Alice") < names.index("Zoé")


@pytest.mark.django_db
def test_category_tree_choices_grandchild_double_indented(db):
    grandparent = Category.objects.create(name="Aïeul")
    parent = Category.objects.create(name="Parent", parent=grandparent)
    grandchild = Category.objects.create(name="Petit-enfant", parent=parent)
    choices = category_tree_choices(Category.objects.all())
    labels = dict(choices)
    assert labels[grandchild.pk] == "        Petit-enfant"


@pytest.mark.django_db
def test_category_tree_choices_treats_hidden_parent_as_root(db):
    """If the parent isn't in the given queryset (e.g. access-scoped away), the
    child renders as a root rather than being dropped or erroring."""
    visible_parent = Category.objects.create(name="Visible")
    hidden_parent = Category.objects.create(name="Caché")
    orphan = Category.objects.create(name="Orphelin", parent=hidden_parent)
    choices = category_tree_choices(Category.objects.filter(pk__in=[visible_parent.pk, orphan.pk]))
    labels = dict(choices)
    assert labels[orphan.pk] == "Orphelin"
