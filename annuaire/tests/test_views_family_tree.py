import json
from pathlib import Path

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
def test_genealogie_renders_detail_panel_and_branch_picker_markup(auth_client, person):
    response = auth_client.get(reverse("genealogie"))
    content = response.content.decode()
    assert 'id="genealogie-detail"' in content
    assert 'id="genealogie-branch-picker"' in content


@pytest.mark.django_db
def test_genealogie_loads_d3_before_family_chart(auth_client, person):
    # family-chart's UMD bundle reads a global `d3` at load time -- d3 must be
    # the earlier <script> tag, or the library throws on load in a real browser.
    response = auth_client.get(reverse("genealogie"))
    content = response.content.decode()
    assert content.index("vendor/d3/d3.min.js") < content.index("vendor/family-chart/family-chart.min.js")
    assert content.index("vendor/family-chart/family-chart.min.js") < content.index("js/family_tree.js")


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


def test_genealogie_js_disables_single_parent_placeholder():
    # Regression guard for the confusing "ADD" placeholder on single-known-parent
    # slots (#59) -- the chart must be configured to omit it entirely.
    js_path = Path(__file__).resolve().parent.parent / "static" / "js" / "family_tree.js"
    assert "setSingleParentEmptyCard(false)" in js_path.read_text()


@pytest.mark.django_db
def test_genealogie_detail_panel_uses_bootstrap_visibility(auth_client, person):
    # Regression guard for the tree de-centering when the detail panel opens
    # (#59) -- the panel must reserve its layout space via Bootstrap display
    # utilities rather than the `hidden` attribute, which removes it from
    # layout and shrinks the chart's width when toggled.
    response = auth_client.get(reverse("genealogie"))
    content = response.content.decode()
    assert 'id="genealogie-detail" class="genealogie-detail d-none d-lg-block"' in content
    assert '<aside id="genealogie-detail" class="genealogie-detail" hidden>' not in content
