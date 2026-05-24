import datetime
import json
import pytest
from django.urls import reverse
from annuaire.models import Person, PresencePSV


LOGIN_URL = "/annuaire/login/"


# ---------------------------------------------------------------------------
# ChaletListView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_chalet_list_requires_login(client):
    response = client.get(reverse("chalet-list"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_chalet_list_returns_200(auth_client):
    response = auth_client.get(reverse("chalet-list"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_chalet_list_context_has_chalets(auth_client, chalet):
    response = auth_client.get(reverse("chalet-list"))
    assert chalet in response.context["chalets"]


# ---------------------------------------------------------------------------
# ChaletDetailView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_chalet_detail_requires_login(client, chalet):
    response = client.get(reverse("chalet-detail", kwargs={"pk": chalet.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_chalet_detail_returns_200(auth_client, chalet):
    response = auth_client.get(reverse("chalet-detail", kwargs={"pk": chalet.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_chalet_detail_404_on_invalid_pk(auth_client):
    response = auth_client.get(reverse("chalet-detail", kwargs={"pk": 99999}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_chalet_detail_context_has_future_presences(auth_client, chalet, presence):
    response = auth_client.get(reverse("chalet-detail", kwargs={"pk": chalet.pk}))
    assert presence in response.context["future_presences"]


@pytest.mark.django_db
def test_chalet_detail_context_has_past_presence(auth_client, chalet, person):
    past = PresencePSV.objects.create(
        person=person, chalet=chalet,
        start_date=datetime.date(2025, 1, 1),
        end_date=datetime.date(2025, 1, 14),
    )
    response = auth_client.get(reverse("chalet-detail", kwargs={"pk": chalet.pk}))
    assert past in response.context["past_presences"]


@pytest.mark.django_db
def test_chalet_detail_context_has_current_presence(auth_client, chalet, person):
    import datetime as dt
    today = dt.date.today()
    current = PresencePSV.objects.create(
        person=person, chalet=chalet,
        start_date=today - dt.timedelta(days=1),
        end_date=today + dt.timedelta(days=1),
    )
    response = auth_client.get(reverse("chalet-detail", kwargs={"pk": chalet.pk}))
    assert current in response.context["current_presences"]


@pytest.mark.django_db
def test_chalet_detail_context_has_presence_form(auth_client, chalet):
    response = auth_client.get(reverse("chalet-detail", kwargs={"pk": chalet.pk}))
    assert "presence_form" in response.context


# ---------------------------------------------------------------------------
# AddPresenceView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_add_presence_requires_login(client, chalet):
    response = client.post(reverse("presence-add", kwargs={"pk": chalet.pk}), {})
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_add_presence_valid_post_creates_and_redirects(auth_client, chalet, person):
    response = auth_client.post(
        reverse("presence-add", kwargs={"pk": chalet.pk}),
        {
            "persons": [person.pk],
            "start_date": "2026-08-01",
            "end_date": "2026-08-15",
        },
    )
    assert response.status_code == 302
    assert reverse("chalet-detail", kwargs={"pk": chalet.pk}) in response["Location"]
    assert PresencePSV.objects.filter(person=person, chalet=chalet).count() == 1


@pytest.mark.django_db
def test_add_presence_creates_one_row_per_person(auth_client, chalet, person, other_person):
    response = auth_client.post(
        reverse("presence-add", kwargs={"pk": chalet.pk}),
        {
            "persons": [person.pk, other_person.pk],
            "start_date": "2026-08-01",
            "end_date": "2026-08-15",
        },
    )
    assert response.status_code == 302
    assert PresencePSV.objects.filter(chalet=chalet, start_date="2026-08-01").count() == 2


@pytest.mark.django_db
def test_add_presence_invalid_post_redirects_with_error(auth_client, chalet):
    response = auth_client.post(
        reverse("presence-add", kwargs={"pk": chalet.pk}),
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
def test_update_presence_requires_login(client, chalet, presence):
    response = client.get(
        reverse("presence-edit", kwargs={"pk": chalet.pk, "presence_pk": presence.pk})
    )
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_update_presence_get_returns_200(auth_client, chalet, presence):
    response = auth_client.get(
        reverse("presence-edit", kwargs={"pk": chalet.pk, "presence_pk": presence.pk})
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_update_presence_get_prefills_dates(auth_client, chalet, presence):
    response = auth_client.get(
        reverse("presence-edit", kwargs={"pk": chalet.pk, "presence_pk": presence.pk})
    )
    content = response.content.decode()
    assert 'value="2026-07-01"' in content
    assert 'value="2026-07-14"' in content


@pytest.mark.django_db
def test_update_presence_invalid_pk_returns_404(auth_client, chalet):
    response = auth_client.get(
        reverse("presence-edit", kwargs={"pk": chalet.pk, "presence_pk": 99999})
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_update_presence_post_valid_updates_and_redirects(auth_client, chalet, presence, person):
    response = auth_client.post(
        reverse("presence-edit", kwargs={"pk": chalet.pk, "presence_pk": presence.pk}),
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
def test_delete_presence_requires_login(client, chalet, presence):
    response = client.post(
        reverse("presence-delete", kwargs={"pk": chalet.pk, "presence_pk": presence.pk})
    )
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_delete_presence_get_redirects_to_chalet(auth_client, chalet, presence):
    response = auth_client.get(
        reverse("presence-delete", kwargs={"pk": chalet.pk, "presence_pk": presence.pk})
    )
    assert response.status_code == 302
    assert reverse("chalet-detail", kwargs={"pk": chalet.pk}) in response["Location"]


@pytest.mark.django_db
def test_delete_presence_post_deletes_and_redirects(auth_client, chalet, presence):
    response = auth_client.post(
        reverse("presence-delete", kwargs={"pk": chalet.pk, "presence_pk": presence.pk})
    )
    assert response.status_code == 302
    assert not PresencePSV.objects.filter(pk=presence.pk).exists()


@pytest.mark.django_db
def test_delete_presence_invalid_pk_returns_404(auth_client, chalet):
    response = auth_client.post(
        reverse("presence-delete", kwargs={"pk": chalet.pk, "presence_pk": 99999})
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# ChaletCreateView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_chalet_create_requires_login(client):
    response = client.get(reverse("chalet-create"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_chalet_create_requires_staff(auth_client):
    response = auth_client.get(reverse("chalet-create"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_chalet_create_get_returns_200(staff_client):
    response = staff_client.get(reverse("chalet-create"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_chalet_create_post_creates_chalet(staff_client, db):
    from annuaire.models import Chalet
    response = staff_client.post(
        reverse("chalet-create"),
        {"name": "Chalet Nouveau", "address": "Route du Col 12, Verbier"},
    )
    assert response.status_code == 302
    chalet = Chalet.objects.get(name="Chalet Nouveau")
    assert reverse("chalet-detail", kwargs={"pk": chalet.pk}) in response["Location"]


@pytest.mark.django_db
def test_chalet_create_post_invalid_returns_200_with_errors(staff_client, db):
    response = staff_client.post(reverse("chalet-create"), {"name": "", "address": ""})
    assert response.status_code == 200
    assert response.context["form"].errors


# ---------------------------------------------------------------------------
# ChaletUpdateView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_chalet_update_requires_login(client, chalet):
    response = client.get(reverse("chalet-edit", kwargs={"pk": chalet.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_chalet_update_non_owner_non_staff_returns_403(auth_client, chalet):
    response = auth_client.get(reverse("chalet-edit", kwargs={"pk": chalet.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_chalet_update_staff_returns_200(staff_client, chalet):
    response = staff_client.get(reverse("chalet-edit", kwargs={"pk": chalet.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_chalet_update_owner_returns_200(auth_client, chalet, person):
    chalet.owners.add(person)
    response = auth_client.get(reverse("chalet-edit", kwargs={"pk": chalet.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_chalet_update_post_valid_updates_chalet(staff_client, chalet):
    response = staff_client.post(
        reverse("chalet-edit", kwargs={"pk": chalet.pk}),
        {"name": "Nouveau Nom", "address": chalet.address},
    )
    assert response.status_code == 302
    chalet.refresh_from_db()
    assert chalet.name == "Nouveau Nom"


@pytest.mark.django_db
def test_chalet_detail_can_edit_chalet_true_for_staff(staff_client, chalet):
    response = staff_client.get(reverse("chalet-detail", kwargs={"pk": chalet.pk}))
    assert response.context["can_edit_chalet"] is True


@pytest.mark.django_db
def test_chalet_detail_can_edit_chalet_false_for_non_owner(auth_client, chalet):
    response = auth_client.get(reverse("chalet-detail", kwargs={"pk": chalet.pk}))
    assert response.context["can_edit_chalet"] is False


@pytest.mark.django_db
def test_chalet_detail_can_edit_chalet_true_for_owner(auth_client, chalet, person):
    chalet.owners.add(person)
    response = auth_client.get(reverse("chalet-detail", kwargs={"pk": chalet.pk}))
    assert response.context["can_edit_chalet"] is True


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
