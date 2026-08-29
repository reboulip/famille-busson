import json
from pathlib import Path

import pytest
from django.urls import reverse

from annuaire.models import Person, Relation

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
def test_genealogie_renders_export_button_with_export_url(auth_client, person):
    response = auth_client.get(reverse("genealogie"))
    content = response.content.decode()
    assert 'id="genealogie-export"' in content
    assert f'data-export-url="{reverse("genealogie-export")}"' in content


@pytest.mark.django_db
def test_genealogie_search_mount_sits_in_the_same_toolbar_as_export_button(auth_client, person):
    # 6.3: search field and export button live in one toolbar row.
    response = auth_client.get(reverse("genealogie"))
    content = response.content.decode()
    toolbar_start = content.index('class="genealogie-toolbar')
    layout_start = content.index("genealogie-layout")
    toolbar_html = content[toolbar_start:layout_start]
    assert 'id="genealogie-search"' in toolbar_html
    assert 'id="genealogie-export"' in toolbar_html


@pytest.mark.django_db
def test_genealogie_loads_d3_before_family_chart(auth_client, person):
    # family-chart's UMD bundle reads a global `d3` at load time -- d3 must be
    # the earlier <script> tag, or the library throws on load in a real browser.
    response = auth_client.get(reverse("genealogie"))
    content = response.content.decode()
    assert content.index("vendor/d3/d3.min.js") < content.index("vendor/family-chart/family-chart.min.js")
    assert content.index("vendor/family-chart/family-chart.min.js") < content.index("js/family_tree.js")


@pytest.mark.django_db
def test_genealogie_loads_family_chart_css_before_main_css(auth_client, person):
    # main.css overrides some .f3 selectors from the vendored family-chart.css
    # (e.g. the long-name label fix) -- same-specificity CSS is decided by
    # load order, so the override only applies if family-chart.css loads
    # first.
    response = auth_client.get(reverse("genealogie"))
    content = response.content.decode()
    assert content.index("vendor/family-chart/family-chart.css") < content.index("css/main.css")


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
def test_genealogie_bare_route_defaults_main_id_to_biggest_branch(auth_client, person):
    # `person` (the auth_client's own profile) is an isolated singleton component;
    # a separate, larger branch exists elsewhere in the tree. The bare route must
    # default to that larger branch's anchor, not to the viewer's own profile (#67).
    branch_a = Person.objects.create(first_name="Branch", last_name="A")
    branch_b = Person.objects.create(first_name="Branch", last_name="B")
    Relation.objects.create(person1=branch_a, person2=branch_b, relationship_type=1)

    response = auth_client.get(reverse("genealogie"))
    components = json.loads(response.context["components_json"])
    assert response.context["main_id"] == components[0]["root_id"]
    assert response.context["main_id"] != str(person.pk)


@pytest.mark.django_db
def test_genealogie_bare_route_main_id_none_without_profile(client, account):
    # `account` has no linked Person (unlike the `person`/`auth_client` fixtures),
    # and no other Person rows exist in the DB either.
    client.login(username="alice@example.com", password="testpass123!")
    response = client.get(reverse("genealogie"))
    assert response.status_code == 200
    assert response.context["main_id"] is None


@pytest.mark.django_db
def test_genealogie_bare_route_without_profile_defaults_to_biggest_branch(client, account, other_person):
    # `account` has no linked Person, but other persons exist in the tree -- the
    # bare route should still default to the biggest branch's anchor.
    client.login(username="alice@example.com", password="testpass123!")
    response = client.get(reverse("genealogie"))
    assert response.status_code == 200
    assert response.context["main_id"] == str(other_person.pk)


def test_genealogie_js_disables_single_parent_placeholder():
    # Regression guard for the confusing "ADD" placeholder on single-known-parent
    # slots (#59) -- the chart must be configured to omit it entirely.
    js_path = Path(__file__).resolve().parent.parent / "static" / "js" / "family_tree.js"
    assert "setSingleParentEmptyCard(false)" in js_path.read_text()


def test_genealogie_js_export_excludes_placeholder_cards():
    # Regression guard (#79) -- the export must only collect real, rendered
    # person cards, never family-chart's synthetic add/unknown/new-rel slots.
    js_path = Path(__file__).resolve().parent.parent / "static" / "js" / "family_tree.js"
    content = js_path.read_text()
    assert "card-to-add" in content
    assert "card-unknown" in content
    assert "card-new-rel" in content


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
