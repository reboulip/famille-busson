"""11.4 — tags on publications."""

import pytest
from django.db import IntegrityError
from django.urls import reverse

from publications.forms import BlogPostForm
from publications.models import BlogPost, Tag


def _post_data(**overrides):
    data = {
        "title": "Un billet",
        "post_type": "NORMAL",
        "body": "Contenu.",
        "authors": [],
        "tags": "",
        "attachments-TOTAL_FORMS": "0",
        "attachments-INITIAL_FORMS": "0",
        "attachments-MIN_NUM_FORMS": "0",
        "attachments-MAX_NUM_FORMS": "1000",
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Tag model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tag_str_returns_name():
    assert str(Tag.objects.create(name="Photos")) == "Photos"


@pytest.mark.django_db
def test_tag_ordering_is_alphabetical():
    Tag.objects.create(name="Réunion")
    Tag.objects.create(name="Annonce")
    assert list(Tag.objects.values_list("name", flat=True)) == ["Annonce", "Réunion"]


@pytest.mark.django_db
def test_tag_name_is_unique():
    Tag.objects.create(name="Photos")
    with pytest.raises(IntegrityError):
        Tag.objects.create(name="Photos")


# ---------------------------------------------------------------------------
# Form-level tag parsing
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_form_creates_new_tags_from_comma_separated_input(person):
    form = BlogPostForm(
        data=_post_data(authors=[person.pk], tags="Photos, Réunion"), current_person=person, user=person.account
    )
    assert form.is_valid(), form.errors
    post = form.save()
    assert {t.name for t in post.tags.all()} == {"Photos", "Réunion"}


@pytest.mark.django_db
def test_form_reuses_existing_tag_case_insensitively(person, tag):
    form = BlogPostForm(
        data=_post_data(authors=[person.pk], tags="photos"), current_person=person, user=person.account
    )
    assert form.is_valid(), form.errors
    post = form.save()
    assert list(post.tags.all()) == [tag]
    assert Tag.objects.count() == 1


@pytest.mark.django_db
def test_form_blank_tags_input_creates_no_tags(person):
    form = BlogPostForm(data=_post_data(authors=[person.pk], tags=""), current_person=person, user=person.account)
    assert form.is_valid(), form.errors
    post = form.save()
    assert post.tags.count() == 0


@pytest.mark.django_db
def test_form_prefills_tags_on_edit(person, blog_post, tag):
    blog_post.tags.add(tag)
    form = BlogPostForm(instance=blog_post, current_person=person, user=person.account)
    assert form.fields["tags"].initial == "Photos"


# ---------------------------------------------------------------------------
# View: create/edit through the full request cycle
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_view_attaches_tags(auth_client, person):
    response = auth_client.post(reverse("blogpost-create"), data=_post_data(authors=[person.pk], tags="Chalet"))
    post = BlogPost.objects.get(title="Un billet")
    assert response.status_code == 302
    assert {t.name for t in post.tags.all()} == {"Chalet"}


@pytest.mark.django_db
def test_update_view_replaces_tags(auth_client, blog_post, person, tag):
    blog_post.tags.add(tag)
    response = auth_client.post(
        reverse("blogpost-edit", args=[blog_post.pk]),
        data=_post_data(authors=[person.pk], title=blog_post.title, tags="Chalet"),
    )
    blog_post.refresh_from_db()
    assert response.status_code == 302
    assert {t.name for t in blog_post.tags.all()} == {"Chalet"}


# ---------------------------------------------------------------------------
# List filtering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_list_filters_by_tag(auth_client, blog_post, other_blog_post, tag):
    blog_post.tags.add(tag)
    response = auth_client.get(reverse("blogpost-list"), {"tag": tag.pk})
    posts = list(response.context["posts"])
    assert blog_post in posts
    assert other_blog_post not in posts


@pytest.mark.django_db
def test_list_without_tag_filter_shows_all(auth_client, blog_post, other_blog_post, tag):
    blog_post.tags.add(tag)
    response = auth_client.get(reverse("blogpost-list"))
    posts = list(response.context["posts"])
    assert blog_post in posts
    assert other_blog_post in posts


@pytest.mark.django_db
def test_filter_tags_context_excludes_unused_tags(auth_client, blog_post, tag):
    Tag.objects.create(name="Non utilisée")
    blog_post.tags.add(tag)
    response = auth_client.get(reverse("blogpost-list"))
    assert list(response.context["filter_tags"]) == [tag]


# ---------------------------------------------------------------------------
# Card rendering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_card_renders_tag_chip_inside_meta_paragraph(auth_client, blog_post, tag):
    blog_post.tags.add(tag)
    response = auth_client.get(reverse("blogpost-list"))
    content = response.content.decode()
    meta_start = content.index('<p class="fb-meta">')
    meta_end = content.index("</p>", meta_start)
    assert "Photos" in content[meta_start:meta_end]


@pytest.mark.django_db
def test_card_tag_chip_links_to_filtered_list(auth_client, blog_post, tag):
    blog_post.tags.add(tag)
    response = auth_client.get(reverse("blogpost-list"))
    assert f"?tag={tag.pk}" in response.content.decode()


@pytest.mark.django_db
def test_card_tag_with_accent_gets_modifier_class(auth_client, blog_post):
    gold_tag = Tag.objects.create(name="Anniversaire", accent="gold")
    blog_post.tags.add(gold_tag)
    response = auth_client.get(reverse("blogpost-list"))
    assert "fb-chip fb-chip--gold" in response.content.decode()
