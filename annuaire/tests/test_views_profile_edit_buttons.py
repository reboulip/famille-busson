import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_edit_profile_shows_save_button_twice(auth_client, person):
    response = auth_client.get(reverse("person-edit", kwargs={"pk": person.pk}))
    content = response.content.decode()
    assert content.count("Enregistrer") == 2


@pytest.mark.django_db
def test_edit_profile_shows_modifier_relations_twice(auth_client, person):
    response = auth_client.get(reverse("person-edit", kwargs={"pk": person.pk}))
    content = response.content.decode()
    assert content.count("Modifier les relations") == 2


@pytest.mark.django_db
def test_edit_profile_shows_cancel_button_twice(auth_client, person):
    response = auth_client.get(reverse("person-edit", kwargs={"pk": person.pk}))
    content = response.content.decode()
    assert content.count("Annuler") == 2


@pytest.mark.django_db
def test_edit_profile_cancel_links_to_profile_detail(auth_client, person):
    response = auth_client.get(reverse("person-edit", kwargs={"pk": person.pk}))
    content = response.content.decode()
    detail_url = reverse("personne-detail", kwargs={"pk": person.pk})
    assert content.count(f'href="{detail_url}"') == 2


@pytest.mark.django_db
def test_edit_profile_cancel_is_a_link_not_a_button(auth_client, person):
    response = auth_client.get(reverse("person-edit", kwargs={"pk": person.pk}))
    content = response.content.decode()
    detail_url = reverse("personne-detail", kwargs={"pk": person.pk})
    assert f'<a href="{detail_url}"' in content


@pytest.mark.django_db
def test_edit_profile_top_actions_render_before_the_form_fields(auth_client, person):
    response = auth_client.get(reverse("person-edit", kwargs={"pk": person.pk}))
    content = response.content.decode()
    first_save = content.find("Enregistrer")
    first_fieldset = content.find("<fieldset")
    assert 0 <= first_save < first_fieldset
