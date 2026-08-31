"""Backfill DocumentFile.extracted_text/thumbnail for pending uploads: PDF text
via PyMuPDF (with Tesseract OCR fallback for image-only pages/scans) and
direct OCR for raster image uploads, plus a first-page thumbnail for PDFs.
Office documents and plain text files are marked "unsupported" and never
processed -- extraction/search coverage is deliberately PDF + images only.

Usage (from the repo root):
    uv run python manage.py extract_document_content

Meant to be run every 15 minutes via cron, e.g.:
    */15 * * * * cd /app && uv run python manage.py extract_document_content
"""

from __future__ import annotations

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from documents.extraction import extract_file_content
from documents.models import DocumentFile

DEFAULT_LIMIT = 20
MAX_OCR_PAGES_PER_FILE = 20


class Command(BaseCommand):
    help = __doc__ or ""

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)

    def handle(self, *args, **options):
        candidates = DocumentFile.objects.filter(extraction_status="pending")[: options["limit"]]

        if not candidates:
            self.stdout.write("Aucun fichier à traiter.")
            return

        processed = 0
        ocr_count = 0
        error_count = 0
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
                self.stdout.write(f"Erreur sur {document_file} : {exc}")
                continue

            processed += 1
            if result.ocr_used:
                ocr_count += 1
            if result.status == "error":
                error_count += 1

        self.stdout.write(f"{processed} fichier(s) traité(s), {ocr_count} par OCR, {error_count} erreur(s).")
