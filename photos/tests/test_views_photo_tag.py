import pytest
from django.urls import reverse

from photos.models import PersonTag

from .conftest import make_uploaded_image


@pytest.mark.django_db
def test_tag_page_requires_login(client, photo):
    response = client.get(reverse("photo-tag", kwargs={"pk": photo.pk}))
    assert response.status_code == 302


@pytest.mark.django_db
def test_tag_page_forbidden_for_restricted_album(auth_client, restricted_album):
    photo = restricted_album.photos.create(file=make_uploaded_image())
    response = auth_client.get(reverse("photo-tag", kwargs={"pk": photo.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_tag_page_shows_existing_tags(auth_client, photo, person):
    PersonTag.objects.create(photo=photo, person=person)
    response = auth_client.get(reverse("photo-tag", kwargs={"pk": photo.pk}))
    assert response.status_code == 200
    assert str(person) in response.context["tagged_persons_initial_json"]


@pytest.mark.django_db
def test_post_adds_new_tags(auth_client, photo, person, other_person):
    response = auth_client.post(
        reverse("photo-tag", kwargs={"pk": photo.pk}),
        {"persons": [str(person.pk), str(other_person.pk)]},
    )
    assert response.status_code == 302
    assert set(photo.person_tags.values_list("person_id", flat=True)) == {person.pk, other_person.pk}


@pytest.mark.django_db
def test_post_records_tagged_by(auth_client, photo, person, account):
    auth_client.post(reverse("photo-tag", kwargs={"pk": photo.pk}), {"persons": [str(person.pk)]})
    tag = PersonTag.objects.get(photo=photo, person=person)
    assert tag.tagged_by_id == account.profile.pk


@pytest.mark.django_db
def test_post_removes_deselected_tags(auth_client, photo, person, other_person):
    PersonTag.objects.create(photo=photo, person=person)
    PersonTag.objects.create(photo=photo, person=other_person)

    response = auth_client.post(reverse("photo-tag", kwargs={"pk": photo.pk}), {"persons": [str(person.pk)]})

    assert response.status_code == 302
    assert set(photo.person_tags.values_list("person_id", flat=True)) == {person.pk}


@pytest.mark.django_db
def test_post_with_no_persons_clears_all_tags(auth_client, photo, person):
    PersonTag.objects.create(photo=photo, person=person)
    auth_client.post(reverse("photo-tag", kwargs={"pk": photo.pk}), {})
    assert not photo.person_tags.exists()


@pytest.mark.django_db
def test_member_of_restricted_album_can_tag(auth_client, account, restricted_album, group, person):
    account.groups.add(group)
    photo = restricted_album.photos.create(file=make_uploaded_image())
    response = auth_client.post(reverse("photo-tag", kwargs={"pk": photo.pk}), {"persons": [str(person.pk)]})
    assert response.status_code == 302
    assert photo.person_tags.filter(person=person).exists()
