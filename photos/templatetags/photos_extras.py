from django import template

from photos.access import effective_groups as _effective_groups
from photos.access import user_can_access_album

register = template.Library()


@register.filter
def can_access(album, user):
    return user_can_access_album(user, album)


@register.filter
def effective_groups(album):
    return _effective_groups(album)
