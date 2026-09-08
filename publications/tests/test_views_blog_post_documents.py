"""Phase 8.4 — linking a publication to a document(s) (#133)."""

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from documents.models import Category, Document
from publications.forms import BlogPostForm
from publications.models import BlogPost


@pytest.fixture
def category(db):
    return Category.objects.create(name="Actes de famille")


@pytest.fixture
def document(db, category):
    return Document.objects.create(title="Acte de test", category=category)


@pytest.fixture
def restricted_group(db):
    return Group.objects.create(name="SCI grand chalet")


@pytest.fixture
def restricted_category(db, restricted_group):
    category = Category.objects.create(name="Documents SCI")
    category.groups.add(restricted_group)
    return category


@pytest.fixture
def restricted_document(db, restricted_category):
    return Document.objects.create(title="Document restreint", category=restricted_category)


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
def test_form_documents_queryset_is_empty_without_a_user():
    form = BlogPostForm()
    assert list(form.fields["documents"].queryset) == []


@pytest.mark.django_db
def test_form_documents_queryset_excludes_restricted_documents(person, document, restricted_document):
    form = BlogPostForm(user=person.account, current_person=person)
    queryset = form.fields["documents"].queryset
    assert document in queryset
    assert restricted_document not in queryset


# ---------------------------------------------------------------------------
# BlogPostCreateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_blogpost_create_links_an_accessible_document(auth_client, person, document):
    response = auth_client.post(
        reverse("blogpost-create"),
        _post_data(authors=[str(person.pk)], documents=[str(document.pk)]),
    )
    assert response.status_code == 302
    post = BlogPost.objects.get(title="Un billet")
    assert document in post.documents.all()


@pytest.mark.django_db
def test_blogpost_create_rejects_a_restricted_document(auth_client, person, restricted_document):
    """The form's queryset is the entire security boundary: a non-member posting a
    restricted document's pk must be rejected, not silently accepted."""
    response = auth_client.post(
        reverse("blogpost-create"),
        _post_data(authors=[str(person.pk)], documents=[str(restricted_document.pk)]),
    )
    assert response.status_code == 200  # redisplayed with form errors, not redirected
    assert not BlogPost.objects.filter(title="Un billet").exists()


# ---------------------------------------------------------------------------
# BlogPostUpdateView -- the critical silent-wipe regression
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_blogpost_edit_preserves_linked_documents(auth_client, blog_post, document):
    blog_post.documents.add(document)
    assert document in blog_post.documents.all()

    response = auth_client.post(
        reverse("blogpost-edit", kwargs={"pk": blog_post.pk}),
        _post_data(
            title="Titre modifié",
            authors=[str(author.pk) for author in blog_post.authors.all()],
            documents=[str(document.pk)],
        ),
    )
    assert response.status_code == 302
    blog_post.refresh_from_db()
    assert document in blog_post.documents.all()


# ---------------------------------------------------------------------------
# BlogPostDetailView -- render-time re-check
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_blogpost_detail_shows_linked_documents(auth_client, blog_post, document):
    blog_post.documents.add(document)
    response = auth_client.get(reverse("blogpost-detail", kwargs={"pk": blog_post.pk}))
    assert document in list(response.context["linked_documents"])
    assert document.title in response.content.decode()


@pytest.mark.django_db
def test_blogpost_detail_hides_a_document_moved_into_a_restricted_category(
    auth_client, blog_post, document, restricted_category
):
    blog_post.documents.add(document)
    document.category = restricted_category
    document.save()

    response = auth_client.get(reverse("blogpost-detail", kwargs={"pk": blog_post.pk}))
    assert document not in list(response.context["linked_documents"])
    assert document.title not in response.content.decode()
