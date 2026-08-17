from django.apps import AppConfig


class DirectoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "annuaire"

    def ready(self) -> None:
        import annuaire.signals  # noqa: F401 -- registers the @receiver signal handlers

        return super().ready()
