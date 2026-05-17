import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from publications.models import Attachment, BlogPost, Comment


@pytest.mark.django_db
@pytest.mark.parametrize("filename", ["a.jpg", "a.jpeg", "a.png", "a.gif", "a.webp", "A.PNG"])
def test_attachment_marks_image_extensions(blog_post, filename):
    attachment = Attachment.objects.create(
        post=blog_post,
        file=SimpleUploadedFile(filename, b'bytes'),
    )
    assert attachment.is_image is True


@pytest.mark.django_db
@pytest.mark.parametrize("filename", ["a.pdf", "a.docx", "a.txt", "a.mp4", "a.zip"])
def test_attachment_marks_non_image_extensions(blog_post, filename):
    attachment = Attachment.objects.create(
        post=blog_post,
        file=SimpleUploadedFile(filename, b'bytes'),
    )
    assert attachment.is_image is False


@pytest.mark.django_db
def test_blogpost_str_returns_title(blog_post):
    assert str(blog_post) == "Première publication"


@pytest.mark.django_db
def test_blogpost_default_type_is_normal(blog_post):
    assert blog_post.post_type == 'NORMAL'


@pytest.mark.django_db
def test_blogpost_ordering_newest_first(db, person):
    older = BlogPost.objects.create(title="Vieux", body="x")
    older.authors.add(person)
    newer = BlogPost.objects.create(title="Récent", body="y")
    newer.authors.add(person)
    posts = list(BlogPost.objects.all())
    assert posts[0] == newer
    assert posts[1] == older


@pytest.mark.django_db
def test_comment_str_includes_author_and_post(comment):
    assert "Alice Busson" in str(comment)
    assert "Première publication" in str(comment)


@pytest.mark.django_db
def test_comment_str_handles_anonymous(db, blog_post):
    c = Comment.objects.create(post=blog_post, author=None, body="anon")
    assert "Anonyme" in str(c)


@pytest.mark.django_db
def test_attachment_filename_property(image_attachment):
    assert image_attachment.filename.endswith('.png')
