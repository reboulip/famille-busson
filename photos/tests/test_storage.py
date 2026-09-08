import pytest

from photos.storage import PhotoStorage, get_photo_storage


def test_get_photo_storage_returns_photo_storage():
    assert isinstance(get_photo_storage(), PhotoStorage)


def test_location_reflects_current_settings(settings, tmp_path):
    settings.PHOTOS_ROOT = tmp_path / "custom"
    storage = PhotoStorage()
    assert str(storage.location) == str(tmp_path / "custom")


def test_url_raises():
    storage = PhotoStorage()
    with pytest.raises(NotImplementedError):
        storage.url("originals/photo.png")
