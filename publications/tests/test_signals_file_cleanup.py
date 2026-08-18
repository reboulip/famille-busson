import os

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from publications.models import Attachment


@pytest.fixture(autouse=True)
def use_tmp_media(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path


def _uploaded(name="doc.pdf"):
    return SimpleUploadedFile(name, b"%PDF-fake", content_type="application/pdf")


@pytest.mark.django_db
def test_attachment_delete_removes_file(django_capture_on_commit_callbacks, blog_post):
    attachment = Attachment.objects.create(post=blog_post, file=_uploaded())
    file_path = attachment.file.path
    assert os.path.exists(file_path)

    with django_capture_on_commit_callbacks(execute=True):
        attachment.delete()

    assert not os.path.exists(file_path)


@pytest.mark.django_db
def test_attachment_replace_file_removes_old_file(django_capture_on_commit_callbacks, blog_post):
    attachment = Attachment.objects.create(post=blog_post, file=_uploaded("old.pdf"))
    old_path = attachment.file.path

    with django_capture_on_commit_callbacks(execute=True):
        attachment.file = _uploaded("new.pdf")
        attachment.save()

    assert not os.path.exists(old_path)
    assert os.path.exists(attachment.file.path)


@pytest.mark.django_db
def test_shared_filename_not_deleted_while_another_row_references_it(django_capture_on_commit_callbacks, blog_post):
    attachment1 = Attachment.objects.create(post=blog_post, file=_uploaded("shared.pdf"))
    shared_name = attachment1.file.name
    attachment2 = Attachment.objects.create(post=blog_post, file=_uploaded("other.pdf"))
    attachment2.file.name = shared_name
    attachment2.save(update_fields=["file"])

    file_path = attachment1.file.path
    assert os.path.exists(file_path)

    with django_capture_on_commit_callbacks(execute=True):
        attachment1.delete()

    assert os.path.exists(file_path)


@pytest.mark.django_db
def test_missing_file_on_disk_does_not_raise(django_capture_on_commit_callbacks, blog_post):
    attachment = Attachment.objects.create(post=blog_post, file=_uploaded())
    os.remove(attachment.file.path)

    with django_capture_on_commit_callbacks(execute=True):
        attachment.delete()  # must not raise even though the file is already gone
