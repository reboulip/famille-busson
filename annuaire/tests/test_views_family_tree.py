import json

import pytest
from django.urls import reverse

LOGIN_URL = "/annuaire/login/"


@pytest.mark.django_db
def test_genealogie_requires_login(client):
    response = client.get(reverse("genealogie"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_genealogie_returns_200(auth_client):
    response = auth_client.get(reverse("genealogie"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_genealogie_person_requires_login(client, person):
    response = client.get(reverse("genealogie-person", kwargs={"pk": person.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_genealogie_person_returns_200(auth_client, person):
    response = auth_client.get(reverse("genealogie-person", kwargs={"pk": person.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_genealogie_person_404_on_invalid_pk(auth_client):
    response = auth_client.get(reverse("genealogie-person", kwargs={"pk": 99999}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_genealogie_context_has_graph_and_components_json(auth_client, person, other_person):
    response = auth_client.get(reverse("genealogie"))
    assert "graph_json" in response.context
    assert "components_json" in response.context
    graph = json.loads(response.context["graph_json"])
    components = json.loads(response.context["components_json"])
    assert {node["id"] for node in graph} == {str(person.pk), str(other_person.pk)}
    assert len(components) == 2


@pytest.mark.django_db
def test_genealogie_person_main_id_is_requested_pk(auth_client, person, other_person):
    response = auth_client.get(reverse("genealogie-person", kwargs={"pk": other_person.pk}))
    assert response.context["main_id"] == str(other_person.pk)


@pytest.mark.django_db
def test_genealogie_bare_route_defaults_main_id_to_own_profile(auth_client, person):
    response = auth_client.get(reverse("genealogie"))
    assert response.context["main_id"] == str(person.pk)


@pytest.mark.django_db
def test_genealogie_bare_route_main_id_none_without_profile(client, account):
    # `account` has no linked Person (unlike the `person`/`auth_client` fixtures).
    client.login(username="alice@example.com", password="testpass123!")
    response = client.get(reverse("genealogie"))
    assert response.status_code == 200
    assert response.context["main_id"] is None
