import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class DocumentStorage(FileSystemStorage):
    """Storage for protected document files, kept outside MEDIA_ROOT and
    media_serve's reach. base_location/location are plain properties here
    (not cached_property, unlike the base class), so they always read the
    current settings.DOCUMENTS_ROOT -- FileSystemStorage's own
    cache-invalidation signal only reacts to a changed "MEDIA_ROOT" setting,
    which would otherwise freeze a fixed location at construction time and
    ignore a test overriding settings.DOCUMENTS_ROOT."""

    @property
    def base_location(self):
        return settings.DOCUMENTS_ROOT

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    def url(self, name):
        raise NotImplementedError(
            "Les fichiers de documents sont protégés : ils ne sont jamais servis par une URL publique."
        )


def get_document_storage():
    return DocumentStorage()
