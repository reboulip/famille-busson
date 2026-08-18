from django.apps import AppConfig


class PublicationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "publications"

    def ready(self) -> None:
        import publications.signals  # noqa: F401 -- registers the file-cleanup signal handlers

        return super().ready()
