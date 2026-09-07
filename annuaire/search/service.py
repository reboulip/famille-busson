from dataclasses import dataclass

from django.db.models import Count

from .backends import get_search_backend
from .registry import SearchSpec, all_specs
from .text import terms


def model_key(model) -> str:
    return f"{model._meta.app_label}.{model._meta.model_name}"


def _ranked_queryset(user, query_terms: list[str], model, spec: SearchSpec):
    backend = get_search_backend()
    qs = spec.accessible(user)
    if spec.order:
        qs = qs.order_by(*spec.order)
    filtered = backend.filter(qs, query_terms, vector_field="search_vector", text_field="search_text")
    ranked = backend.annotate_rank(filtered, query_terms, vector_field="search_vector")
    if model._meta.model_name == "album":
        # _album_card.html renders {{ album.photo_count }} -- AlbumListView annotates
        # this the same way; a search result must match or the card breaks.
        ranked = ranked.annotate(photo_count=Count("photos"))
    return ranked


@dataclass
class SearchGroup:
    key: str
    label: str
    card_template: str
    results: list
    total_count: int


def search_all(user, query: str, *, per_type_limit: int = 5) -> list[SearchGroup]:
    """One bounded, ranked, access-scoped preview per registered type.

    Never queries Model.objects.all() -- every group starts from spec.accessible(user).
    """
    query_terms = terms(query)
    if not query_terms:
        return []
    groups = []
    for model, spec in all_specs().items():
        ranked = _ranked_queryset(user, query_terms, model, spec)
        groups.append(
            SearchGroup(
                key=model_key(model),
                label=spec.label,
                card_template=spec.card_template,
                results=list(ranked[:per_type_limit]),
                total_count=ranked.count(),
            )
        )
    return groups


def search_one(user, query: str, key: str):
    """Returns (spec, ranked_queryset) for the type matching `key`, or None if
    `key` doesn't name a registered type (e.g. a stale/tampered ?type= value)."""
    query_terms = terms(query)
    if not query_terms:
        return None
    for model, spec in all_specs().items():
        if model_key(model) == key:
            return spec, _ranked_queryset(user, query_terms, model, spec)
    return None
