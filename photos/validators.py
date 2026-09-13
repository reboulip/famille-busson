import os

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif"}
MAX_PHOTO_SIZE = 25 * 1024 * 1024  # 25 Mo
MAX_FILES_PER_SELECTION = 200
MAX_CONCURRENT_UPLOADS = 3


def validate_photo_extension(file):
    extension = os.path.splitext(file.name)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            _("Type de fichier non autorisé : « %(extension)s ».") % {"extension": extension or _("sans extension")}
        )


def validate_photo_size(file):
    if file.size > MAX_PHOTO_SIZE:
        raise ValidationError(
            _("Le fichier est trop volumineux (%(size)s Mo). Taille maximale : %(max)s Mo.")
            % {"size": f"{file.size / (1024 * 1024):.1f}", "max": MAX_PHOTO_SIZE // (1024 * 1024)}
        )
