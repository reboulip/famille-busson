"""Backfill DocumentFile.extracted_text/thumbnail for pending uploads: PDF text
via PyMuPDF (with Tesseract OCR fallback for image-only pages/scans) and
direct OCR for raster image uploads, plus a first-page thumbnail for PDFs.
Office documents and plain text files are marked "unsupported" and never
processed -- extraction/search coverage is deliberately PDF + images only.

Usage (from the repo root):
    uv run python manage.py extract_document_content

Runs every 15 minutes via the background task queue (see docs/background_tasks.md) --
still hand-runnable for ad-hoc/manual use.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from documents.models import DocumentFile
from documents.tasks import DEFAULT_LIMIT, process_pending_document_files


class Command(BaseCommand):
    help = __doc__ or ""

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)

    def handle(self, *args, **options):
        if not DocumentFile.objects.filter(extraction_status="pending").exists():
            self.stdout.write("Aucun fichier à traiter.")
            return

        processed, ocr_count, error_count, error_messages = process_pending_document_files(limit=options["limit"])
        for message in error_messages:
            self.stdout.write(message)
        self.stdout.write(f"{processed} fichier(s) traité(s), {ocr_count} par OCR, {error_count} erreur(s).")
