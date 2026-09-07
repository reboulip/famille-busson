import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from photos.derivatives import (
    THUMBNAIL_MAX_SIZE,
    WEB_MAX_SIZE,
    generate_derivatives,
    read_exif_taken_at,
)
from photos.models import Photo

from .conftest import make_uploaded_image


def _exif_image_bytes(orientation=None, taken_at="2024:07:14 10:30:00"):
    image = Image.new("RGB", (2000, 1000), color="red")
    exif = image.getexif()
    if taken_at is not None:
        exif[36867] = taken_at  # DateTimeOriginal
    if orientation is not None:
        exif[274] = orientation  # Orientation
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


def test_read_exif_taken_at_parses_datetime_original():
    image = Image.open(io.BytesIO(_exif_image_bytes()))
    taken_at = read_exif_taken_at(image)
    assert taken_at is not None
    assert taken_at.year == 2024
    assert taken_at.month == 7
    assert taken_at.day == 14


def test_read_exif_taken_at_returns_none_when_missing():
    image = Image.new("RGB", (10, 10))
    assert read_exif_taken_at(image) is None


def test_generate_derivatives_produces_thumbnail_and_web_bytes(db, album):
    photo = Photo.objects.create(album=album, file=make_uploaded_image())
    result = generate_derivatives(photo)
    assert result.status == "done"
    assert result.thumbnail_bytes is not None
    assert result.web_bytes is not None

    thumb = Image.open(io.BytesIO(result.thumbnail_bytes))
    assert thumb.width <= THUMBNAIL_MAX_SIZE[0]
    assert thumb.height <= THUMBNAIL_MAX_SIZE[1]

    web = Image.open(io.BytesIO(result.web_bytes))
    assert web.width <= WEB_MAX_SIZE[0]
    assert web.height <= WEB_MAX_SIZE[1]


def test_generate_derivatives_extracts_dimensions(db, album):
    upload = SimpleUploadedFile("exif.jpg", _exif_image_bytes(), content_type="image/jpeg")
    photo = Photo.objects.create(album=album, file=upload)
    result = generate_derivatives(photo)
    assert result.status == "done"
    assert result.width == 2000
    assert result.height == 1000
    assert result.taken_at is not None


def test_generate_derivatives_never_raises_on_corrupt_data(db, album):
    upload = SimpleUploadedFile("broken.jpg", b"not an actual image", content_type="image/jpeg")
    photo = Photo(album=album, file=upload)
    photo.save()
    result = generate_derivatives(photo)
    assert result.status == "error"
    assert result.error
