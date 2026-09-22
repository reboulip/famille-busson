import pytest

from photos.models import Album, Photo

from .conftest import make_uploaded_image


@pytest.mark.django_db
def test_forward_fk_resolves_to_a_trashed_parent(album, account):
    photo = Photo.objects.create(album=album, file=make_uploaded_image())
    album.soft_delete(account)
    photo.refresh_from_db()
    assert photo.album == album


@pytest.mark.django_db
def test_trashing_an_album_does_not_soft_delete_its_photos(album, account):
    photo = Photo.objects.create(album=album, file=make_uploaded_image())
    album.soft_delete(account)
    assert Photo.objects.filter(pk=photo.pk).exists()


@pytest.mark.django_db
def test_trashed_album_excluded_from_default_manager(album, account):
    album.soft_delete(account)
    assert not Album.objects.filter(pk=album.pk).exists()
    assert Album.all_objects.filter(pk=album.pk).exists()


@pytest.mark.django_db
def test_photo_manager_chronological_filters_trashed(album, account):
    photo = Photo.objects.create(album=album, file=make_uploaded_image())
    photo.soft_delete(account)
    assert photo not in list(Photo.objects.chronological())
    assert Photo.all_objects.filter(pk=photo.pk).exists()
