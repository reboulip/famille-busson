from unittest.mock import MagicMock

from annuaire.models import Person
from annuaire.search.backends import FallbackSearchBackend, PostgresSearchBackend, get_search_backend
from annuaire.search.text import terms


class _FakeConnection:
    def __init__(self, vendor):
        self.vendor = vendor


def test_get_search_backend_dispatches_on_vendor():
    assert isinstance(get_search_backend(_FakeConnection("postgresql")), PostgresSearchBackend)
    assert isinstance(get_search_backend(_FakeConnection("sqlite")), FallbackSearchBackend)


def test_get_search_backend_defaults_to_connection_vendor(db):
    # The test suite always runs on SQLite (see CLAUDE.md's toolchain section).
    assert isinstance(get_search_backend(), FallbackSearchBackend)


# ---------------------------------------------------------------------------
# FallbackSearchBackend -- exercised end-to-end against a real SQLite queryset
# ---------------------------------------------------------------------------


def test_fallback_backend_filters_by_icontains(db):
    Person.objects.create(first_name="Alice", last_name="Busson")
    Person.objects.create(first_name="Bob", last_name="Martin")
    backend = FallbackSearchBackend()

    qs = backend.filter(Person.objects.all(), terms("busson"), vector_field="search_vector", text_field="last_name")

    assert list(qs) == list(Person.objects.filter(last_name__icontains="busson"))


def test_fallback_backend_filter_with_no_terms_returns_none(db):
    Person.objects.create(first_name="Alice", last_name="Busson")
    backend = FallbackSearchBackend()

    qs = backend.filter(Person.objects.all(), [], vector_field="search_vector", text_field="last_name")

    assert list(qs) == []


def test_fallback_backend_annotate_rank_is_always_zero(db):
    Person.objects.create(first_name="Alice", last_name="Busson")
    backend = FallbackSearchBackend()

    qs = backend.annotate_rank(Person.objects.all(), terms("busson"), vector_field="search_vector")

    assert all(person.rank == 0.0 for person in qs)


def test_fallback_backend_preserves_existing_ordering(db):
    Person.objects.create(first_name="Bob", last_name="Busson")
    Person.objects.create(first_name="Alice", last_name="Busson")
    backend = FallbackSearchBackend()

    qs = backend.filter(
        Person.objects.order_by("first_name"), terms("busson"), vector_field="search_vector", text_field="last_name"
    )

    assert [p.first_name for p in qs] == ["Alice", "Bob"]


# ---------------------------------------------------------------------------
# PostgresSearchBackend -- exercised against a mocked queryset, not a real model.
# No model in this codebase has a SearchVectorField yet (that lands in item 11.2),
# and Django's ORM resolves a `.filter(**{field: ...})`/`.annotate()` field name
# against the model's actual fields even when the query is never executed -- so a
# real queryset would raise FieldError before the SearchQuery/SearchRank shape
# could be inspected at all. Mocking isolates exactly what this item owns: that
# the right expressions get built and passed through.
# ---------------------------------------------------------------------------


def test_postgres_backend_filter_builds_raw_tsquery(db):
    from django.contrib.postgres.search import SearchQuery

    backend = PostgresSearchBackend()
    qs = MagicMock()

    backend.filter(qs, terms("famille busson"), vector_field="search_vector", text_field="last_name")

    qs.filter.assert_called_once()
    (query,) = qs.filter.call_args.kwargs.values()
    assert isinstance(query, SearchQuery)
    assert query.source_expressions[1].value == "famille:* & busson:*"


def test_postgres_backend_filter_with_no_terms_returns_none():
    backend = PostgresSearchBackend()
    qs = MagicMock()

    result = backend.filter(qs, [], vector_field="search_vector", text_field="last_name")

    qs.filter.assert_not_called()
    assert result == qs.none.return_value


def test_postgres_backend_annotate_rank_adds_rank_annotation(db):
    from django.contrib.postgres.search import SearchQuery

    backend = PostgresSearchBackend()
    qs = MagicMock()

    backend.annotate_rank(qs, terms("busson"), vector_field="search_vector")

    qs.annotate.assert_called_once()
    rank_expr = qs.annotate.call_args.kwargs["rank"]
    assert isinstance(rank_expr.source_expressions[2], SearchQuery)
    qs.annotate.return_value.order_by.assert_called_once_with("-rank")


def test_postgres_backend_annotate_rank_with_no_terms_is_zero_value():
    from django.db.models import Value

    backend = PostgresSearchBackend()
    qs = MagicMock()

    backend.annotate_rank(qs, [], vector_field="search_vector")

    qs.annotate.assert_called_once()
    rank_expr = qs.annotate.call_args.kwargs["rank"]
    assert isinstance(rank_expr, Value)
    assert rank_expr.value == 0.0
