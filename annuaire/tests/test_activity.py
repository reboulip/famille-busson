"""11.5 -- activity feed aggregation logic."""

import datetime
import io

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from annuaire.activity import activity_since
from annuaire.models import Person
from documents.models import Category, Document
from photos.models import Album, Photo
from publications.models import BlogPost, Comment


def _uploaded_image():
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="blue").save(buffer, format="PNG")
    return SimpleUploadedFile(name="photo.png", content=buffer.getvalue(), content_type="image/png")


def _aware(*args):
    return timezone.make_aware(datetime.datetime(*args), datetime.UTC)


@pytest.mark.django_db
def test_new_post_is_included(person):
    post = BlogPost.objects.create(title="Nouvelle", body="x")
    post.authors.add(person)
    cutoff = timezone.now() - datetime.timedelta(days=1)

    entries = activity_since(person.account, cutoff)

    assert any(e.kind == "post" and e.item == post for e in entries)


@pytest.mark.django_db
def test_post_before_cutoff_is_excluded(person):
    post = BlogPost.objects.create(title="Ancienne", body="x")
    post.authors.add(person)
    BlogPost.objects.filter(pk=post.pk).update(created_at=_aware(2020, 1, 1))
    cutoff = timezone.now() - datetime.timedelta(days=1)

    entries = activity_since(person.account, cutoff)

    assert not any(e.kind == "post" and e.item == post for e in entries)


@pytest.mark.django_db
def test_new_comment_is_included(person):
    post = BlogPost.objects.create(title="Un billet", body="x")
    post.authors.add(person)
    comment = Comment.objects.create(post=post, author=person, body="Bien dit")
    cutoff = timezone.now() - datetime.timedelta(days=1)

    entries = activity_since(person.account, cutoff)

    assert any(e.kind == "comment" and e.item == comment for e in entries)


@pytest.mark.django_db
def test_document_in_locked_category_is_excluded(person):
    group = Group.objects.create(name="SCI grand chalet")
    category = Category.objects.create(name="Réservé")
    category.groups.add(group)
    Document.objects.create(title="Secret", category=category)
    cutoff = timezone.now() - datetime.timedelta(days=1)

    entries = activity_since(person.account, cutoff)

    assert not any(e.kind == "document" for e in entries)


@pytest.mark.django_db
def test_document_in_open_category_is_included(person):
    category = Category.objects.create(name="Actes")
    document = Document.objects.create(title="Acte", category=category)
    cutoff = timezone.now() - datetime.timedelta(days=1)

    entries = activity_since(person.account, cutoff)

    assert any(e.kind == "document" and e.item == document for e in entries)


@pytest.mark.django_db
def test_photos_aggregate_per_album_not_per_photo(person):
    album = Album.objects.create(title="Été")
    for _ in range(3):
        Photo.objects.create(album=album, file=_uploaded_image())
    cutoff = timezone.now() - datetime.timedelta(days=1)

    entries = activity_since(person.account, cutoff)

    album_entries = [e for e in entries if e.kind == "album_photos"]
    assert len(album_entries) == 1
    assert album_entries[0].item == album
    assert album_entries[0].count == 3


@pytest.mark.django_db
def test_album_restricted_to_another_group_is_excluded(person):
    group = Group.objects.create(name="SCI grand chalet")
    album = Album.objects.create(title="Privé")
    album.groups.add(group)
    Photo.objects.create(album=album, file=_uploaded_image())
    cutoff = timezone.now() - datetime.timedelta(days=1)

    entries = activity_since(person.account, cutoff)

    assert not any(e.kind == "album_photos" for e in entries)


@pytest.mark.django_db
def test_new_member_is_included(person):
    new_person = Person.objects.create(first_name="Bob", last_name="Busson")
    cutoff = timezone.now() - datetime.timedelta(days=1)

    entries = activity_since(person.account, cutoff)

    assert any(e.kind == "member" and e.item == new_person for e in entries)


@pytest.mark.django_db
def test_member_created_before_cutoff_is_excluded(person):
    other = Person.objects.create(first_name="Bob", last_name="Busson")
    Person.objects.filter(pk=other.pk).update(created_at=_aware(2020, 1, 1))
    cutoff = timezone.now() - datetime.timedelta(days=1)

    entries = activity_since(person.account, cutoff)

    assert not any(e.kind == "member" and e.item == other for e in entries)


@pytest.mark.django_db
def test_since_none_returns_full_history(person):
    other = Person.objects.create(first_name="Bob", last_name="Busson")
    Person.objects.filter(pk=other.pk).update(created_at=_aware(2020, 1, 1))

    entries = activity_since(person.account, None)

    assert any(e.kind == "member" and e.item == other for e in entries)


@pytest.mark.django_db
def test_viewer_own_profile_is_excluded_from_their_own_feed(person):
    entries = activity_since(person.account, None)

    assert not any(e.kind == "member" and e.item == person for e in entries)


@pytest.mark.django_db
def test_results_are_sorted_most_recent_first(person):
    older = BlogPost.objects.create(title="Ancienne", body="x")
    older.authors.add(person)
    BlogPost.objects.filter(pk=older.pk).update(created_at=_aware(2024, 1, 1))
    newer = BlogPost.objects.create(title="Récente", body="y")
    newer.authors.add(person)
    BlogPost.objects.filter(pk=newer.pk).update(created_at=_aware(2024, 6, 1))

    entries = activity_since(person.account, None, limit=50)

    post_entries = [e.item for e in entries if e.kind == "post"]
    assert post_entries.index(newer) < post_entries.index(older)


@pytest.mark.django_db
def test_results_are_capped_at_limit(person):
    for i in range(5):
        post = BlogPost.objects.create(title=f"Post {i}", body="x")
        post.authors.add(person)

    entries = activity_since(person.account, None, limit=2)

    assert len(entries) == 2


@pytest.mark.django_db
def test_no_activity_returns_empty_list(person):
    cutoff = timezone.now() + datetime.timedelta(days=1)

    entries = activity_since(person.account, cutoff)

    assert entries == []
