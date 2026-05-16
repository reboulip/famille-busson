import datetime
import pytest
from django.urls import reverse
from annuaire.models import PresencePSV


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
def test_chalet_detail_context_has_presences(auth_client, chalet, presence):
    response = auth_client.get(reverse("chalet-detail", kwargs={"pk": chalet.pk}))
    assert presence in response.context["presences"]


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
            "person": person.pk,
            "start_date": "2026-08-01",
            "end_date": "2026-08-15",
        },
    )
    assert response.status_code == 302
    assert reverse("chalet-detail", kwargs={"pk": chalet.pk}) in response["Location"]
    assert PresencePSV.objects.filter(person=person, chalet=chalet).exists()


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
