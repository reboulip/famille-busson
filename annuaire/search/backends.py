from typing import Protocol

from django.db import connection as _default_connection
from django.db.models import F, Q, QuerySet, Value


class SearchBackend(Protocol):
    """Shape both database backends present, so callers never branch on vendor."""

    def filter(self, qs: QuerySet, terms: list[str], *, vector_field: str, text_field: str) -> QuerySet: ...

    def annotate_rank(self, qs: QuerySet, terms: list[str], *, vector_field: str) -> QuerySet: ...


class PostgresSearchBackend:
    """Ranked, prefix-matching full-text search over a `SearchVectorField`.

    `terms` must already be sanitized to plain `\\w+` runs (see `search.text.terms`)
    before reaching here -- the raw `:*` prefix syntax below is unsafe on
    unsanitized input.
    """

    def filter(self, qs: QuerySet, terms: list[str], *, vector_field: str, text_field: str) -> QuerySet:
        from django.contrib.postgres.search import SearchQuery

        if not terms:
            return qs.none()
        query = SearchQuery(" & ".join(f"{term}:*" for term in terms), search_type="raw", config="french")
        return qs.filter(**{vector_field: query})

    def annotate_rank(self, qs: QuerySet, terms: list[str], *, vector_field: str) -> QuerySet:
        from django.contrib.postgres.search import SearchQuery, SearchRank

        if not terms:
            return qs.annotate(rank=Value(0.0))
        query = SearchQuery(" & ".join(f"{term}:*" for term in terms), search_type="raw", config="french")
        return qs.annotate(rank=SearchRank(F(vector_field), query, weights=[0.1, 0.2, 0.4, 1.0])).order_by("-rank")


class FallbackSearchBackend:
    """`icontains` search for SQLite (dev/test), where no full-text index exists.

    No ranking is possible here, so `annotate_rank` always yields 0.0 and ordering
    is left to the caller's queryset -- tests must assert result membership, never
    result order, since production never takes this path for ranking.
    """

    def filter(self, qs: QuerySet, terms: list[str], *, vector_field: str, text_field: str) -> QuerySet:
        if not terms:
            return qs.none()
        query = Q()
        for term in terms:
            query &= Q(**{f"{text_field}__icontains": term})
        return qs.filter(query)

    def annotate_rank(self, qs: QuerySet, terms: list[str], *, vector_field: str) -> QuerySet:
        return qs.annotate(rank=Value(0.0))


def get_search_backend(connection=None) -> SearchBackend:
    """Dispatch on the active database vendor."""
    connection = connection or _default_connection
    if connection.vendor == "postgresql":
        return PostgresSearchBackend()
    return FallbackSearchBackend()
