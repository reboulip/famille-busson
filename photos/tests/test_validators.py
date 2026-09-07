import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from photos.validators import MAX_PHOTO_SIZE, validate_photo_extension, validate_photo_size


def test_valid_extension_passes():
    file = SimpleUploadedFile("photo.jpg", b"data", content_type="image/jpeg")
    validate_photo_extension(file)  # does not raise


def test_heic_extension_is_allowed():
    file = SimpleUploadedFile("photo.heic", b"data", content_type="image/heic")
    validate_photo_extension(file)  # does not raise


def test_invalid_extension_raises():
    file = SimpleUploadedFile("document.pdf", b"data", content_type="application/pdf")
    with pytest.raises(ValidationError):
        validate_photo_extension(file)


def test_oversized_file_raises():
    file = SimpleUploadedFile("photo.jpg", b"x" * (MAX_PHOTO_SIZE + 1), content_type="image/jpeg")
    with pytest.raises(ValidationError):
        validate_photo_size(file)


def test_undersized_file_passes():
    file = SimpleUploadedFile("photo.jpg", b"x" * 100, content_type="image/jpeg")
    validate_photo_size(file)  # does not raise
