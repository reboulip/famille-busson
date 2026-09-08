"""'Quoi de neuf' — new publications, comments, documents, photos and members
since the viewer's last visit.

Modelled on annuaire/memories.py: `since` is an explicit parameter rather than
read from the clock or from the account here, so this can be tested against a
fixed cutoff instead of the current time.
"""

from __future__ import annotations

import datetime
from typing import NamedTuple


class FeedEntry(NamedTuple):
    kind: str  # "post" | "comment" | "document" | "album_photos" | "member"
    item: object
    timestamp: datetime.datetime
    count: int = 1  # >1 only for "album_photos"


def activity_since(user, since: datetime.datetime | None, limit: int = 20) -> list[FeedEntry]:
    """Entries newer than `since` (or all history if `since` is None), one
    source query each, merged and sorted most-recent-first, capped at `limit`.

    Every source is capped at `limit` *before* merging -- never
    `QuerySet.union()` across these heterogeneous models. Each access helper
    is called once and reused, since documents.access.accessible_categories()
    walks every category in Python and a per-row call would be a performance
    cliff.
    """
    # Lazy-imported, same as memories.py's own cross-app imports -- annuaire
    # must not gain a hard top-level dependency on photos/publications/documents.
    from django.db.models import Count, Max, Q

    from documents.access import accessible_documents
    from photos.access import accessible_albums
    from publications.models import BlogPost, Comment

    from .models import Person

    entries: list[FeedEntry] = []

    posts_qs = BlogPost.objects.order_by("-created_at")
    if since is not None:
        posts_qs = posts_qs.filter(created_at__gt=since)
    entries += [FeedEntry(kind="post", item=post, timestamp=post.created_at) for post in posts_qs[:limit]]

    comments_qs = Comment.objects.select_related("post", "author").order_by("-created_at")
    if since is not None:
        comments_qs = comments_qs.filter(created_at__gt=since)
    entries += [
        FeedEntry(kind="comment", item=comment, timestamp=comment.created_at) for comment in comments_qs[:limit]
    ]

    documents_qs = accessible_documents(user).order_by("-created_at")
    if since is not None:
        documents_qs = documents_qs.filter(created_at__gt=since)
    entries += [
        FeedEntry(kind="document", item=document, timestamp=document.created_at) for document in documents_qs[:limit]
    ]

    # Aggregated per album, never per photo -- a single bulk upload would
    # otherwise bury every other source in the merged feed.
    since_filter = Q(photos__uploaded_at__gt=since) if since is not None else Q()
    albums_with_new_photos = accessible_albums(user).annotate(
        new_photo_count=Count("photos", filter=since_filter),
        latest_photo_at=Max("photos__uploaded_at", filter=since_filter),
    )
    entries += [
        FeedEntry(kind="album_photos", item=album, timestamp=album.latest_photo_at, count=album.new_photo_count)
        for album in albums_with_new_photos.order_by("-latest_photo_at")[:limit]
        if album.latest_photo_at is not None
    ]

    # Excludes the viewer's own profile: telling someone they joined the
    # directory, in their own "what's new" feed, isn't informative to them.
    viewer_person = getattr(user, "profile", None)
    members_qs = Person.objects.order_by("-created_at")
    if viewer_person is not None:
        members_qs = members_qs.exclude(pk=viewer_person.pk)
    if since is not None:
        members_qs = members_qs.filter(created_at__gt=since)
    entries += [FeedEntry(kind="member", item=person, timestamp=person.created_at) for person in members_qs[:limit]]

    entries.sort(key=lambda entry: entry.timestamp, reverse=True)
    return entries[:limit]
