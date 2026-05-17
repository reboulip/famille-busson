import pytest
from django.urls import reverse

from publications.models import Comment


LOGIN_URL = "/annuaire/login/"


# ---------------------------------------------------------------------------
# Comment creation (via BlogPostDetailView POST)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_comment_post_requires_login(client, blog_post):
    response = client.post(
        reverse("blogpost-detail", kwargs={"pk": blog_post.pk}),
        {"body": "Anonyme tente."},
    )
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_comment_post_creates_comment_with_request_user_profile(auth_client, blog_post, person):
    response = auth_client.post(
        reverse("blogpost-detail", kwargs={"pk": blog_post.pk}),
        {"body": "Super article !"},
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("blogpost-detail", kwargs={"pk": blog_post.pk})
    created = Comment.objects.get(post=blog_post, body="Super article !")
    assert created.author == person


@pytest.mark.django_db
def test_comment_post_redirects_user_without_profile_to_profile_create(client, blog_post):
    from annuaire.models import Account
    Account.objects.create_user(email="profileless@example.com", password="testpass123!")
    client.login(username="profileless@example.com", password="testpass123!")
    response = client.post(
        reverse("blogpost-detail", kwargs={"pk": blog_post.pk}),
        {"body": "x"},
    )
    assert response.status_code == 302
    assert reverse("profile-create") in response["Location"]
    assert not Comment.objects.filter(post=blog_post, body="x").exists()


@pytest.mark.django_db
def test_comment_post_invalid_re_renders_detail(auth_client, blog_post):
    response = auth_client.post(
        reverse("blogpost-detail", kwargs={"pk": blog_post.pk}),
        {"body": ""},
    )
    assert response.status_code == 200
    assert response.context["comment_form"].errors


# ---------------------------------------------------------------------------
# CommentDeleteView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_comment_delete_requires_login(client, comment):
    response = client.get(reverse("comment-delete", kwargs={"pk": comment.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_comment_delete_forbidden_for_non_staff_even_if_author(auth_client, comment):
    response = auth_client.get(reverse("comment-delete", kwargs={"pk": comment.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_comment_delete_get_returns_confirm_for_staff(staff_client, comment):
    response = staff_client.get(reverse("comment-delete", kwargs={"pk": comment.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_comment_delete_post_removes_and_redirects_to_post(staff_client, comment):
    post_pk = comment.post.pk
    response = staff_client.post(reverse("comment-delete", kwargs={"pk": comment.pk}))
    assert response.status_code == 302
    assert response["Location"] == reverse("blogpost-detail", kwargs={"pk": post_pk})
    assert not Comment.objects.filter(pk=comment.pk).exists()


@pytest.mark.django_db
def test_comment_delete_404_on_invalid_pk(staff_client):
    response = staff_client.get(reverse("comment-delete", kwargs={"pk": 99999}))
    assert response.status_code == 404
