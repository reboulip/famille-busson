from django.apps import AppConfig


class PhotosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "photos"

    def ready(self) -> None:
        import pillow_heif

        # Must run before any HEIC/HEIF upload is opened by Pillow (ImageField's
        # own validation, or a later derivative-generation pass) -- registering
        # here, once, at app startup avoids import-order surprises.
        pillow_heif.register_heif_opener()

        import photos.signals  # noqa: F401 -- registers file-cleanup and derivative-reset signal handlers

        return super().ready()
