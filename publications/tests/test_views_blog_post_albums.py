"""10.9 — linking a publication to an album."""

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from photos.models import Album
from publications.forms import BlogPostForm
from publications.models import BlogPost


@pytest.fixture
def album(db):
    return Album.objects.create(title="Été 2025")


@pytest.fixture
def restricted_group(db):
    return Group.objects.create(name="SCI grand chalet")


@pytest.fixture
def restricted_album(db, restricted_group):
    album = Album.objects.create(title="Album restreint")
    album.groups.add(restricted_group)
    return album


def _post_data(**overrides):
    data = {
        "title": "Un billet",
        "post_type": "NORMAL",
        "body": "Contenu.",
        "authors": [],
        "attachments-TOTAL_FORMS": "0",
        "attachments-INITIAL_FORMS": "0",
        "attachments-MIN_NUM_FORMS": "0",
        "attachments-MAX_NUM_FORMS": "1000",
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Form-level security boundary
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_form_albums_queryset_is_empty_without_a_user():
    form = BlogPostForm()
    assert list(form.fields["albums"].queryset) == []


@pytest.mark.django_db
def test_form_albums_queryset_excludes_restricted_albums(person, album, restricted_album):
    form = BlogPostForm(user=person.account, current_person=person)
    queryset = form.fields["albums"].queryset
    assert album in queryset
    assert restricted_album not in queryset


# ---------------------------------------------------------------------------
# BlogPostCreateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_blogpost_create_links_an_accessible_album(auth_client, person, album):
    response = auth_client.post(
        reverse("blogpost-create"),
        _post_data(authors=[str(person.pk)], albums=[str(album.pk)]),
    )
    assert response.status_code == 302
    post = BlogPost.objects.get(title="Un billet")
    assert album in post.albums.all()


@pytest.mark.django_db
def test_blogpost_create_rejects_a_restricted_album(auth_client, person, restricted_album):
    """The form's queryset is the entire security boundary: a non-member posting a
    restricted album's pk must be rejected, not silently accepted."""
    response = auth_client.post(
        reverse("blogpost-create"),
        _post_data(authors=[str(person.pk)], albums=[str(restricted_album.pk)]),
    )
    assert response.status_code == 200  # redisplayed with form errors, not redirected
    assert not BlogPost.objects.filter(title="Un billet").exists()


# ---------------------------------------------------------------------------
# BlogPostUpdateView -- the critical silent-wipe regression
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_blogpost_edit_preserves_linked_albums(auth_client, blog_post, album):
    blog_post.albums.add(album)
    assert album in blog_post.albums.all()

    response = auth_client.post(
        reverse("blogpost-edit", kwargs={"pk": blog_post.pk}),
        _post_data(
            title="Titre modifié",
            authors=[str(author.pk) for author in blog_post.authors.all()],
            albums=[str(album.pk)],
        ),
    )
    assert response.status_code == 302
    blog_post.refresh_from_db()
    assert album in blog_post.albums.all()


# ---------------------------------------------------------------------------
# BlogPostDetailView -- render-time re-check
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_blogpost_detail_shows_linked_albums(auth_client, blog_post, album):
    blog_post.albums.add(album)
    response = auth_client.get(reverse("blogpost-detail", kwargs={"pk": blog_post.pk}))
    assert album in list(response.context["linked_albums"])
    assert album.title in response.content.decode()


@pytest.mark.django_db
def test_blogpost_detail_hides_an_album_moved_into_a_restricted_group(auth_client, blog_post, album, restricted_group):
    blog_post.albums.add(album)
    album.groups.add(restricted_group)

    response = auth_client.get(reverse("blogpost-detail", kwargs={"pk": blog_post.pk}))
    assert album not in list(response.context["linked_albums"])
    assert album.title not in response.content.decode()
