import pytest
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
