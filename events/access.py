from django.db.models import Q

from .models import Event


def effective_groups(event):
    """Events are flat (no nesting), so this is just the event's own groups --
    no ancestor walk needed."""
    return list(event.groups.all())


def user_can_access_event(user, event):
    if user.is_staff or user.is_superuser:
        return True
    groups = effective_groups(event)
    if not groups:
        return True
    user_group_ids = set(user.groups.values_list("id", flat=True))
    return any(group.id in user_group_ids for group in groups)


def accessible_events(user, *, bypass_staff=True):
    """SQL-level filter. Unlike photos.Album/documents.Category, a locked event is
    INVISIBLE (never "visible but locked") -- a leaked event date/address is a
    bigger deal than a leaked folder name. Every list/detail/calendar/ICS/home
    card/map consumer must scope through this, never Event.objects.all().

    `bypass_staff=False` disables the staff/superuser "see everything" shortcut
    -- used by the iCal feed (12.5), where the subscriber is a specific
    account piping data into a third-party calendar service, not browsing the
    site directly. A staff member's feed must reflect their own group
    membership like anyone else's, not their in-app staff privileges."""
    if bypass_staff and (user.is_staff or user.is_superuser):
        return Event.objects.all()
    return Event.objects.filter(Q(groups__isnull=True) | Q(groups__in=user.groups.all())).distinct()
