import datetime
import json

import pytest
from django.urls import reverse

from annuaire.models import Person, Stay

LOGIN_URL = "/annuaire/login/"


# ---------------------------------------------------------------------------
# PlaceListView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_place_list_requires_login(client):
    response = client.get(reverse("place-list"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_place_list_returns_200(auth_client):
    response = auth_client.get(reverse("place-list"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_place_list_context_has_places(auth_client, place):
    response = auth_client.get(reverse("place-list"))
    assert place in response.context["places"]


@pytest.mark.django_db
def test_place_list_context_has_presences_json(auth_client, presence):
    response = auth_client.get(reverse("place-list"))
    data = json.loads(response.context["presences_json"])
    assert any(
        item["person"] == str(presence.person)
        and item["place"] == presence.place.name
        and item["start"] == presence.start_date.isoformat()
        and item["end"] == presence.end_date.isoformat()
        for item in data
    )


@pytest.mark.django_db
def test_place_detail_context_has_presences_json_filtered_to_place(
    auth_client,
    place,
    person,
    other_person,
):
    Stay.objects.create(
        person=person,
        place=place,
        start_date=datetime.date(2026, 7, 1),
        end_date=datetime.date(2026, 7, 5),
    )
    other_place = place.__class__.objects.create(name="Autre", address="X")
    Stay.objects.create(
        person=other_person,
        place=other_place,
        start_date=datetime.date(2026, 8, 1),
        end_date=datetime.date(2026, 8, 5),
    )
    response = auth_client.get(reverse("place-detail", kwargs={"pk": place.pk}))
    data = json.loads(response.context["presences_json"])
    assert all(item["place"] == place.name for item in data)
    assert len(data) == 1


# ---------------------------------------------------------------------------
# PlaceDetailView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_place_detail_requires_login(client, place):
    response = client.get(reverse("place-detail", kwargs={"pk": place.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_place_detail_returns_200(auth_client, place):
    response = auth_client.get(reverse("place-detail", kwargs={"pk": place.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_place_detail_does_not_render_gps_coordinates(auth_client, place):
    response = auth_client.get(reverse("place-detail", kwargs={"pk": place.pk}))
    assert "Coordonnées GPS" not in response.content.decode()


@pytest.mark.django_db
def test_place_detail_404_on_invalid_pk(auth_client):
    response = auth_client.get(reverse("place-detail", kwargs={"pk": 99999}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_place_detail_context_has_future_presences(auth_client, place, presence):
    response = auth_client.get(reverse("place-detail", kwargs={"pk": place.pk}))
    assert presence in response.context["future_presences"]


@pytest.mark.django_db
def test_place_detail_context_has_past_presence(auth_client, place, person):
    past = Stay.objects.create(
        person=person,
        place=place,
        start_date=datetime.date(2025, 1, 1),
        end_date=datetime.date(2025, 1, 14),
    )
    response = auth_client.get(reverse("place-detail", kwargs={"pk": place.pk}))
    assert past in response.context["past_presences"]


@pytest.mark.django_db
def test_place_detail_context_has_current_presence(auth_client, place, person):
    import datetime as dt

    today = dt.date.today()
    current = Stay.objects.create(
        person=person,
        place=place,
        start_date=today - dt.timedelta(days=1),
        end_date=today + dt.timedelta(days=1),
    )
    response = auth_client.get(reverse("place-detail", kwargs={"pk": place.pk}))
    assert current in response.context["current_presences"]


@pytest.mark.django_db
def test_place_detail_context_has_presence_form(auth_client, place):
    response = auth_client.get(reverse("place-detail", kwargs={"pk": place.pk}))
    assert "presence_form" in response.context


# ---------------------------------------------------------------------------
# AddPresenceView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_add_presence_requires_login(client, place):
    response = client.post(reverse("stay-add", kwargs={"pk": place.pk}), {})
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_add_presence_valid_post_creates_and_redirects(auth_client, place, person):
    response = auth_client.post(
        reverse("stay-add", kwargs={"pk": place.pk}),
        {
            "persons": [person.pk],
            "start_date": "2026-08-01",
            "end_date": "2026-08-15",
        },
    )
    assert response.status_code == 302
    assert reverse("place-detail", kwargs={"pk": place.pk}) in response["Location"]
    assert Stay.objects.filter(person=person, place=place).count() == 1


@pytest.mark.django_db
def test_add_presence_creates_one_row_per_person(auth_client, place, person, other_person):
    response = auth_client.post(
        reverse("stay-add", kwargs={"pk": place.pk}),
        {
            "persons": [person.pk, other_person.pk],
            "start_date": "2026-08-01",
            "end_date": "2026-08-15",
        },
    )
    assert response.status_code == 302
    assert Stay.objects.filter(place=place, start_date="2026-08-01").count() == 2


@pytest.mark.django_db
def test_add_presence_invalid_post_redirects_with_error(auth_client, place):
    response = auth_client.post(
        reverse("stay-add", kwargs={"pk": place.pk}),
        {"person": "", "start_date": "", "end_date": ""},
        follow=True,
    )
    assert response.status_code == 200
    messages = list(response.context["messages"])
    assert any("erreur" in str(m).lower() or "présence" in str(m).lower() for m in messages)


# ---------------------------------------------------------------------------
# UpdatePresenceView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_update_presence_requires_login(client, place, presence):
    response = client.get(reverse("stay-edit", kwargs={"pk": place.pk, "stay_pk": presence.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_update_presence_get_returns_200(auth_client, place, presence):
    response = auth_client.get(reverse("stay-edit", kwargs={"pk": place.pk, "stay_pk": presence.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_update_presence_get_prefills_dates(auth_client, place, presence):
    response = auth_client.get(reverse("stay-edit", kwargs={"pk": place.pk, "stay_pk": presence.pk}))
    content = response.content.decode()
    assert f'value="{presence.start_date.isoformat()}"' in content
    assert f'value="{presence.end_date.isoformat()}"' in content


@pytest.mark.django_db
def test_update_presence_invalid_pk_returns_404(auth_client, place):
    response = auth_client.get(reverse("stay-edit", kwargs={"pk": place.pk, "stay_pk": 99999}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_update_presence_post_valid_updates_and_redirects(auth_client, place, presence, person):
    response = auth_client.post(
        reverse("stay-edit", kwargs={"pk": place.pk, "stay_pk": presence.pk}),
        {
            "person": person.pk,
            "start_date": "2026-07-10",
            "end_date": "2026-07-20",
        },
    )
    assert response.status_code == 302
    presence.refresh_from_db()
    assert presence.start_date == datetime.date(2026, 7, 10)


# ---------------------------------------------------------------------------
# DeletePresenceView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_delete_presence_requires_login(client, place, presence):
    response = client.post(reverse("stay-delete", kwargs={"pk": place.pk, "stay_pk": presence.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_delete_presence_get_redirects_to_place(auth_client, place, presence):
    response = auth_client.get(reverse("stay-delete", kwargs={"pk": place.pk, "stay_pk": presence.pk}))
    assert response.status_code == 302
    assert reverse("place-detail", kwargs={"pk": place.pk}) in response["Location"]


@pytest.mark.django_db
def test_delete_presence_post_deletes_and_redirects(auth_client, place, presence):
    response = auth_client.post(reverse("stay-delete", kwargs={"pk": place.pk, "stay_pk": presence.pk}))
    assert response.status_code == 302
    assert not Stay.objects.filter(pk=presence.pk).exists()


@pytest.mark.django_db
def test_delete_presence_invalid_pk_returns_404(auth_client, place):
    response = auth_client.post(reverse("stay-delete", kwargs={"pk": place.pk, "stay_pk": 99999}))
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PlaceCreateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_place_create_requires_login(client):
    response = client.get(reverse("place-create"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_place_create_allowed_for_any_member(auth_client):
    response = auth_client.get(reverse("place-create"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_place_create_redirects_account_without_profile(client, db):
    from annuaire.models import Account

    # A fresh email with no matching Person -- the post-save signal (CLAUDE.md
    # sec. 5) only auto-links when a same-email Person already exists, so this
    # account genuinely has no profile.
    Account.objects.create_user(email="noprofile@example.com", password="testpass123!")
    client.login(username="noprofile@example.com", password="testpass123!")
    response = client.get(reverse("place-create"))
    assert response.status_code == 302
    assert reverse("profile-create") in response["Location"]


@pytest.fixture
def staff_person(staff_account):
    from annuaire.models import Person

    p = Person.objects.create(first_name="Staff", last_name="Member", email=staff_account.email)
    p.account = staff_account
    p.save()
    return p


@pytest.mark.django_db
def test_place_create_get_returns_200(staff_client, staff_person):
    response = staff_client.get(reverse("place-create"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_place_create_form_renders_hidden_coordinate_fields(auth_client):
    # Guard against the address picker silently losing coordinates -- omitting
    # these hidden fields means address_picker.js has nothing to write into.
    response = auth_client.get(reverse("place-create"))
    content = response.content.decode()
    assert 'id="id_latitude"' in content
    assert 'id="id_longitude"' in content


@pytest.mark.django_db
def test_place_create_form_does_not_render_gps_coordinates(auth_client):
    response = auth_client.get(reverse("place-create"))
    assert "Coordonnées GPS" not in response.content.decode()


@pytest.mark.django_db
def test_place_create_post_creates_place(staff_client, staff_person, db):
    from annuaire.models import Place

    response = staff_client.post(
        reverse("place-create"),
        {"name": "Place Nouveau", "address": "Route du Col 12, Verbier"},
    )
    assert response.status_code == 302
    place = Place.objects.get(name="Place Nouveau")
    assert reverse("place-detail", kwargs={"pk": place.pk}) in response["Location"]


@pytest.mark.django_db
def test_place_create_post_invalid_returns_200_with_errors(staff_client, staff_person, db):
    response = staff_client.post(reverse("place-create"), {"name": "", "address": ""})
    assert response.status_code == 200
    assert response.context["form"].errors


@pytest.mark.django_db
def test_place_create_post_auto_assigns_creator_and_additional_owners(auth_client, person, other_person):
    from annuaire.models import Place

    response = auth_client.post(
        reverse("place-create"),
        {"name": "Place Partagé", "address": "Route du Col 12, Verbier", "owners": [other_person.pk]},
    )
    assert response.status_code == 302
    place = Place.objects.get(name="Place Partagé")
    assert set(place.owners.all()) == {person, other_person}


# ---------------------------------------------------------------------------
# PlaceUpdateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_place_update_requires_login(client, place):
    response = client.get(reverse("place-edit", kwargs={"pk": place.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_place_update_non_owner_non_staff_returns_403(auth_client, place):
    response = auth_client.get(reverse("place-edit", kwargs={"pk": place.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_place_update_staff_returns_200(staff_client, place):
    response = staff_client.get(reverse("place-edit", kwargs={"pk": place.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_place_update_owner_returns_200(auth_client, place, person):
    place.owners.add(person)
    response = auth_client.get(reverse("place-edit", kwargs={"pk": place.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_place_update_post_valid_updates_place(staff_client, place):
    response = staff_client.post(
        reverse("place-edit", kwargs={"pk": place.pk}),
        {"name": "Nouveau Nom", "address": place.address},
    )
    assert response.status_code == 302
    place.refresh_from_db()
    assert place.name == "Nouveau Nom"


@pytest.mark.django_db
def test_place_detail_can_edit_place_true_for_staff(staff_client, place):
    response = staff_client.get(reverse("place-detail", kwargs={"pk": place.pk}))
    assert response.context["can_edit_place"] is True


@pytest.mark.django_db
def test_place_detail_can_edit_place_false_for_non_owner(auth_client, place):
    response = auth_client.get(reverse("place-detail", kwargs={"pk": place.pk}))
    assert response.context["can_edit_place"] is False


@pytest.mark.django_db
def test_place_detail_can_edit_place_true_for_owner(auth_client, place, person):
    place.owners.add(person)
    response = auth_client.get(reverse("place-detail", kwargs={"pk": place.pk}))
    assert response.context["can_edit_place"] is True


# ---------------------------------------------------------------------------
# person_search_ajax
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_person_search_requires_login(client):
    response = client.get(reverse("person-search-ajax"), {"q": "ali"})
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_person_search_short_query_returns_empty(auth_client, person):
    response = auth_client.get(reverse("person-search-ajax"), {"q": "a"})
    assert response.status_code == 200
    assert json.loads(response.content) == {"results": []}


@pytest.mark.django_db
def test_person_search_matches_first_name(auth_client, person):
    response = auth_client.get(reverse("person-search-ajax"), {"q": "Ali"})
    data = json.loads(response.content)
    assert any(r["id"] == person.pk for r in data["results"])


@pytest.mark.django_db
def test_person_search_matches_last_name(auth_client, person, other_person):
    response = auth_client.get(reverse("person-search-ajax"), {"q": "Bus"})
    data = json.loads(response.content)
    ids = {r["id"] for r in data["results"]}
    assert person.pk in ids
    assert other_person.pk in ids


@pytest.mark.django_db
def test_person_search_excludes_ids(auth_client, person, other_person):
    response = auth_client.get(
        reverse("person-search-ajax"),
        {"q": "Bus", "exclude": str(person.pk)},
    )
    data = json.loads(response.content)
    ids = {r["id"] for r in data["results"]}
    assert person.pk not in ids
    assert other_person.pk in ids


@pytest.mark.django_db
def test_person_search_limits_to_ten(auth_client, db):
    for i in range(12):
        Person.objects.create(first_name=f"Test{i:02d}", last_name="Search")
    response = auth_client.get(reverse("person-search-ajax"), {"q": "Search"})
    data = json.loads(response.content)
    assert len(data["results"]) == 10


# ---------------------------------------------------------------------------
# PlaceOwnersUpdateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_place_owners_edit_requires_login(client, place):
    response = client.get(reverse("place-owners-edit", kwargs={"pk": place.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_place_owners_edit_forbidden_for_non_owner_non_staff(auth_client, place):
    response = auth_client.get(reverse("place-owners-edit", kwargs={"pk": place.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_place_owners_edit_get_allowed_for_owner(auth_client, place, person):
    place.owners.add(person)
    response = auth_client.get(reverse("place-owners-edit", kwargs={"pk": place.pk}))
    assert response.status_code == 200
    assert response.context["place"] == place


@pytest.mark.django_db
def test_place_owners_edit_get_allowed_for_staff(staff_client, place):
    response = staff_client.get(reverse("place-owners-edit", kwargs={"pk": place.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_place_owners_edit_get_exposes_initial_json(auth_client, place, person, other_person):
    place.owners.add(person)
    place.owners.add(other_person)
    response = auth_client.get(reverse("place-owners-edit", kwargs={"pk": place.pk}))
    data = json.loads(response.context["owners_initial_json"])
    ids = {item["id"] for item in data}
    assert ids == {person.pk, other_person.pk}


@pytest.mark.django_db
def test_place_owners_edit_post_replaces_owners(staff_client, place, person, other_person):
    place.owners.add(person)
    response = staff_client.post(
        reverse("place-owners-edit", kwargs={"pk": place.pk}),
        {"owners": [str(other_person.pk)]},
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("place-detail", kwargs={"pk": place.pk})
    assert list(place.owners.all()) == [other_person]


@pytest.mark.django_db
def test_place_owners_edit_post_empty_clears_owners(staff_client, place, person):
    place.owners.add(person)
    response = staff_client.post(
        reverse("place-owners-edit", kwargs={"pk": place.pk}),
        {},
    )
    assert response.status_code == 302
    assert place.owners.count() == 0


@pytest.mark.django_db
def test_place_owners_edit_post_forbidden_for_non_owner_non_staff(auth_client, place, other_person):
    response = auth_client.post(
        reverse("place-owners-edit", kwargs={"pk": place.pk}),
        {"owners": [str(other_person.pk)]},
    )
    assert response.status_code == 403
    assert place.owners.count() == 0


@pytest.mark.django_db
def test_place_owners_edit_post_allowed_for_owner(auth_client, place, person, other_person):
    place.owners.add(person)
    response = auth_client.post(
        reverse("place-owners-edit", kwargs={"pk": place.pk}),
        {"owners": [str(person.pk), str(other_person.pk)]},
    )
    assert response.status_code == 302
    assert set(place.owners.all()) == {person, other_person}


@pytest.mark.django_db
def test_place_list_heading_names_presences_too(auth_client):
    # #127
    content = auth_client.get(reverse("place-list")).content.decode()
    assert "<h1>Résidences et Présences</h1>" in content


@pytest.mark.django_db
def test_place_list_shows_the_presence_calendar_above_the_place_grid(auth_client, place):
    # #127: the calendar is the reason people open this page, so it comes first.
    content = auth_client.get(reverse("place-list")).content.decode()
    assert content.index("presence-calendar") < content.index("fb-grid--wide")
