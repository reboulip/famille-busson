import os

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".doc",
    ".docx",
    ".odt",
    ".xls",
    ".xlsx",
    ".ods",
    ".ppt",
    ".pptx",
    ".odp",
    ".txt",
    ".rtf",
    ".csv",
}
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50 Mo


def validate_document_extension(file):
    extension = os.path.splitext(file.name)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            _("Type de fichier non autorisé : « %(extension)s ».") % {"extension": extension or _("sans extension")}
        )


def validate_document_size(file):
    if file.size > MAX_DOCUMENT_SIZE:
        raise ValidationError(
            _("Le fichier est trop volumineux (%(size)s Mo). Taille maximale : %(max)s Mo.")
            % {"size": f"{file.size / (1024 * 1024):.1f}", "max": MAX_DOCUMENT_SIZE // (1024 * 1024)}
        )
