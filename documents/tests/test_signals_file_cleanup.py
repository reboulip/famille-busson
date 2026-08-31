import os

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from documents.models import DocumentFile


def _uploaded(name="doc.pdf"):
    return SimpleUploadedFile(name, b"%PDF-fake", content_type="application/pdf")


@pytest.mark.django_db
def test_document_file_delete_removes_file(django_capture_on_commit_callbacks, document):
    doc_file = DocumentFile.objects.create(document=document, file=_uploaded())
    file_path = doc_file.file.path
    assert os.path.exists(file_path)

    with django_capture_on_commit_callbacks(execute=True):
        doc_file.delete()

    assert not os.path.exists(file_path)


@pytest.mark.django_db
def test_document_file_replace_file_removes_old_file(django_capture_on_commit_callbacks, document):
    doc_file = DocumentFile.objects.create(document=document, file=_uploaded("old.pdf"))
    old_path = doc_file.file.path

    with django_capture_on_commit_callbacks(execute=True):
        doc_file.file = _uploaded("new.pdf")
        doc_file.save()

    assert not os.path.exists(old_path)
    assert os.path.exists(doc_file.file.path)


@pytest.mark.django_db
def test_shared_filename_not_deleted_while_another_row_references_it(django_capture_on_commit_callbacks, document):
    doc_file1 = DocumentFile.objects.create(document=document, file=_uploaded("shared.pdf"))
    shared_name = doc_file1.file.name
    doc_file2 = DocumentFile.objects.create(document=document, file=_uploaded("other.pdf"))
    doc_file2.file.name = shared_name
    doc_file2.save(update_fields=["file"])

    file_path = doc_file1.file.path
    assert os.path.exists(file_path)

    with django_capture_on_commit_callbacks(execute=True):
        doc_file1.delete()

    assert os.path.exists(file_path)


@pytest.mark.django_db
def test_missing_file_on_disk_does_not_raise(django_capture_on_commit_callbacks, document):
    doc_file = DocumentFile.objects.create(document=document, file=_uploaded())
    os.remove(doc_file.file.path)

    with django_capture_on_commit_callbacks(execute=True):
        doc_file.delete()  # must not raise even though the file is already gone


@pytest.mark.django_db
def test_replacing_file_resets_extraction_state(document):
    doc_file = DocumentFile.objects.create(
        document=document,
        file=_uploaded("old.pdf"),
        extraction_status="done",
        extracted_text="contenu extrait",
        ocr_used=True,
        extraction_error="",
    )
    doc_file.file = _uploaded("new.pdf")
    doc_file.save()
    doc_file.refresh_from_db()

    assert doc_file.extraction_status == "pending"
    assert doc_file.extracted_text == ""
    assert doc_file.ocr_used is False
    assert doc_file.extracted_at is None


@pytest.mark.django_db
def test_saving_without_changing_file_keeps_extraction_state(document):
    doc_file = DocumentFile.objects.create(
        document=document,
        file=_uploaded("scan.pdf"),
        extraction_status="done",
        extracted_text="contenu extrait",
    )
    doc_file.caption = "Légende mise à jour"
    doc_file.save()
    doc_file.refresh_from_db()

    assert doc_file.extraction_status == "done"
    assert doc_file.extracted_text == "contenu extrait"


@pytest.mark.django_db
def test_replacing_file_removes_thumbnail_file(django_capture_on_commit_callbacks, document):
    doc_file = DocumentFile.objects.create(
        document=document,
        file=_uploaded("old.pdf"),
        thumbnail=SimpleUploadedFile("thumb.png", b"\x89PNG\r\n\x1a\nfake", content_type="image/png"),
    )
    thumbnail_path = doc_file.thumbnail.path
    assert os.path.exists(thumbnail_path)

    with django_capture_on_commit_callbacks(execute=True):
        doc_file.file = _uploaded("new.pdf")
        doc_file.save()

    assert not os.path.exists(thumbnail_path)
