from django.apps import AppConfig


class GenealogyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "genealogy"

    def ready(self) -> None:
        import genealogy.signals  # noqa: F401 -- registers the search index

        return super().ready()
