import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from publications.models import Attachment, BlogPost, Comment, Tag


@pytest.mark.django_db
@pytest.mark.parametrize("filename", ["a.jpg", "a.jpeg", "a.png", "a.gif", "a.webp", "A.PNG"])
def test_attachment_marks_image_extensions(blog_post, filename):
    attachment = Attachment.objects.create(
        post=blog_post,
        file=SimpleUploadedFile(filename, b"bytes"),
    )
    assert attachment.is_image is True


@pytest.mark.django_db
@pytest.mark.parametrize("filename", ["a.pdf", "a.docx", "a.txt", "a.mp4", "a.zip"])
def test_attachment_marks_non_image_extensions(blog_post, filename):
    attachment = Attachment.objects.create(
        post=blog_post,
        file=SimpleUploadedFile(filename, b"bytes"),
    )
    assert attachment.is_image is False


@pytest.mark.django_db
@pytest.mark.parametrize("filename", ["a.pdf", "A.PDF"])
def test_attachment_marks_pdf_extension(blog_post, filename):
    attachment = Attachment.objects.create(post=blog_post, file=SimpleUploadedFile(filename, b"bytes"))
    assert attachment.is_pdf is True


@pytest.mark.django_db
@pytest.mark.parametrize("filename", ["a.jpg", "a.docx", "a.txt"])
def test_attachment_is_pdf_false_for_non_pdf_extensions(blog_post, filename):
    attachment = Attachment.objects.create(post=blog_post, file=SimpleUploadedFile(filename, b"bytes"))
    assert attachment.is_pdf is False


@pytest.mark.django_db
def test_blogpost_str_returns_title(blog_post):
    assert str(blog_post) == "Première publication"


@pytest.mark.django_db
def test_blogpost_accent_is_blank_with_no_tags(blog_post):
    assert blog_post.accent == ""


@pytest.mark.django_db
def test_blogpost_accent_is_blank_when_no_tag_is_accented(blog_post):
    blog_post.tags.add(Tag.objects.create(name="Photos", accent=""))
    assert blog_post.accent == ""


@pytest.mark.django_db
def test_blogpost_accent_reflects_first_accented_tag(blog_post):
    blog_post.tags.add(Tag.objects.create(name="Aaa", accent=""))
    blog_post.tags.add(Tag.objects.create(name="Zzz", accent="gold"))
    assert blog_post.accent == "gold"


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
    assert image_attachment.filename.endswith(".png")
