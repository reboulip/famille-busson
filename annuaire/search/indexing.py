from django.db import connection, transaction
from django.db.models import Model
from django.db.models.signals import post_delete, post_save

from .registry import SearchSpec, all_specs, register
from .text import MAX_SEARCH_TEXT_LENGTH, normalize


def build_index_payload(instance: Model, spec: SearchSpec) -> dict:
    """Extract and normalize every weighted field into one payload.

    Unaccenting happens here, in Python, identically for every weight and for
    both backends -- never via a Postgres `unaccent` extension -- so what CI
    (SQLite) verifies is exactly what production does.
    """
    weighted_text: dict[str, str] = {}
    parts: list[str] = []
    for weight, extractor in spec.weights.items():
        text = normalize(extractor(instance) or "")
        weighted_text[weight] = text
        if text:
            parts.append(text)
    search_text = " ".join(parts)[:MAX_SEARCH_TEXT_LENGTH]
    return {"search_text": search_text, "weighted_text": weighted_text}


def apply_index(model: type[Model], pk, payload: dict) -> None:
    """Writes via `.update()`, never `.save()` -- `.save()` would re-fire
    `post_save` and loop straight back into the receiver that scheduled this."""
    fields = {"search_text": payload["search_text"]}
    if connection.vendor == "postgresql":
        from django.contrib.postgres.search import SearchVector
        from django.db.models import Value

        vector = None
        for weight, text in payload["weighted_text"].items():
            component = SearchVector(Value(text), weight=weight, config="french")
            vector = component if vector is None else vector + component
        fields["search_vector"] = vector
    model.objects.filter(pk=pk).update(**fields)


def enqueue_reindex(model: type[Model], pk) -> None:
    """Public so a signal a generic post_save/reindex_on pairing can't express
    (e.g. an M2M change) can still schedule a reindex through the same path."""

    def _task():
        from django_q.tasks import async_task

        from annuaire.tasks import reindex_search_object

        async_task(reindex_search_object, model._meta.app_label, model._meta.model_name, pk)

    transaction.on_commit(_task)


def register_search_index(model: type[Model], spec: SearchSpec, *, reindex_on=()) -> None:
    """Registers `spec` and wires signal-driven reindexing for `model`.

    Mirrors `annuaire.file_cleanup.register_file_cleanup`'s registration-helper
    idiom. `reindex_on` is an iterable of `(child_model, fk_field_name)` pairs:
    both save and delete on the child re-enqueue the *parent*'s reindex, which is
    how a `Document`'s index picks up its `DocumentFile.extracted_text` children
    -- including a deleted file's text disappearing, since the reindex recomputes
    `search_text` from scratch against whatever files remain.
    """
    register(model, spec)

    def _on_save(sender, instance, update_fields=None, **kwargs):
        if update_fields is not None and not (set(update_fields) & spec.source_fields):
            return
        enqueue_reindex(model, instance.pk)

    post_save.connect(_on_save, sender=model, weak=False)

    for child_model, fk_field in reindex_on:

        def _on_child_change(sender, instance, fk_field=fk_field, **kwargs):
            parent_pk = getattr(instance, f"{fk_field}_id")
            if parent_pk is not None:
                enqueue_reindex(model, parent_pk)

        post_save.connect(_on_child_change, sender=child_model, weak=False)
        post_delete.connect(_on_child_change, sender=child_model, weak=False)


def backfill_search_indexes() -> int:
    """Reindex every row across every registered spec. Shared by the management
    command and by each app's own migration data-backfill, so the two can never
    drift apart. Returns the number of rows reindexed."""
    count = 0
    for model, spec in all_specs().items():
        for instance in model.objects.iterator():
            apply_index(model, instance.pk, build_index_payload(instance, spec))
            count += 1
    return count
