from django import template

from photos.access import effective_groups as _effective_groups
from photos.access import user_can_access_album
from photos.validators import ALLOWED_EXTENSIONS, MAX_CONCURRENT_UPLOADS, MAX_FILES_PER_SELECTION, MAX_PHOTO_SIZE

register = template.Library()


@register.filter
def can_access(album, user):
    return user_can_access_album(user, album)


@register.filter
def effective_groups(album):
    return _effective_groups(album)


@register.simple_tag
def allowed_photo_extensions():
    """Comma-separated extension list for a file input's `accept` attribute --
    single source of truth shared with `validate_photo_extension`, so the
    picker and the server-side validation can't drift apart."""
    return ",".join(sorted(ALLOWED_EXTENSIONS))


@register.simple_tag
def max_photo_size_bytes():
    return MAX_PHOTO_SIZE


@register.simple_tag
def max_photo_size_mb():
    return MAX_PHOTO_SIZE // (1024 * 1024)


@register.simple_tag
def max_files_per_selection():
    return MAX_FILES_PER_SELECTION


@register.simple_tag
def max_concurrent_uploads():
    return MAX_CONCURRENT_UPLOADS
