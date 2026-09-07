"""11.2 -- search indexes: the registry/indexing machinery itself."""

import pytest

from annuaire.models import Person
from annuaire.search.indexing import apply_index, backfill_search_indexes, build_index_payload
from annuaire.search.registry import all_specs, get_spec


def test_no_registered_model_declares_a_gin_index_in_meta():
    # The GIN index must only ever exist via the vendor-guarded RunPython in each
    # app's migration -- never via Meta.indexes/GinIndex, which would make SQLite's
    # _remake_table (triggered by any future AlterField) emit invalid "USING gin"
    # DDL the next time an unrelated migration touches the model.
    for model in all_specs():
        for index in model._meta.indexes:
            assert index.__class__.__name__ != "GinIndex", f"{model.__name__} declares a GinIndex in Meta.indexes"


@pytest.mark.django_db
def test_build_index_payload_normalizes_and_joins_weighted_text():
    person = Person(first_name="Büsson", last_name="Été", description="**gras**")
    spec = get_spec(Person)

    payload = build_index_payload(person, spec)

    assert "busson" in payload["search_text"]
    assert "ete" in payload["search_text"]
    assert "gras" in payload["search_text"]


@pytest.mark.django_db
def test_apply_index_writes_via_update_not_save(monkeypatch):
    person = Person.objects.create(first_name="Alice", last_name="Busson")

    def _fail_if_called(*args, **kwargs):
        raise AssertionError(".save() must never be called by apply_index")

    monkeypatch.setattr(Person, "save", _fail_if_called)

    apply_index(Person, person.pk, {"search_text": "alice busson", "weighted_text": {"A": "alice busson"}})

    person = Person.objects.get(pk=person.pk)
    assert person.search_text == "alice busson"


@pytest.mark.django_db
def test_backfill_search_indexes_reindexes_every_registered_model(person):
    Person.objects.filter(pk=person.pk).update(search_text="")

    count = backfill_search_indexes()

    person.refresh_from_db()
    assert count > 0
    assert "busson" in person.search_text
