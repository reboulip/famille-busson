import pytest
from django.urls import reverse
from django.utils import timezone

from photos.models import PersonTag, Photo

from .conftest import make_uploaded_image


@pytest.mark.django_db
def test_photo_detail_requires_login(client, photo):
    response = client.get(reverse("photo-detail", kwargs={"pk": photo.pk}))
    assert response.status_code == 302


@pytest.mark.django_db
def test_photo_detail_shows_photo(auth_client, photo):
    response = auth_client.get(reverse("photo-detail", kwargs={"pk": photo.pk}))
    assert response.status_code == 200
    assert response.context["photo"] == photo


@pytest.mark.django_db
def test_photo_detail_404s_for_restricted_album(auth_client, restricted_album):
    photo = restricted_album.photos.create(file=make_uploaded_image())
    response = auth_client.get(reverse("photo-detail", kwargs={"pk": photo.pk}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_photo_detail_accessible_for_member(auth_client, account, restricted_album, group):
    account.groups.add(group)
    photo = restricted_album.photos.create(file=make_uploaded_image())
    response = auth_client.get(reverse("photo-detail", kwargs={"pk": photo.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_photo_detail_shows_tagged_persons(auth_client, photo, person):
    PersonTag.objects.create(photo=photo, person=person)
    response = auth_client.get(reverse("photo-detail", kwargs={"pk": photo.pk}))
    assert person in response.context["tagged_persons"]
    assert str(person) in response.content.decode()


@pytest.mark.django_db
def test_photo_detail_can_edit_true_for_uploader(auth_client, photo, person):
    photo.uploaded_by = person
    photo.save()
    response = auth_client.get(reverse("photo-detail", kwargs={"pk": photo.pk}))
    assert response.context["can_edit"] is True


@pytest.mark.django_db
def test_photo_detail_can_edit_false_for_non_uploader(auth_client, photo):
    response = auth_client.get(reverse("photo-detail", kwargs={"pk": photo.pk}))
    assert response.context["can_edit"] is False


@pytest.mark.django_db
def test_photo_detail_shows_next_and_previous(auth_client, album):
    first = Photo.objects.create(album=album, file=make_uploaded_image(), taken_at=timezone.now())
    second = Photo.objects.create(
        album=album, file=make_uploaded_image(), taken_at=timezone.now() - timezone.timedelta(days=1)
    )
    response = auth_client.get(reverse("photo-detail", kwargs={"pk": first.pk}))
    assert response.context["previous_photo"] is None
    assert response.context["next_photo"] == second


@pytest.mark.django_db
def test_photo_edit_by_uploader_succeeds(auth_client, photo, person):
    photo.uploaded_by = person
    photo.save()
    response = auth_client.post(reverse("photo-edit", kwargs={"pk": photo.pk}), {"caption": "Nouvelle légende"})
    assert response.status_code == 302
    photo.refresh_from_db()
    assert photo.caption == "Nouvelle légende"


@pytest.mark.django_db
def test_photo_edit_by_non_uploader_is_forbidden(auth_client, photo):
    response = auth_client.post(reverse("photo-edit", kwargs={"pk": photo.pk}), {"caption": "Nouvelle légende"})
    assert response.status_code == 403


@pytest.mark.django_db
def test_photo_edit_by_staff_succeeds(staff_client, photo):
    response = staff_client.post(reverse("photo-edit", kwargs={"pk": photo.pk}), {"caption": "Nouvelle légende"})
    assert response.status_code == 302


@pytest.mark.django_db
def test_photo_delete_by_uploader_succeeds(auth_client, photo, person):
    photo.uploaded_by = person
    photo.save()
    response = auth_client.post(reverse("photo-delete", kwargs={"pk": photo.pk}))
    assert response.status_code == 302
    assert not Photo.objects.filter(pk=photo.pk).exists()


@pytest.mark.django_db
def test_photo_delete_by_non_uploader_is_forbidden(auth_client, photo):
    response = auth_client.post(reverse("photo-delete", kwargs={"pk": photo.pk}))
    assert response.status_code == 403
    assert Photo.objects.filter(pk=photo.pk).exists()


@pytest.mark.django_db
def test_photo_delete_redirects_to_album(staff_client, photo):
    response = staff_client.post(reverse("photo-delete", kwargs={"pk": photo.pk}))
    assert response.url == reverse("album-detail", kwargs={"pk": photo.album_id})
