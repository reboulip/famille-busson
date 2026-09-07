"""'Il y a X ans' widget logic (10.10).

`memories()` takes `today` as a parameter precisely so these can pin a fixed
date instead of depending on the day the suite runs -- mirrors
test_birthdays.py's idiom.
"""

import datetime
import io

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from annuaire.memories import memories
from photos.models import Album, Photo
from publications.models import BlogPost


def _uploaded_image():
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="blue").save(buffer, format="PNG")
    return SimpleUploadedFile(name="photo.png", content=buffer.getvalue(), content_type="image/png")


def _aware(*args):
    return timezone.make_aware(datetime.datetime(*args), datetime.UTC)


@pytest.mark.django_db
def test_photo_from_same_date_earlier_year_is_included(account):
    today = datetime.date(2026, 6, 10)
    album = Album.objects.create(title="Album")
    photo = Photo.objects.create(album=album, file=_uploaded_image(), taken_at=_aware(2020, 6, 10, 12, 0))

    results = memories(today, account)
    assert len(results) == 1
    assert results[0].kind == "photo"
    assert results[0].item == photo
    assert results[0].years_ago == 6


@pytest.mark.django_db
def test_photo_from_a_different_date_is_excluded(account):
    today = datetime.date(2026, 6, 10)
    album = Album.objects.create(title="Album")
    Photo.objects.create(album=album, file=_uploaded_image(), taken_at=_aware(2020, 6, 11, 12, 0))

    assert memories(today, account) == []


@pytest.mark.django_db
def test_photo_in_restricted_album_is_excluded_for_non_member(account):
    today = datetime.date(2026, 6, 10)
    group = Group.objects.create(name="SCI")
    album = Album.objects.create(title="Album privé")
    album.groups.add(group)
    Photo.objects.create(album=album, file=_uploaded_image(), taken_at=_aware(2020, 6, 10, 12, 0))

    assert memories(today, account) == []


@pytest.mark.django_db
def test_photo_in_restricted_album_is_included_for_member(account):
    today = datetime.date(2026, 6, 10)
    group = Group.objects.create(name="SCI")
    account.groups.add(group)
    album = Album.objects.create(title="Album privé")
    album.groups.add(group)
    photo = Photo.objects.create(album=album, file=_uploaded_image(), taken_at=_aware(2020, 6, 10, 12, 0))

    results = memories(today, account)
    assert [entry.item for entry in results] == [photo]


@pytest.mark.django_db
def test_post_from_same_date_earlier_year_is_included(account):
    today = datetime.date(2026, 6, 10)
    post = BlogPost.objects.create(title="Souvenir", body="Contenu.")
    BlogPost.objects.filter(pk=post.pk).update(created_at=_aware(2022, 6, 10, 9, 0))
    post.refresh_from_db()

    results = memories(today, account)
    assert len(results) == 1
    assert results[0].kind == "post"
    assert results[0].item == post
    assert results[0].years_ago == 4


@pytest.mark.django_db
def test_results_are_sorted_most_recent_anniversary_first(account):
    today = datetime.date(2026, 6, 10)
    album = Album.objects.create(title="Album")
    older = Photo.objects.create(album=album, file=_uploaded_image(), taken_at=_aware(2015, 6, 10, 12, 0))
    newer = Photo.objects.create(album=album, file=_uploaded_image(), taken_at=_aware(2024, 6, 10, 12, 0))

    results = memories(today, account)
    assert [entry.item for entry in results] == [newer, older]


@pytest.mark.django_db
def test_results_are_capped_at_limit(account):
    today = datetime.date(2026, 6, 10)
    album = Album.objects.create(title="Album")
    for year in (2015, 2016, 2017, 2018):
        Photo.objects.create(album=album, file=_uploaded_image(), taken_at=_aware(year, 6, 10, 12, 0))

    assert len(memories(today, account, limit=2)) == 2


@pytest.mark.django_db
def test_no_matches_returns_empty_list(account):
    today = datetime.date(2026, 6, 10)
    assert memories(today, account) == []


@pytest.mark.django_db
def test_home_context_has_memories(auth_client):
    response = auth_client.get(reverse("home"))
    assert "memories" in response.context
