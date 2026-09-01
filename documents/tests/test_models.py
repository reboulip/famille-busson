import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.db.models import ProtectedError

from documents.models import Category, CategoryGroupAccess, DocumentFile


@pytest.mark.django_db
def test_category_str():
    category = Category.objects.create(name="Actes")
    assert str(category) == "Actes"


@pytest.mark.django_db
def test_category_without_parent_is_valid():
    category = Category(name="Racine")
    category.full_clean()


@pytest.mark.django_db
def test_category_group_access_str(category):
    group = Group.objects.create(name="SCI")
    access = CategoryGroupAccess.objects.create(category=category, group=group)
    assert str(access) == f"{category} — {group}"


@pytest.mark.django_db
def test_category_cannot_be_own_parent():
    category = Category.objects.create(name="Actes")
    category.parent = category
    with pytest.raises(ValidationError):
        category.full_clean()


@pytest.mark.django_db
def test_category_cannot_create_cycle():
    a = Category.objects.create(name="A")
    Category.objects.create(name="B", parent=a)
    b = Category.objects.get(name="B")
    a.parent = b
    with pytest.raises(ValidationError):
        a.full_clean()


@pytest.mark.django_db
def test_category_depth_capped_at_five():
    node = None
    for i in range(6):
        node = Category.objects.create(name=f"Niveau {i}", parent=node)
    seventh = Category(name="Niveau 6", parent=node)
    with pytest.raises(ValidationError):
        seventh.full_clean()


@pytest.mark.django_db
def test_category_within_depth_limit_is_valid():
    node = None
    for i in range(4):
        node = Category.objects.create(name=f"Niveau {i}", parent=node)
    fifth = Category(name="Niveau 4", parent=node)
    fifth.full_clean()


@pytest.mark.django_db
def test_category_cannot_restrict_when_ancestor_restricted():
    parent = Category.objects.create(name="Parent")
    group = Group.objects.create(name="SCI")
    parent.groups.add(group)
    child = Category.objects.create(name="Enfant", parent=parent)
    other_group = Group.objects.create(name="Autre")
    with pytest.raises(ValidationError):
        child.groups.add(other_group)


@pytest.mark.django_db
def test_category_cannot_restrict_when_descendant_restricted():
    parent = Category.objects.create(name="Parent")
    child = Category.objects.create(name="Enfant", parent=parent)
    group = Group.objects.create(name="SCI")
    child.groups.add(group)
    other_group = Group.objects.create(name="Autre")
    with pytest.raises(ValidationError):
        parent.groups.add(other_group)


@pytest.mark.django_db
def test_category_can_restrict_when_ancestry_public():
    parent = Category.objects.create(name="Parent")
    child = Category.objects.create(name="Enfant", parent=parent)
    group = Group.objects.create(name="SCI")
    child.groups.add(group)
    assert list(child.groups.all()) == [group]


@pytest.mark.django_db
def test_category_deletion_protected_while_documents_exist(category, document):
    with pytest.raises(ProtectedError):
        category.delete()


@pytest.mark.django_db
def test_document_str(document):
    assert str(document) == document.title


@pytest.mark.django_db
def test_document_redactor_defaults_to_none(document):
    assert document.redactor is None


@pytest.mark.django_db
def test_document_redactor_set_leaves_uploaded_by_untouched(document, person, other_person):
    document.uploaded_by = person
    document.redactor = other_person
    document.save()
    document.refresh_from_db()
    assert document.uploaded_by == person
    assert document.redactor == other_person


@pytest.mark.django_db
def test_document_redactor_set_null_on_person_delete(document, person):
    document.redactor = person
    document.save()
    person.delete()
    document.refresh_from_db()
    assert document.redactor is None


@pytest.mark.django_db
def test_document_file_str_uses_caption(document):
    doc_file = DocumentFile.objects.create(
        document=document, caption="Scan recto", file=SimpleUploadedFile("scan.pdf", b"%PDF-fake")
    )
    assert str(doc_file) == "Scan recto"


@pytest.mark.django_db
def test_document_file_str_falls_back_to_filename(document):
    doc_file = DocumentFile.objects.create(
        document=document, file=SimpleUploadedFile("unnamed_scan.pdf", b"%PDF-fake")
    )
    assert str(doc_file) == "unnamed_scan.pdf"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "filename,expected",
    [
        ("photo.jpg", "image"),
        ("photo.PNG", "image"),
        ("scan.pdf", "pdf"),
        ("notes.txt", "other"),
    ],
)
def test_document_file_preview_kind(document, filename, expected):
    doc_file = DocumentFile.objects.create(document=document, file=SimpleUploadedFile(filename, b"content"))
    assert doc_file.preview_kind == expected


@pytest.mark.django_db
def test_category_group_access_unique_constraint(category):
    group = Group.objects.create(name="SCI")
    CategoryGroupAccess.objects.create(category=category, group=group)
    with pytest.raises(IntegrityError):
        CategoryGroupAccess.objects.create(category=category, group=group)


@pytest.mark.django_db
def test_group_deletion_protected_while_category_restricts_it(category):
    group = Group.objects.create(name="SCI")
    category.groups.add(group)
    with pytest.raises(ProtectedError):
        group.delete()
