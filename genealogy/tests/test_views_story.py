import pytest
from django.urls import reverse

from genealogy.models import Story, StoryPhoto


@pytest.mark.django_db
def test_story_tab_requires_login(client, person):
    response = client.get(reverse("personne-detail", kwargs={"pk": person.pk}) + "?tab=histoire")
    assert response.status_code == 302


@pytest.mark.django_db
def test_story_tab_lists_stories(auth_client, person, story):
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}) + "?tab=histoire")
    assert response.status_code == 200
    assert story.title in response.content.decode()


@pytest.mark.django_db
def test_story_create_requires_login(client, person):
    response = client.get(reverse("story-create", kwargs={"person_pk": person.pk}))
    assert response.status_code == 302


@pytest.mark.django_db
def test_story_create_get_200(auth_client, person):
    response = auth_client.get(reverse("story-create", kwargs={"person_pk": person.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_story_create_post_creates_story_owned_by_author(auth_client, person, account):
    response = auth_client.post(
        reverse("story-create", kwargs={"person_pk": person.pk}),
        {"title": "Un été à la campagne", "body": "Il faisait beau.", "date": "1995-07-01"},
    )
    assert response.status_code == 302
    story = Story.objects.get(title="Un été à la campagne")
    assert story.person == person
    assert story.created_by == account.profile


@pytest.mark.django_db
def test_story_create_any_member_can_create_for_another_person(auth_client, other_person):
    response = auth_client.post(
        reverse("story-create", kwargs={"person_pk": other_person.pk}),
        {"title": "Récit sur Bob", "body": "", "date": ""},
    )
    assert response.status_code == 302
    assert Story.objects.filter(title="Récit sur Bob", person=other_person).exists()


@pytest.mark.django_db
def test_story_create_links_selected_photos_in_order(auth_client, person, photo, album):
    from photos.models import Photo

    second_photo = Photo.objects.create(album=album, file=photo.file)
    response = auth_client.post(
        reverse("story-create", kwargs={"person_pk": person.pk}),
        {"title": "Avec photos", "body": "", "date": "", "photos": [str(second_photo.pk), str(photo.pk)]},
    )
    assert response.status_code == 302
    created = Story.objects.get(title="Avec photos")
    ordered = list(StoryPhoto.objects.filter(story=created).order_by("order").values_list("photo_id", flat=True))
    assert ordered == [second_photo.pk, photo.pk]


@pytest.mark.django_db
def test_story_update_requires_owner_or_staff(auth_client, other_person, account):
    story = Story.objects.create(person=other_person, title="Récit de Bob", created_by=None)
    response = auth_client.post(
        reverse("story-update", kwargs={"pk": story.pk}), {"title": "Modifié", "body": "", "date": "", "end_date": ""}
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_story_update_get_200_and_prefills_linked_photos(auth_client, person, account, photo):
    story = Story.objects.create(person=person, title="Mon récit", created_by=account.profile)
    StoryPhoto.objects.create(story=story, photo=photo)
    response = auth_client.get(reverse("story-update", kwargs={"pk": story.pk}))
    assert response.status_code == 200
    assert str(photo.pk) in response.content.decode()


@pytest.mark.django_db
def test_story_update_reorders_existing_photo_links(auth_client, person, account, album, photo):
    from photos.models import Photo

    story = Story.objects.create(person=person, title="Mon récit", created_by=account.profile)
    second_photo = Photo.objects.create(album=album, file=photo.file)
    StoryPhoto.objects.create(story=story, photo=photo, order=0)
    StoryPhoto.objects.create(story=story, photo=second_photo, order=1)

    response = auth_client.post(
        reverse("story-update", kwargs={"pk": story.pk}),
        {
            "title": "Mon récit",
            "body": "",
            "date": "",
            "end_date": "",
            "photos": [str(second_photo.pk), str(photo.pk)],
        },
    )
    assert response.status_code == 302
    ordered = list(StoryPhoto.objects.filter(story=story).order_by("order").values_list("photo_id", flat=True))
    assert ordered == [second_photo.pk, photo.pk]


@pytest.mark.django_db
def test_story_update_allowed_for_author(auth_client, person, account):
    story = Story.objects.create(person=person, title="Mon récit", created_by=account.profile)
    response = auth_client.post(
        reverse("story-update", kwargs={"pk": story.pk}),
        {"title": "Mon récit modifié", "body": "", "date": "", "end_date": ""},
    )
    assert response.status_code == 302
    story.refresh_from_db()
    assert story.title == "Mon récit modifié"


@pytest.mark.django_db
def test_story_update_allowed_for_staff(staff_client, other_person):
    story = Story.objects.create(person=other_person, title="Récit de Bob")
    response = staff_client.post(
        reverse("story-update", kwargs={"pk": story.pk}),
        {"title": "Corrigé par le staff", "body": "", "date": "", "end_date": ""},
    )
    assert response.status_code == 302
    story.refresh_from_db()
    assert story.title == "Corrigé par le staff"


@pytest.mark.django_db
def test_story_delete_requires_owner_or_staff(auth_client, other_person):
    story = Story.objects.create(person=other_person, title="Récit de Bob")
    response = auth_client.post(reverse("story-delete", kwargs={"pk": story.pk}))
    assert response.status_code == 403
    assert Story.objects.filter(pk=story.pk).exists()


@pytest.mark.django_db
def test_story_delete_allowed_for_author(auth_client, person, account):
    story = Story.objects.create(person=person, title="Mon récit", created_by=account.profile)
    response = auth_client.post(reverse("story-delete", kwargs={"pk": story.pk}))
    assert response.status_code == 302
    assert not Story.objects.filter(pk=story.pk).exists()


@pytest.mark.django_db
def test_story_tab_only_shows_accessible_photos(auth_client, person, album, photo):
    from django.contrib.auth.models import Group

    story = Story.objects.create(person=person, title="Avec une photo restreinte")
    restricted_album = album
    group = Group.objects.create(name="Groupe restreint")
    restricted_album.groups.add(group)
    StoryPhoto.objects.create(story=story, photo=photo)

    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}) + "?tab=histoire")
    assert response.status_code == 200
    assert reverse("photo-detail", kwargs={"pk": photo.pk}) not in response.content.decode()


@pytest.mark.django_db
def test_edit_actions_hidden_for_non_owner(auth_client, other_person):
    story = Story.objects.create(person=other_person, title="Récit de Bob")
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": other_person.pk}) + "?tab=histoire")
    content = response.content.decode()
    assert story.title in content
    assert reverse("story-update", kwargs={"pk": story.pk}) not in content
