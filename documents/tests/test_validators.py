import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from documents.validators import MAX_DOCUMENT_SIZE, validate_document_extension, validate_document_size


@pytest.mark.parametrize(
    "filename",
    [
        "scan.pdf",
        "photo.jpg",
        "photo.JPEG",
        "photo.png",
        "photo.gif",
        "photo.webp",
        "letter.doc",
        "letter.docx",
        "letter.odt",
        "sheet.xls",
        "sheet.xlsx",
        "sheet.ods",
        "slides.ppt",
        "slides.pptx",
        "slides.odp",
        "notes.txt",
        "notes.rtf",
        "data.csv",
    ],
)
def test_validate_document_extension_accepts_allowlisted_types(filename):
    validate_document_extension(SimpleUploadedFile(filename, b"content"))


@pytest.mark.parametrize(
    "filename",
    [
        "image.svg",
        "page.html",
        "page.htm",
        "page.xhtml",
        "script.exe",
        "archive.zip",
        "no_extension",
    ],
)
def test_validate_document_extension_rejects_disallowed_types(filename):
    with pytest.raises(ValidationError):
        validate_document_extension(SimpleUploadedFile(filename, b"content"))


def test_validate_document_extension_case_insensitive():
    validate_document_extension(SimpleUploadedFile("SCAN.PDF", b"content"))


def test_validate_document_size_accepts_under_cap():
    small_file = SimpleUploadedFile("scan.pdf", b"x" * 1024)
    validate_document_size(small_file)


def test_validate_document_size_rejects_over_cap():
    oversized = SimpleUploadedFile("scan.pdf", b"x" * (MAX_DOCUMENT_SIZE + 1))
    with pytest.raises(ValidationError):
        validate_document_size(oversized)


def test_validate_document_size_accepts_exactly_at_cap():
    exact = SimpleUploadedFile("scan.pdf", b"x" * MAX_DOCUMENT_SIZE)
    validate_document_size(exact)
