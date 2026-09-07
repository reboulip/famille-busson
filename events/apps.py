from django.apps import AppConfig


class EventsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "events"

    def ready(self) -> None:
        import events.signals  # noqa: F401 -- registers the post_save notification receiver

        return super().ready()
