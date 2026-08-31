import dataclasses

import pymupdf
import pytest

from documents.extraction import (
    ExtractionResult,
    build_pdf_thumbnail,
    extract_file_content,
    extract_image_text,
    extract_pdf_text,
    tesseract_available,
)


def _text_pdf_bytes(text="Contenu réel du document."):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def _blank_pdf_bytes():
    doc = pymupdf.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


class _FakeFieldFile:
    def __init__(self, name, data):
        self.name = name
        self._data = data

    def open(self, mode="rb"):
        import io

        return io.BytesIO(self._data)


class _FakeDocumentFile:
    def __init__(self, name, data):
        self.file = _FakeFieldFile(name, data)


# ---------------------------------------------------------------------------
# extract_pdf_text
# ---------------------------------------------------------------------------


def test_extract_pdf_text_from_text_layer():
    data = _text_pdf_bytes("Contenu réel du document.")
    text, ocr_used = extract_pdf_text(data)
    assert "Contenu réel du document." in text
    assert ocr_used is False


def test_extract_pdf_text_falls_back_to_ocr_for_blank_page(monkeypatch):
    import documents.extraction as extraction

    monkeypatch.setattr(extraction, "tesseract_available", lambda: True)
    monkeypatch.setattr(extraction.pytesseract, "image_to_string", lambda image, lang: "Texte OCR")
    data = _blank_pdf_bytes()
    text, ocr_used = extract_pdf_text(data)
    assert text == "Texte OCR"
    assert ocr_used is True


def test_extract_pdf_text_skips_ocr_when_tesseract_unavailable(monkeypatch):
    import documents.extraction as extraction

    monkeypatch.setattr(extraction, "tesseract_available", lambda: False)
    data = _blank_pdf_bytes()
    text, ocr_used = extract_pdf_text(data)
    assert text == ""
    assert ocr_used is False


def test_extract_pdf_text_respects_max_ocr_pages(monkeypatch):
    import documents.extraction as extraction

    monkeypatch.setattr(extraction, "tesseract_available", lambda: True)
    calls = []
    monkeypatch.setattr(extraction.pytesseract, "image_to_string", lambda image, lang: calls.append(1) or "OCR")
    doc = pymupdf.open()
    for _ in range(3):
        doc.new_page()
    data = doc.tobytes()
    doc.close()
    extract_pdf_text(data, max_ocr_pages=1)
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# build_pdf_thumbnail
# ---------------------------------------------------------------------------


def test_build_pdf_thumbnail_returns_png_bytes():
    data = _text_pdf_bytes()
    thumbnail = build_pdf_thumbnail(data)
    assert thumbnail is not None
    assert thumbnail[:8] == b"\x89PNG\r\n\x1a\n"


# ---------------------------------------------------------------------------
# extract_image_text
# ---------------------------------------------------------------------------


def test_extract_image_text_calls_pytesseract(monkeypatch):
    import documents.extraction as extraction

    monkeypatch.setattr(extraction.pytesseract, "image_to_string", lambda image, lang: "Texte image")
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="white").save(buf, format="PNG")
    text = extract_image_text(buf.getvalue())
    assert text == "Texte image"


# ---------------------------------------------------------------------------
# extract_file_content
# ---------------------------------------------------------------------------


def test_extract_file_content_pdf(monkeypatch):
    document_file = _FakeDocumentFile("scan.pdf", _text_pdf_bytes("Un contenu"))
    result = extract_file_content(document_file)
    assert result.status == "done"
    assert "Un contenu" in result.text
    assert result.thumbnail_bytes is not None


def test_extract_file_content_image_with_tesseract(monkeypatch):
    import io

    from PIL import Image

    import documents.extraction as extraction

    monkeypatch.setattr(extraction, "tesseract_available", lambda: True)
    monkeypatch.setattr(extraction.pytesseract, "image_to_string", lambda image, lang: "Texte photo")
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="white").save(buf, format="PNG")
    document_file = _FakeDocumentFile("photo.png", buf.getvalue())
    result = extract_file_content(document_file)
    assert result.status == "done"
    assert result.text == "Texte photo"
    assert result.ocr_used is True
    assert result.thumbnail_bytes is None


def test_extract_file_content_image_without_tesseract(monkeypatch):
    import documents.extraction as extraction

    monkeypatch.setattr(extraction, "tesseract_available", lambda: False)
    document_file = _FakeDocumentFile("photo.png", b"fake png bytes")
    result = extract_file_content(document_file)
    assert result.status == "error"
    assert "non disponible" in result.error


def test_extract_file_content_unsupported_type():
    document_file = _FakeDocumentFile("notes.txt", b"some text")
    result = extract_file_content(document_file)
    assert result.status == "unsupported"
    assert result.text == ""


def test_extract_file_content_corrupt_pdf_does_not_raise():
    document_file = _FakeDocumentFile("bad.pdf", b"not a real pdf")
    result = extract_file_content(document_file)
    assert result.status == "error"
    assert result.error


def test_extraction_result_is_frozen():
    result = ExtractionResult(text="", ocr_used=False, thumbnail_bytes=None, status="done", error="")
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.text = "changed"


def test_tesseract_available_returns_bool():
    assert isinstance(tesseract_available(), bool)
