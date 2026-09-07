"""'Il y a X ans' — resurfacing a photo or publication from this date in an
earlier year, next to the home page's birthdays widget.

Modelled on annuaire/birthdays.py: `today` is an explicit parameter rather
than read from the clock here, so this can be tested against a fixed date
instead of whatever day the suite happens to run on.
"""

from __future__ import annotations

import datetime
from typing import NamedTuple


class Memory(NamedTuple):
    kind: str  # "photo" | "post"
    item: object
    years_ago: int


def memories(today: datetime.date, user, limit: int = 3) -> list[Memory]:
    """Photos and publications from `today`'s month/day in earlier years,
    most-recent-anniversary first, capped at `limit`.

    Comparisons run on Photo.taken_at/BlogPost.created_at, both stored in UTC
    (project-wide USE_TZ=True, TIME_ZONE="UTC") -- a photo taken or a post
    published late at night in local time can surface a calendar day off from
    the photographer's/author's own view. A pre-existing, accepted class of
    approximation elsewhere in this codebase (see birthdays.py); not fixed here.
    """
    # Lazy-imported, same as home()'s existing publications.models import --
    # annuaire must not gain a hard top-level dependency on photos/publications.
    from photos.access import accessible_photos
    from publications.models import BlogPost

    entries = [
        Memory(kind="photo", item=photo, years_ago=today.year - photo.taken_at.year)
        for photo in accessible_photos(user).filter(
            taken_at__month=today.month, taken_at__day=today.day, taken_at__year__lt=today.year
        )
    ]
    entries += [
        Memory(kind="post", item=post, years_ago=today.year - post.created_at.year)
        for post in BlogPost.objects.filter(
            created_at__month=today.month, created_at__day=today.day, created_at__year__lt=today.year
        )
    ]
    entries.sort(key=lambda entry: entry.years_ago)
    return entries[:limit]
