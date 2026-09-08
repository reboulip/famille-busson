"""11.2 -- Album/Photo signal-driven search reindexing."""

import pytest


@pytest.mark.django_db
def test_creating_an_album_populates_search_text(album, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        album.description = "**gras**"
        album.save()

    album.refresh_from_db()
    assert "ete" in album.search_text
    assert "gras" in album.search_text


@pytest.mark.django_db
def test_creating_a_photo_populates_search_text_from_caption(photo, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        photo.caption = "Été à Genève"
        photo.save()

    photo.refresh_from_db()
    assert "ete" in photo.search_text
    assert "geneve" in photo.search_text


@pytest.mark.django_db
def test_photo_search_text_includes_album_description(album, photo, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        album.description = "Vacances en montagne"
        album.save()
        photo.caption = "trigger reindex"
        photo.save()

    photo.refresh_from_db()
    assert "montagne" in photo.search_text
