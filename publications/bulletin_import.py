"""Stage and apply a bulletin package import -- mirrors genealogy/gedcom/importer.py's
stage/apply split. Nothing here is visible outside the staging tables
(BulletinImport/BulletinImportImage) until a staff member explicitly applies it."""

from __future__ import annotations

from datetime import date

from django.core.files.base import ContentFile
from django.db import transaction

from .bulletin_package import validate_package
from .models import Bulletin, BulletinImage, BulletinImport, BulletinImportImage


def partial_date_to_date(value: str) -> date:
    """'1995-04' -> 1995-04-01; '2014-04-29' -> 2014-04-29; '1995' -> 1995-01-01."""
    parts = value.split("-")
    year = int(parts[0])
    month = int(parts[1]) if len(parts) > 1 else 1
    day = int(parts[2]) if len(parts) > 2 else 1
    return date(year, month, day)


def stage_bulletin_import(*, zip_file, source_pdf, uploaded_by, original_filename: str) -> BulletinImport:
    """Validates the uploaded zip and stages it. Raises PackageValidationError
    on a structural problem -- the caller is responsible for not leaving a
    half-staged import behind (wrap in a transaction, as done here)."""
    result = validate_package(zip_file)

    with transaction.atomic():
        bulletin_import = BulletinImport.objects.create(
            uploaded_by=uploaded_by,
            original_filename=original_filename,
            document_id=result.data.get("id", ""),
            data=result.data,
            validation_report={"errors": result.errors, "warnings": result.warnings, "stats": result.stats},
        )
        if source_pdf is not None:
            bulletin_import.source_pdf.save(source_pdf.name, source_pdf, save=True)
        for img in result.data["images"]:
            payload = result.images.get(img["id"])
            if payload is None:
                continue  # missing file: already recorded as an error in validation_report
            image = BulletinImportImage(
                bulletin_import=bulletin_import,
                image_id=img["id"],
                kind=img["kind"],
                width=img["width"],
                height=img["height"],
                sha256=img["sha256"],
            )
            filename = img["file"].rsplit("/", 1)[-1]
            image.file.save(filename, ContentFile(payload), save=False)
            image.save()

    return bulletin_import


def apply_bulletin_import(bulletin_import: BulletinImport, actor) -> Bulletin:
    """Creates real Bulletin/BulletinImage rows from a staged, validated import.
    Only ever called after explicit staff approval -- nothing before this point
    is visible outside the staging tables. Re-importing the same document_id
    updates the existing Bulletin in place (SPEC.md §4)."""
    data = bulletin_import.data
    with transaction.atomic():
        bulletin, _created = Bulletin.objects.update_or_create(
            document_id=data["id"],
            defaults={
                "series_code": data["series"]["code"],
                "series_title": data["series"]["title"],
                "issue_number": data["issue"].get("number"),
                "issue_label": data["issue"].get("label", ""),
                "date_value": data["date"]["value"],
                "sort_date": partial_date_to_date(data["date"]["value"]),
                "title": data["title"],
                "summary": data.get("summary", ""),
                "data": data,
                "schema_version": data["schema_version"],
                "source_sha256": data["source"]["sha256"],
                "source_file_name": data["source"]["file_name"],
                "imported_by": actor,
            },
        )

        if bulletin_import.source_pdf:
            bulletin_import.source_pdf.open("rb")
            try:
                bulletin.source_pdf.save(
                    bulletin_import.source_pdf.name.rsplit("/", 1)[-1],
                    ContentFile(bulletin_import.source_pdf.read()),
                    save=True,
                )
            finally:
                bulletin_import.source_pdf.close()

        bulletin.images.all().delete()
        for staged_image in bulletin_import.images.all():
            staged_image.file.open("rb")
            try:
                image = BulletinImage(
                    bulletin=bulletin,
                    image_id=staged_image.image_id,
                    kind=staged_image.kind,
                    width=staged_image.width,
                    height=staged_image.height,
                    sha256=staged_image.sha256,
                )
                image.file.save(
                    staged_image.file.name.rsplit("/", 1)[-1], ContentFile(staged_image.file.read()), save=True
                )
            finally:
                staged_image.file.close()

        bulletin_import.status = "applied"
        bulletin_import.save(update_fields=["status"])

    return bulletin
