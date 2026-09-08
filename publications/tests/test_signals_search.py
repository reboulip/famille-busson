"""11.2 -- BlogPost's signal-driven search reindexing, including tag changes."""

import pytest

from publications.models import BlogPost, Tag


@pytest.mark.django_db
def test_creating_a_post_populates_search_text(person, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        post = BlogPost.objects.create(title="Été à Genève", body="**gras**")
        post.authors.add(person)

    post.refresh_from_db()
    assert "ete" in post.search_text
    assert "geneve" in post.search_text
    assert "gras" in post.search_text


@pytest.mark.django_db
def test_adding_a_tag_reindexes_the_post(blog_post, django_capture_on_commit_callbacks):
    BlogPost.objects.filter(pk=blog_post.pk).update(search_text="")
    tag = Tag.objects.create(name="Réunion")

    with django_capture_on_commit_callbacks(execute=True):
        blog_post.tags.add(tag)

    blog_post.refresh_from_db()
    assert "reunion" in blog_post.search_text


@pytest.mark.django_db
def test_removing_a_tag_reindexes_the_post(blog_post, tag, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        blog_post.tags.add(tag)
    blog_post.refresh_from_db()
    assert "photos" in blog_post.search_text

    with django_capture_on_commit_callbacks(execute=True):
        blog_post.tags.remove(tag)

    blog_post.refresh_from_db()
    assert "photos" not in blog_post.search_text
