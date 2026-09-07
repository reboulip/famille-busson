from django.db.models import Q

from .models import Album, Photo


def effective_groups(album):
    """Albums are flat (no nesting like documents.Category), so this is just
    the album's own groups -- no ancestor walk needed."""
    return list(album.groups.all())


def user_can_access_album(user, album):
    if user.is_staff or user.is_superuser:
        return True
    groups = effective_groups(album)
    if not groups:
        return True
    user_group_ids = set(user.groups.values_list("id", flat=True))
    return any(group.id in user_group_ids for group in groups)


def accessible_albums(user):
    """SQL-level filter -- unlike documents.access.accessible_categories' Python
    ancestor walk, flat albums make this a plain queryset filter."""
    if user.is_staff or user.is_superuser:
        return Album.objects.all()
    return Album.objects.filter(Q(groups__isnull=True) | Q(groups__in=user.groups.all())).distinct()


def accessible_photos(user):
    return Photo.objects.filter(album__in=accessible_albums(user))
