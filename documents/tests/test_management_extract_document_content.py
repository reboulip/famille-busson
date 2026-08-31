from io import StringIO

import pymupdf
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from documents.models import DocumentFile


def _text_pdf(text="Contenu réel."):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return SimpleUploadedFile("scan.pdf", data, content_type="application/pdf")


def _run_command(*args, **kwargs):
    out = StringIO()
    call_command("extract_document_content", *args, stdout=out, **kwargs)
    return out.getvalue()


@pytest.mark.django_db
def test_command_processes_pending_files(document):
    doc_file = DocumentFile.objects.create(document=document, file=_text_pdf("Un texte à trouver."))
    assert doc_file.extraction_status == "pending"

    output = _run_command()

    doc_file.refresh_from_db()
    assert doc_file.extraction_status == "done"
    assert "Un texte à trouver." in doc_file.extracted_text
    assert doc_file.extracted_at is not None
    assert "1 fichier(s) traité(s)" in output


@pytest.mark.django_db
def test_command_no_pending_files(db):
    output = _run_command()
    assert "Aucun fichier à traiter." in output


@pytest.mark.django_db
def test_command_skips_already_done_files(document):
    doc_file = DocumentFile.objects.create(
        document=document,
        file=_text_pdf(),
        extraction_status="done",
        extracted_text="déjà traité",
    )
    _run_command()
    doc_file.refresh_from_db()
    assert doc_file.extracted_text == "déjà traité"


@pytest.mark.django_db
def test_command_respects_limit(document):
    for i in range(3):
        DocumentFile.objects.create(document=document, file=_text_pdf(f"Texte {i}"))

    output = _run_command("--limit", "2")

    done_count = DocumentFile.objects.filter(extraction_status="done").count()
    assert done_count == 2
    assert "2 fichier(s) traité(s)" in output


@pytest.mark.django_db
def test_command_one_corrupt_file_does_not_abort_run(document):
    good_file = DocumentFile.objects.create(document=document, file=_text_pdf("Bon fichier"))
    bad_file = DocumentFile.objects.create(
        document=document, file=SimpleUploadedFile("bad.pdf", b"not a real pdf", content_type="application/pdf")
    )

    _run_command()

    good_file.refresh_from_db()
    bad_file.refresh_from_db()
    assert good_file.extraction_status == "done"
    assert bad_file.extraction_status == "error"
    assert bad_file.extraction_error


@pytest.mark.django_db
def test_command_unsupported_file_type(document):
    doc_file = DocumentFile.objects.create(
        document=document, file=SimpleUploadedFile("notes.txt", b"some text", content_type="text/plain")
    )
    _run_command()
    doc_file.refresh_from_db()
    assert doc_file.extraction_status == "unsupported"


@pytest.mark.django_db
def test_command_saves_thumbnail_for_pdf(document):
    doc_file = DocumentFile.objects.create(document=document, file=_text_pdf())
    _run_command()
    doc_file.refresh_from_db()
    assert doc_file.thumbnail


@pytest.mark.django_db
def test_command_counts_ocr_used_files(document, monkeypatch):
    import io

    from PIL import Image

    import documents.extraction as extraction

    monkeypatch.setattr(extraction, "tesseract_available", lambda: True)
    monkeypatch.setattr(extraction.pytesseract, "image_to_string", lambda image, lang: "Texte photo")
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="white").save(buf, format="PNG")
    doc_file = DocumentFile.objects.create(
        document=document,
        file=SimpleUploadedFile("photo.png", buf.getvalue(), content_type="image/png"),
    )

    output = _run_command()

    doc_file.refresh_from_db()
    assert doc_file.ocr_used is True
    assert "1 par OCR" in output


@pytest.mark.django_db
def test_command_unexpected_save_failure_is_caught(document, monkeypatch):
    DocumentFile.objects.create(document=document, file=_text_pdf())

    def _raise(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(DocumentFile, "save", _raise)
    output = _run_command()
    assert "Erreur sur" in output
