from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "documents"

    def ready(self) -> None:
        import documents.signals  # noqa: F401 -- registers the file-cleanup signal handlers

        return super().ready()
