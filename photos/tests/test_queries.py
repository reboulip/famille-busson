import pytest
from django.utils import timezone

from photos.models import Photo
from photos.queries import neighbours

from .conftest import make_uploaded_image


@pytest.mark.django_db
def test_neighbours_middle_photo(album):
    now = timezone.now()
    first = Photo.objects.create(album=album, file=make_uploaded_image(), taken_at=now)
    middle = Photo.objects.create(album=album, file=make_uploaded_image(), taken_at=now - timezone.timedelta(days=1))
    last = Photo.objects.create(album=album, file=make_uploaded_image(), taken_at=now - timezone.timedelta(days=2))

    previous_photo, next_photo = neighbours(middle)
    assert previous_photo == first
    assert next_photo == last


@pytest.mark.django_db
def test_neighbours_first_photo_has_no_previous(album):
    now = timezone.now()
    first = Photo.objects.create(album=album, file=make_uploaded_image(), taken_at=now)
    Photo.objects.create(album=album, file=make_uploaded_image(), taken_at=now - timezone.timedelta(days=1))

    previous_photo, next_photo = neighbours(first)
    assert previous_photo is None
    assert next_photo is not None


@pytest.mark.django_db
def test_neighbours_last_photo_has_no_next(album):
    now = timezone.now()
    Photo.objects.create(album=album, file=make_uploaded_image(), taken_at=now)
    last = Photo.objects.create(album=album, file=make_uploaded_image(), taken_at=now - timezone.timedelta(days=1))

    previous_photo, next_photo = neighbours(last)
    assert previous_photo is not None
    assert next_photo is None


@pytest.mark.django_db
def test_neighbours_only_photo_has_neither(album):
    only = Photo.objects.create(album=album, file=make_uploaded_image())
    previous_photo, next_photo = neighbours(only)
    assert previous_photo is None
    assert next_photo is None
