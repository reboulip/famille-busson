"""Content extraction for uploaded documents: PDF text via PyMuPDF, with
Tesseract OCR as a fallback for image-only pages/scans and for raster image
uploads outright, plus a first-page thumbnail for PDFs. Shared by the
extract_document_content management command -- mirrors annuaire/geocoding.py's
split between pure extraction logic and the command that drives it.

Scope is deliberately PDF + images only (matching the sprint's extraction/
search coverage decision) -- office docs and plain text files are marked
"unsupported" here and never processed, even though they're allowed uploads.
"""

from __future__ import annotations

import io
import shutil
from dataclasses import dataclass

import pymupdf
import pytesseract
from PIL import Image

from documents.previews import preview_kind

MIN_CHARS_PER_PAGE_BEFORE_OCR = 20
THUMBNAIL_DPI = 150
OCR_DPI = 200
OCR_LANGUAGE = "fra"


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    ocr_used: bool
    thumbnail_bytes: bytes | None
    status: str  # "done" | "unsupported" | "error"
    error: str


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def _page_to_image(page, dpi: int) -> Image.Image:
    pixmap = page.get_pixmap(dpi=dpi)
    return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def extract_pdf_text(data: bytes, max_ocr_pages: int = 20) -> tuple[str, bool]:
    """Extract text per page via PyMuPDF; a page with little/no embedded text
    is rasterized and OCR'd instead, up to max_ocr_pages. Returns
    (full_text, ocr_used). If tesseract isn't installed, OCR is silently
    skipped and only the embedded text layer is used."""
    ocr_used = False
    ocr_pages_done = 0
    can_ocr = tesseract_available()
    parts = []
    with pymupdf.open(stream=data, filetype="pdf") as pdf:
        for page in pdf:
            text = page.get_text().strip()
            if len(text) < MIN_CHARS_PER_PAGE_BEFORE_OCR and can_ocr and ocr_pages_done < max_ocr_pages:
                image = _page_to_image(page, OCR_DPI)
                text = pytesseract.image_to_string(image, lang=OCR_LANGUAGE).strip()
                ocr_used = True
                ocr_pages_done += 1
            if text:
                parts.append(text)
    return "\n\n".join(parts), ocr_used


def build_pdf_thumbnail(data: bytes) -> bytes:
    """Render the PDF's first page to PNG bytes. A well-formed PDF always has
    at least one page -- PyMuPDF itself refuses to write a zero-page file."""
    with pymupdf.open(stream=data, filetype="pdf") as pdf:
        pixmap = pdf[0].get_pixmap(dpi=THUMBNAIL_DPI)
        return pixmap.tobytes("png")


def extract_image_text(data: bytes) -> str:
    """OCR a raster image file directly."""
    with Image.open(io.BytesIO(data)) as image:
        return pytesseract.image_to_string(image, lang=OCR_LANGUAGE).strip()


def extract_file_content(document_file, max_ocr_pages: int = 20) -> ExtractionResult:
    """Main entry point: dispatch by file type. Never raises -- callers persist
    `status`/`error` regardless of outcome, so one corrupt file never aborts a
    backfill run."""
    kind = preview_kind(document_file.file.name)
    if kind not in ("pdf", "image"):
        return ExtractionResult(text="", ocr_used=False, thumbnail_bytes=None, status="unsupported", error="")

    try:
        with document_file.file.open("rb") as fh:
            data = fh.read()

        if kind == "pdf":
            text, ocr_used = extract_pdf_text(data, max_ocr_pages=max_ocr_pages)
            thumbnail_bytes = build_pdf_thumbnail(data)
            return ExtractionResult(
                text=text, ocr_used=ocr_used, thumbnail_bytes=thumbnail_bytes, status="done", error=""
            )

        # kind == "image": OCR is the only extraction method, no embedded-text fallback.
        if not tesseract_available():
            return ExtractionResult(
                text="",
                ocr_used=False,
                thumbnail_bytes=None,
                status="error",
                error="OCR non disponible (tesseract non installé).",
            )
        text = extract_image_text(data)
        return ExtractionResult(text=text, ocr_used=True, thumbnail_bytes=None, status="done", error="")
    except Exception as exc:
        return ExtractionResult(text="", ocr_used=False, thumbnail_bytes=None, status="error", error=str(exc)[:255])
