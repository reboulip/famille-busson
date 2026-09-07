"""Photo derivative generation: thumbnails, web-size renditions, and EXIF
capture date/orientation. Pure functions returning a frozen result dataclass
that never raises -- mirrors documents/extraction.py's pattern, so callers
(photos/tasks.py) persist `status`/`error` regardless of outcome and one
corrupt photo never aborts a batch run.
"""

from __future__ import annotations

import datetime as dt
import io
from dataclasses import dataclass

from django.utils import timezone as django_timezone
from PIL import Image, ImageOps

THUMBNAIL_MAX_SIZE = (400, 400)
WEB_MAX_SIZE = (1600, 1600)
DERIVATIVE_QUALITY = 82
DERIVATIVE_FORMAT = "WEBP"

# EXIF tag id for DateTimeOriginal -- looked up by number rather than via
# PIL.ExifTags.TAGS, which is a plain name->id dict not guaranteed stable
# across Pillow versions for lookup-by-name.
_EXIF_DATETIME_ORIGINAL = 36867


@dataclass(frozen=True)
class DerivativeResult:
    status: str  # "done" | "error"
    error: str
    thumbnail_bytes: bytes | None
    web_bytes: bytes | None
    taken_at: dt.datetime | None
    width: int | None
    height: int | None


def read_exif_taken_at(image: Image.Image) -> dt.datetime | None:
    """Extract EXIF DateTimeOriginal. The value is naive local camera time with
    no timezone info attached; since the true capture timezone is unknown, it
    is made aware in UTC directly (the project runs entirely in UTC) rather
    than guessed at -- a documented, accepted trade-off (see the sprint
    brief). Never raises: returns None on missing/malformed EXIF."""
    try:
        exif = image.getexif()
        raw = exif.get(_EXIF_DATETIME_ORIGINAL)
        if not raw:
            return None
        naive = dt.datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
        return django_timezone.make_aware(naive, dt.UTC)
    except (ValueError, TypeError, OSError):
        return None


def _prepare_for_encode(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        return image.convert("RGBA")
    return image.convert("RGB")


def _resize_and_encode(image: Image.Image, max_size: tuple[int, int]) -> bytes:
    resized = image.copy()
    resized.thumbnail(max_size, Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    resized.save(buffer, format=DERIVATIVE_FORMAT, quality=DERIVATIVE_QUALITY)
    return buffer.getvalue()


def generate_derivatives(photo) -> DerivativeResult:
    """Main entry point: read the photo's original file, extract EXIF, apply
    orientation, and build both derivatives. Never raises -- the caller
    persists `status`/`error` on the model regardless of outcome, so one
    corrupt/oversized upload never aborts a batch run."""
    try:
        with photo.file.open("rb") as fh:
            data = fh.read()
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            taken_at = read_exif_taken_at(image)
            # Applied (baked in) rather than stored separately -- nothing would
            # consume an unapplied orientation, and a stored-but-unapplied value
            # is a rotation bug waiting to happen.
            oriented = ImageOps.exif_transpose(image) or image
            width, height = oriented.size
            prepared = _prepare_for_encode(oriented)
            thumbnail_bytes = _resize_and_encode(prepared, THUMBNAIL_MAX_SIZE)
            web_bytes = _resize_and_encode(prepared, WEB_MAX_SIZE)
        return DerivativeResult(
            status="done",
            error="",
            thumbnail_bytes=thumbnail_bytes,
            web_bytes=web_bytes,
            taken_at=taken_at,
            width=width,
            height=height,
        )
    except Exception as exc:
        return DerivativeResult(
            status="error",
            error=str(exc)[:255],
            thumbnail_bytes=None,
            web_bytes=None,
            taken_at=None,
            width=None,
            height=None,
        )
