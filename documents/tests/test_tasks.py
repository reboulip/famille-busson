"""Background-queue task wrapper (9.6) -- documents.tasks.

The command-level behavior (OCR counting, error handling, thumbnails, limits) is
already covered in depth by test_management_extract_document_content.py, which now
exercises this same function indirectly through the command. These tests check the
function's own return contract directly, since a task has no stdout to assert on.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from documents.models import DocumentFile
from documents.tasks import process_pending_document_files


def _text_pdf(text="Contenu réel."):
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return SimpleUploadedFile("scan.pdf", data, content_type="application/pdf")


@pytest.mark.django_db
def test_returns_zero_counts_and_no_errors_when_nothing_is_pending(db):
    processed, ocr_count, error_count, errors = process_pending_document_files()
    assert (processed, ocr_count, error_count, errors) == (0, 0, 0, [])


@pytest.mark.django_db
def test_processes_a_pending_file_and_returns_counts(document):
    DocumentFile.objects.create(document=document, file=_text_pdf("Un texte à trouver."))

    processed, ocr_count, error_count, errors = process_pending_document_files()

    assert processed == 1
    assert error_count == 0
    assert errors == []


@pytest.mark.django_db
def test_a_failing_file_is_reported_without_aborting_the_run(document, monkeypatch):
    DocumentFile.objects.create(document=document, file=_text_pdf())

    def _raise(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(DocumentFile, "save", _raise)

    processed, ocr_count, error_count, errors = process_pending_document_files()

    assert processed == 0
    assert error_count == 1
    assert len(errors) == 1
    assert "boom" in errors[0]
