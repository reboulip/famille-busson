from django.db.models import Q

from .models import Bulletin


def effective_groups(bulletin):
    """Bulletins are flat (no nesting like documents.Category), so this is
    just the bulletin's own groups -- no ancestor walk needed."""
    return list(bulletin.groups.all())


def user_can_access_bulletin(user, bulletin):
    if user.is_staff or user.is_superuser:
        return True
    groups = effective_groups(bulletin)
    if not groups:
        return True
    user_group_ids = set(user.groups.values_list("id", flat=True))
    return any(group.id in user_group_ids for group in groups)


def accessible_bulletins(user):
    """SQL-level filter -- mirrors photos.access.accessible_albums."""
    if user.is_staff or user.is_superuser:
        return Bulletin.objects.all()
    return Bulletin.objects.filter(Q(groups__isnull=True) | Q(groups__in=user.groups.all())).distinct()
