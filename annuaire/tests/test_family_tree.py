import pytest

from annuaire.family_tree import build_family_chart_data, find_components
from annuaire.models import Person, Relation


@pytest.mark.django_db
def test_empty_db_returns_empty_data():
    assert build_family_chart_data() == []


def test_empty_data_returns_no_components():
    assert find_components([]) == []


@pytest.mark.django_db
def test_isolated_person_is_own_component(person):
    data = build_family_chart_data()
    components = find_components(data)
    assert components == [{"root_id": str(person.pk), "size": 1, "label": "Alice Busson"}]


@pytest.mark.django_db
def test_parent_relation_direction(person, other_person):
    # person1=other_person, person2=person, type=2 means "person is other_person's parent".
    Relation.objects.create(person1=other_person, person2=person, relationship_type=2)
    data = build_family_chart_data()
    by_id = {node["id"]: node for node in data}
    assert by_id[str(other_person.pk)]["rels"]["parents"] == [str(person.pk)]
    assert by_id[str(person.pk)]["rels"]["children"] == [str(other_person.pk)]


@pytest.mark.django_db
def test_relation_not_double_counted(person, other_person):
    Relation.objects.create(person1=other_person, person2=person, relationship_type=2)
    # The post_save signal mirrors this into a second row.
    assert Relation.objects.count() == 2

    data = build_family_chart_data()
    by_id = {node["id"]: node for node in data}
    assert by_id[str(other_person.pk)]["rels"]["parents"] == [str(person.pk)]
    assert by_id[str(person.pk)]["rels"]["children"] == [str(other_person.pk)]


@pytest.mark.django_db
@pytest.mark.parametrize("relationship_type", [0, 1])
def test_spouse_types_collapse_to_rels_spouses(person, other_person, relationship_type):
    Relation.objects.create(person1=person, person2=other_person, relationship_type=relationship_type)
    data = build_family_chart_data()
    by_id = {node["id"]: node for node in data}
    assert by_id[str(person.pk)]["rels"]["spouses"] == [str(other_person.pk)]
    assert by_id[str(other_person.pk)]["rels"]["spouses"] == [str(person.pk)]


@pytest.mark.django_db
def test_self_relation_is_dropped(person):
    # bulk_create bypasses the post_save signal, which would otherwise recurse
    # forever trying to mirror a person1==person2 row -- a self-relation should
    # never occur via the normal UI (AddRelationView blocks it), but defend
    # against a stray one (e.g. bad fixture data) without touching that signal.
    Relation.objects.bulk_create([Relation(person1=person, person2=person, relationship_type=2)])
    data = build_family_chart_data()
    by_id = {node["id"]: node for node in data}
    assert by_id[str(person.pk)]["rels"] == {"parents": [], "spouses": [], "children": []}


@pytest.mark.django_db
def test_defensive_symmetrization_for_one_sided_relation(person, other_person):
    # bulk_create bypasses the post_save signal, so only one side exists in the DB.
    Relation.objects.bulk_create([Relation(person1=other_person, person2=person, relationship_type=2)])
    assert Relation.objects.count() == 1

    data = build_family_chart_data()
    by_id = {node["id"]: node for node in data}
    assert by_id[str(other_person.pk)]["rels"]["parents"] == [str(person.pk)]
    assert by_id[str(person.pk)]["rels"]["children"] == [str(other_person.pk)]


@pytest.mark.django_db
def test_defensive_symmetrization_for_one_sided_child_relation(person, other_person):
    # Same as the parent case above, but starting from the "child" side of the pair.
    Relation.objects.bulk_create([Relation(person1=person, person2=other_person, relationship_type=3)])
    assert Relation.objects.count() == 1

    data = build_family_chart_data()
    by_id = {node["id"]: node for node in data}
    assert by_id[str(person.pk)]["rels"]["children"] == [str(other_person.pk)]
    assert by_id[str(other_person.pk)]["rels"]["parents"] == [str(person.pk)]


@pytest.mark.django_db
def test_defensive_symmetrization_for_one_sided_spouse_relation(person, other_person):
    Relation.objects.bulk_create([Relation(person1=person, person2=other_person, relationship_type=1)])
    assert Relation.objects.count() == 1

    data = build_family_chart_data()
    by_id = {node["id"]: node for node in data}
    assert by_id[str(person.pk)]["rels"]["spouses"] == [str(other_person.pk)]
    assert by_id[str(other_person.pk)]["rels"]["spouses"] == [str(person.pk)]


@pytest.mark.django_db
def test_ids_are_strings(person):
    data = build_family_chart_data()
    assert data[0]["id"] == str(person.pk)
    assert isinstance(data[0]["id"], str)


@pytest.mark.django_db
def test_url_populated(person):
    data = build_family_chart_data()
    node = data[0]
    assert node["data"]["url"] == f"/annuaire/personne/{person.pk}/"


@pytest.mark.django_db
def test_avatar_falls_back_to_default_picture(person):
    data = build_family_chart_data()
    assert data[0]["data"]["avatar"].endswith("default_profile_picture.png")


@pytest.mark.django_db
def test_birthday_is_bare_year_string_or_empty(person):
    import datetime

    data = build_family_chart_data()
    assert data[0]["data"]["birthday"] == ""

    person.birth_date = datetime.date(1975, 6, 1)
    person.save()
    data = build_family_chart_data()
    by_id = {node["id"]: node for node in data}
    assert by_id[str(person.pk)]["data"]["birthday"] == "1975"


@pytest.mark.django_db
def test_component_root_prefers_highest_degree(person, other_person):
    # Add a third person related only to `person`, so `person` has degree 2
    # (other_person + third) while `other_person` and `third` each have degree 1.
    third = Person.objects.create(first_name="Carol", last_name="Busson")
    Relation.objects.create(person1=person, person2=other_person, relationship_type=1)
    Relation.objects.create(person1=person, person2=third, relationship_type=2)

    data = build_family_chart_data()
    components = find_components(data)
    assert len(components) == 1
    assert components[0]["root_id"] == str(person.pk)
    assert components[0]["size"] == 3


@pytest.mark.django_db
def test_multiple_disconnected_components_sorted_by_size(person, other_person):
    Person.objects.create(first_name="Solo", last_name="Busson")
    Relation.objects.create(person1=person, person2=other_person, relationship_type=1)

    data = build_family_chart_data()
    components = find_components(data)
    assert [component["size"] for component in components] == [2, 1]
