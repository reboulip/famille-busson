"""Background-queue task wrappers (9.6).

`process_pending_document_files` is the same batch logic the
`extract_document_content` management command runs by hand -- both call this,
so there is exactly one place that owns it. django-q2 calls it directly by
import path (`documents.tasks.process_pending_document_files`); it takes no
required arguments, since the scheduled run always processes whatever is
pending up to the default limit.
"""

from __future__ import annotations

from django.core.files.base import ContentFile
from django.utils import timezone

from documents.extraction import extract_file_content
from documents.models import DocumentFile

DEFAULT_LIMIT = 20
MAX_OCR_PAGES_PER_FILE = 20


def process_pending_document_files(limit: int = DEFAULT_LIMIT) -> tuple[int, int, int, list[str]]:
    """Process up to `limit` pending DocumentFiles.

    Returns (processed, ocr_count, error_count, error_messages) -- one French
    "Erreur sur ..." line per failed file, for the caller (command or task) to
    report however fits it (stdout vs. logging).
    """
    candidates = DocumentFile.objects.filter(extraction_status="pending")[:limit]

    processed = 0
    ocr_count = 0
    error_count = 0
    error_messages = []
    for document_file in candidates:
        try:
            result = extract_file_content(document_file, max_ocr_pages=MAX_OCR_PAGES_PER_FILE)
            document_file.extracted_text = result.text
            document_file.extraction_status = result.status
            document_file.extraction_error = result.error
            document_file.extracted_at = timezone.now()
            document_file.ocr_used = result.ocr_used
            if result.thumbnail_bytes is not None:
                document_file.thumbnail.save("thumbnail.png", ContentFile(result.thumbnail_bytes), save=False)
            document_file.save()
        except Exception as exc:
            error_count += 1
            error_messages.append(f"Erreur sur {document_file} : {exc}")
            continue

        processed += 1
        if result.ocr_used:
            ocr_count += 1
        if result.status == "error":
            error_count += 1

    return processed, ocr_count, error_count, error_messages
