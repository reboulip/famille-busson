from django import template

from documents.access import effective_groups as _effective_groups
from documents.access import user_can_access_category
from documents.validators import ALLOWED_EXTENSIONS

register = template.Library()


@register.filter
def can_access(category, user):
    return user_can_access_category(user, category)


@register.filter
def effective_groups(category):
    return _effective_groups(category)


@register.simple_tag
def allowed_file_extensions():
    """Comma-separated extension list for a file input's `accept` attribute --
    single source of truth shared with `validate_document_extension`, so the
    picker and the server-side validation can't drift apart."""
    return ",".join(sorted(ALLOWED_EXTENSIONS))
