import os

import pytest

from documents.storage import DocumentStorage, get_document_storage


def test_storage_url_raises():
    storage = DocumentStorage()
    with pytest.raises(NotImplementedError):
        storage.url("files/some-file.pdf")


def test_get_document_storage_returns_a_document_storage_instance():
    assert isinstance(get_document_storage(), DocumentStorage)


def test_storage_location_follows_settings_override(tmp_path, settings):
    settings.DOCUMENTS_ROOT = tmp_path
    storage = DocumentStorage()
    assert storage.location == os.path.abspath(tmp_path)


def test_storage_location_updates_after_settings_change(tmp_path, settings):
    storage = DocumentStorage()
    other_root = tmp_path / "other"
    settings.DOCUMENTS_ROOT = other_root
    assert storage.location == os.path.abspath(other_root)


def test_storage_saves_under_documents_root(tmp_path, settings):
    from django.core.files.base import ContentFile

    settings.DOCUMENTS_ROOT = tmp_path
    storage = DocumentStorage()
    name = storage.save("files/hello.txt", ContentFile(b"hello"))
    assert os.path.exists(os.path.join(tmp_path, name))
