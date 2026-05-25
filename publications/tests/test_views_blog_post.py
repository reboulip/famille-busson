import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from publications.models import Attachment, BlogPost


LOGIN_URL = "/annuaire/login/"


def _empty_attachment_formset_data(initial=0, total=3):
    """Return management-form fields for AttachmentFormSet with no submitted rows."""
    return {
        'attachments-TOTAL_FORMS': str(total),
        'attachments-INITIAL_FORMS': str(initial),
        'attachments-MIN_NUM_FORMS': '0',
        'attachments-MAX_NUM_FORMS': '1000',
    }


# ---------------------------------------------------------------------------
# BlogPostListView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_blogpost_list_requires_login(client):
    response = client.get(reverse("blogpost-list"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_blogpost_list_returns_200(auth_client):
    response = auth_client.get(reverse("blogpost-list"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_blogpost_list_contains_posts(auth_client, blog_post):
    response = auth_client.get(reverse("blogpost-list"))
    assert blog_post in response.context["posts"]


@pytest.mark.django_db
def test_blogpost_list_orders_newest_first(auth_client, person):
    older = BlogPost.objects.create(title="Vieux", body="x")
    older.authors.add(person)
    newer = BlogPost.objects.create(title="Récent", body="y")
    newer.authors.add(person)
    response = auth_client.get(reverse("blogpost-list"))
    posts = list(response.context["posts"])
    assert posts.index(newer) < posts.index(older)


# ---------------------------------------------------------------------------
# BlogPostDetailView (GET)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_blogpost_detail_requires_login(client, blog_post):
    response = client.get(reverse("blogpost-detail", kwargs={"pk": blog_post.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_blogpost_detail_returns_200(auth_client, blog_post):
    response = auth_client.get(reverse("blogpost-detail", kwargs={"pk": blog_post.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_blogpost_detail_404_on_invalid_pk(auth_client):
    response = auth_client.get(reverse("blogpost-detail", kwargs={"pk": 99999}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_blogpost_detail_exposes_comment_form(auth_client, blog_post):
    response = auth_client.get(reverse("blogpost-detail", kwargs={"pk": blog_post.pk}))
    assert "comment_form" in response.context


@pytest.mark.django_db
def test_blogpost_detail_can_edit_true_for_author(auth_client, blog_post):
    response = auth_client.get(reverse("blogpost-detail", kwargs={"pk": blog_post.pk}))
    assert response.context["can_edit"] is True


@pytest.mark.django_db
def test_blogpost_detail_can_edit_false_for_non_author(auth_client, other_blog_post):
    response = auth_client.get(reverse("blogpost-detail", kwargs={"pk": other_blog_post.pk}))
    assert response.context["can_edit"] is False


@pytest.mark.django_db
def test_blogpost_detail_can_edit_true_for_staff(staff_client, blog_post):
    response = staff_client.get(reverse("blogpost-detail", kwargs={"pk": blog_post.pk}))
    assert response.context["can_edit"] is True


@pytest.mark.django_db
def test_blogpost_detail_renders_image_inline(auth_client, image_attachment):
    response = auth_client.get(
        reverse("blogpost-detail", kwargs={"pk": image_attachment.post.pk})
    )
    assert b'<img' in response.content
    assert image_attachment.file.url.encode() in response.content


@pytest.mark.django_db
def test_blogpost_detail_renders_pdf_as_download_link(auth_client, pdf_attachment):
    response = auth_client.get(
        reverse("blogpost-detail", kwargs={"pk": pdf_attachment.post.pk})
    )
    assert b'download' in response.content
    assert pdf_attachment.file.url.encode() in response.content


# ---------------------------------------------------------------------------
# BlogPostCreateView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_blogpost_create_requires_login(client):
    response = client.get(reverse("blogpost-create"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_blogpost_create_get_returns_200(auth_client):
    response = auth_client.get(reverse("blogpost-create"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_blogpost_create_post_creates_post_and_assigns_author(auth_client, person):
    data = {
        "title": "Mon premier article",
        "body": "Contenu de l'article.",
        "post_type": "NORMAL",
        "authors": [person.pk],
    }
    data.update(_empty_attachment_formset_data())
    response = auth_client.post(reverse("blogpost-create"), data)
    assert response.status_code == 302
    post = BlogPost.objects.get(title="Mon premier article")
    assert person in post.authors.all()
    assert reverse("blogpost-detail", kwargs={"pk": post.pk}) in response["Location"]


@pytest.mark.django_db
def test_blogpost_create_force_adds_current_user_as_author(auth_client, person, other_person):
    """If user tampers and omits themselves, view should still add them as an author."""
    data = {
        "title": "Article sans moi",
        "body": "x",
        "post_type": "NORMAL",
        "authors": [other_person.pk],
    }
    data.update(_empty_attachment_formset_data())
    auth_client.post(reverse("blogpost-create"), data)
    post = BlogPost.objects.get(title="Article sans moi")
    assert person in post.authors.all()
    assert other_person in post.authors.all()


@pytest.mark.django_db
def test_blogpost_create_with_bc_type(auth_client, person):
    data = {
        "title": "BC announcement",
        "body": "x",
        "post_type": "BC",
        "authors": [person.pk],
    }
    data.update(_empty_attachment_formset_data())
    auth_client.post(reverse("blogpost-create"), data)
    assert BlogPost.objects.get(title="BC announcement").post_type == 'BC'


@pytest.mark.django_db
def test_blogpost_create_with_attachment(auth_client, person):
    data = {
        "title": "Avec pj",
        "body": "x",
        "post_type": "NORMAL",
        "authors": [person.pk],
        "attachments-TOTAL_FORMS": "3",
        "attachments-INITIAL_FORMS": "0",
        "attachments-MIN_NUM_FORMS": "0",
        "attachments-MAX_NUM_FORMS": "1000",
        "attachments-0-file": SimpleUploadedFile("p.png", b"data", "image/png"),
        "attachments-0-caption": "Photo",
    }
    auth_client.post(reverse("blogpost-create"), data)
    post = BlogPost.objects.get(title="Avec pj")
    assert post.attachments.count() == 1
    assert post.attachments.first().is_image is True


@pytest.mark.django_db
def test_blogpost_create_invalid_returns_200(auth_client, person):
    data = {"title": "", "body": "", "post_type": "NORMAL", "authors": [person.pk]}
    data.update(_empty_attachment_formset_data())
    response = auth_client.post(reverse("blogpost-create"), data)
    assert response.status_code == 200
    assert response.context["form"].errors


@pytest.mark.django_db
def test_blogpost_create_with_invalid_attachment_formset_does_not_create_post(auth_client, person):
    """Regression for #17: an invalid attachment formset must not leak a saved BlogPost."""
    data = {
        "title": "Doit ne pas être créé",
        "body": "x",
        "post_type": "NORMAL",
        "authors": [person.pk],
        "attachments-TOTAL_FORMS": "1",
        "attachments-INITIAL_FORMS": "0",
        "attachments-MIN_NUM_FORMS": "0",
        "attachments-MAX_NUM_FORMS": "1000",
        "attachments-0-caption": "Légende sans fichier",
    }
    response = auth_client.post(reverse("blogpost-create"), data)
    assert response.status_code == 200
    assert not BlogPost.objects.filter(title="Doit ne pas être créé").exists()


@pytest.mark.django_db
def test_blogpost_create_without_attachment_creates_post(auth_client, person):
    """PJ is optional: a publication can be created without any attachment."""
    data = {
        "title": "Sans pièce jointe",
        "body": "x",
        "post_type": "NORMAL",
        "authors": [person.pk],
    }
    data.update(_empty_attachment_formset_data())
    response = auth_client.post(reverse("blogpost-create"), data)
    assert response.status_code == 302
    post = BlogPost.objects.get(title="Sans pièce jointe")
    assert post.attachments.count() == 0


@pytest.mark.django_db
def test_blogpost_create_get_seeds_authors_with_current_user(auth_client, person):
    response = auth_client.get(reverse("blogpost-create"))
    data = json.loads(response.context["authors_initial_json"])
    assert [item["id"] for item in data] == [person.pk]


@pytest.mark.django_db
def test_blogpost_edit_get_seeds_authors_with_existing(auth_client, blog_post, person, other_person):
    blog_post.authors.add(other_person)
    response = auth_client.get(reverse("blogpost-edit", kwargs={"pk": blog_post.pk}))
    data = json.loads(response.context["authors_initial_json"])
    ids = {item["id"] for item in data}
    assert ids == {person.pk, other_person.pk}


@pytest.mark.django_db
def test_blogpost_create_supports_multiple_authors(auth_client, person, other_person):
    data = {
        "title": "Co-écrit",
        "body": "Du contenu.",
        "post_type": "NORMAL",
        "authors": [str(person.pk), str(other_person.pk)],
    }
    data.update(_empty_attachment_formset_data())
    response = auth_client.post(reverse("blogpost-create"), data)
    assert response.status_code == 302
    post = BlogPost.objects.get(title="Co-écrit")
    assert set(post.authors.all()) == {person, other_person}


@pytest.mark.django_db
def test_blogpost_update_with_invalid_attachment_formset_does_not_modify_post(
    auth_client, blog_post, person,
):
    """Regression for #17: invalid formset must not partially apply BlogPost edits."""
    original_title = blog_post.title
    data = {
        "title": "Titre tampon",
        "body": "Nouveau contenu.",
        "post_type": "NORMAL",
        "authors": [person.pk],
        "attachments-TOTAL_FORMS": "1",
        "attachments-INITIAL_FORMS": "0",
        "attachments-MIN_NUM_FORMS": "0",
        "attachments-MAX_NUM_FORMS": "1000",
        "attachments-0-caption": "Légende sans fichier",
    }
    response = auth_client.post(
        reverse("blogpost-edit", kwargs={"pk": blog_post.pk}), data,
    )
    assert response.status_code == 200
    blog_post.refresh_from_db()
    assert blog_post.title == original_title


# ---------------------------------------------------------------------------
# BlogPostUpdateView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_blogpost_update_requires_login(client, blog_post):
    response = client.get(reverse("blogpost-edit", kwargs={"pk": blog_post.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_blogpost_update_forbidden_for_non_author(auth_client, other_blog_post):
    response = auth_client.get(reverse("blogpost-edit", kwargs={"pk": other_blog_post.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_blogpost_update_allowed_for_author(auth_client, blog_post):
    response = auth_client.get(reverse("blogpost-edit", kwargs={"pk": blog_post.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_blogpost_update_allowed_for_staff(staff_client, blog_post):
    response = staff_client.get(reverse("blogpost-edit", kwargs={"pk": blog_post.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_blogpost_update_post_updates_fields(auth_client, blog_post, person):
    data = {
        "title": "Titre modifié",
        "body": "Nouveau contenu.",
        "post_type": "BC",
        "authors": [person.pk],
    }
    data.update(_empty_attachment_formset_data())
    response = auth_client.post(
        reverse("blogpost-edit", kwargs={"pk": blog_post.pk}), data,
    )
    assert response.status_code == 302
    blog_post.refresh_from_db()
    assert blog_post.title == "Titre modifié"
    assert blog_post.post_type == "BC"


# ---------------------------------------------------------------------------
# BlogPostDeleteView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_blogpost_delete_requires_login(client, blog_post):
    response = client.get(reverse("blogpost-delete", kwargs={"pk": blog_post.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_blogpost_delete_forbidden_for_non_author(auth_client, other_blog_post):
    response = auth_client.get(reverse("blogpost-delete", kwargs={"pk": other_blog_post.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_blogpost_delete_get_returns_confirm_for_author(auth_client, blog_post):
    response = auth_client.get(reverse("blogpost-delete", kwargs={"pk": blog_post.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_blogpost_delete_post_removes_post(auth_client, blog_post):
    pk = blog_post.pk
    response = auth_client.post(reverse("blogpost-delete", kwargs={"pk": pk}))
    assert response.status_code == 302
    assert response["Location"] == reverse("blogpost-list")
    assert not BlogPost.objects.filter(pk=pk).exists()


@pytest.mark.django_db
def test_blogpost_delete_post_allowed_for_staff(staff_client, blog_post):
    pk = blog_post.pk
    response = staff_client.post(reverse("blogpost-delete", kwargs={"pk": pk}))
    assert response.status_code == 302
    assert not BlogPost.objects.filter(pk=pk).exists()
