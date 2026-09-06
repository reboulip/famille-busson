"""Phase 8.5 — publication attachments render through the same in-page viewer as the
documents app, instead of navigating away on click (#131)."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_image_attachment_uses_the_document_viewer(auth_client, image_attachment):
    response = auth_client.get(reverse("blogpost-detail", kwargs={"pk": image_attachment.post.pk}))
    content = response.content.decode()
    assert "document-viewer" in content
    assert "document-viewer-fullscreen-btn" in content


@pytest.mark.django_db
def test_image_is_not_wrapped_in_a_navigating_link(auth_client, image_attachment):
    """The old markup wrapped the <img> in an <a href> to the same file, which
    navigated the browser away on click -- that's the bug #131 reports."""
    response = auth_client.get(reverse("blogpost-detail", kwargs={"pk": image_attachment.post.pk}))
    content = response.content.decode()
    img_index = content.index(f'src="{image_attachment.file.url}"')
    # Nothing between the viewer stage and this <img> may be an anchor pointing at
    # the image file itself -- the image sits inside a plain stage div, not a link.
    preceding = content[max(0, img_index - 120) : img_index]
    assert "<a " not in preceding


@pytest.mark.django_db
def test_pdf_attachment_uses_the_document_viewer(auth_client, pdf_attachment):
    response = auth_client.get(reverse("blogpost-detail", kwargs={"pk": pdf_attachment.post.pk}))
    content = response.content.decode()
    assert "document-viewer-pdf-pages" in content
    assert 'data-pdf-url="' + pdf_attachment.file.url in content


@pytest.mark.django_db
def test_viewer_script_loads_only_when_there_is_something_to_view(auth_client, blog_post):
    response = auth_client.get(reverse("blogpost-detail", kwargs={"pk": blog_post.pk}))
    assert "document_viewer.js" not in response.content.decode()


@pytest.mark.django_db
def test_viewer_script_loads_when_an_image_is_attached(auth_client, image_attachment):
    response = auth_client.get(reverse("blogpost-detail", kwargs={"pk": image_attachment.post.pk}))
    assert "document_viewer.js" in response.content.decode()


@pytest.mark.django_db
def test_multiple_images_render_as_a_carousel_strip(auth_client, blog_post, image_attachment):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from publications.models import Attachment

    Attachment.objects.create(
        post=blog_post,
        file=SimpleUploadedFile("second.png", b"\x89PNG\r\n\x1a\nmore-fake-bytes", content_type="image/png"),
    )
    response = auth_client.get(reverse("blogpost-detail", kwargs={"pk": blog_post.pk}))
    content = response.content.decode()
    assert "document-viewer-strip" in content
    assert "2 images" in content
