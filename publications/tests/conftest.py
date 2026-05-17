import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from publications.models import Attachment, BlogPost, Comment

from annuaire.tests.conftest import (  # noqa: F401 — re-exported as fixtures
    client,
    account,
    person,
    other_account,
    other_person,
    auth_client,
    staff_account,
    staff_client,
)


@pytest.fixture
def blog_post(db, person):
    post = BlogPost.objects.create(title="Première publication", body="Du contenu.")
    post.authors.add(person)
    return post


@pytest.fixture
def bc_post(db, person):
    post = BlogPost.objects.create(
        title="Annonce BC", body="Une annonce Busson connection.", post_type='BC',
    )
    post.authors.add(person)
    return post


@pytest.fixture
def other_blog_post(db, other_person):
    post = BlogPost.objects.create(title="Article de Bob", body="Le contenu de Bob.")
    post.authors.add(other_person)
    return post


@pytest.fixture
def comment(db, blog_post, person):
    return Comment.objects.create(post=blog_post, author=person, body="Bien dit.")


@pytest.fixture
def image_attachment(db, blog_post):
    uploaded = SimpleUploadedFile(
        name='photo.png',
        content=b'\x89PNG\r\n\x1a\nfake-png-bytes',
        content_type='image/png',
    )
    return Attachment.objects.create(post=blog_post, file=uploaded, caption="Une image")


@pytest.fixture
def pdf_attachment(db, blog_post):
    uploaded = SimpleUploadedFile(
        name='doc.pdf',
        content=b'%PDF-fake',
        content_type='application/pdf',
    )
    return Attachment.objects.create(post=blog_post, file=uploaded, caption="Un PDF")
