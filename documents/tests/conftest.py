import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile

from annuaire.tests.conftest import (  # noqa: F401 -- re-exported as fixtures
    account,
    auth_client,
    client,
    other_account,
    other_person,
    person,
    staff_account,
    staff_client,
)
from documents.models import Category, Document, DocumentFile


@pytest.fixture(autouse=True)
def use_tmp_media(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    settings.DOCUMENTS_ROOT = tmp_path / "documents_data"


@pytest.fixture
def category(db):
    return Category.objects.create(name="Actes de famille")


@pytest.fixture
def document(db, category):
    return Document.objects.create(title="Acte de naissance", category=category)


@pytest.fixture
def document_file(db, document):
    uploaded = SimpleUploadedFile(name="doc.pdf", content=b"%PDF-fake", content_type="application/pdf")
    return DocumentFile.objects.create(document=document, file=uploaded)


@pytest.fixture
def group(db):
    return Group.objects.create(name="SCI grand chalet")


@pytest.fixture
def restricted_category(db, group):
    category = Category.objects.create(name="Documents SCI")
    category.groups.add(group)
    return category


@pytest.fixture
def document_post_data():
    """Builds a valid document-create/document-edit POST payload, including the
    formset management form and `files` non-deleted file uploads by default. Since
    2.3, a zero-file payload (files=0) is *invalid* -- callers testing that rejection
    path pass files=0 explicitly."""

    def _make(category, *, files=1, **overrides):
        data = {"title": "Titre", "category": category.pk, "document_date": "", "description": ""}
        data["files-TOTAL_FORMS"] = str(files)
        data["files-INITIAL_FORMS"] = "0"
        data["files-MIN_NUM_FORMS"] = "0"
        data["files-MAX_NUM_FORMS"] = "1000"
        for i in range(files):
            data[f"files-{i}-caption"] = ""
            data[f"files-{i}-file"] = SimpleUploadedFile(f"file{i}.pdf", b"%PDF-fake", content_type="application/pdf")
        data.update(overrides)
        return data

    return _make
