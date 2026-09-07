"""Shared aggregator behind the unified calendar (page, AJAX refresh, and
12.5's iCal feed): one query per source type (events, chalet présences,
birthdays), merged into one list of a shared entry shape.

`annuaire` must not gain a hard top-level dependency on `events` -- the same
posture as activity.py/memories.py's cross-app imports -- so `events.access`
is imported lazily, inside the function body.
"""

from __future__ import annotations

import calendar
import datetime
from typing import NamedTuple

from django.urls import reverse
from django.utils import timezone

from .models import Person, PresencePSV

VALID_TYPES = {"event", "presence", "birthday"}


class CalendarEntry(NamedTuple):
    type: str  # "event" | "presence" | "birthday"
    title: str
    subtitle: str
    start: str  # ISO date or datetime string
    end: str  # ISO date or datetime string, INCLUSIVE
    all_day: bool
    url: str
    uid: str


def parse_types_param(raw: str | None) -> set[str] | None:
    """Parse a `?types=event,presence,birthday` query string into a set, or
    None for "no filter" (every type). Shared by the calendar page/AJAX view
    and 12.5's iCal feed, so a subscriber's `?types=` narrows both the same
    way."""
    if not raw:
        return None
    parsed = {t.strip() for t in raw.split(",") if t.strip() in VALID_TYPES}
    return parsed or None


def _event_entries(
    user, start: datetime.date, end: datetime.date, host: str | None, *, strict: bool
) -> list[CalendarEntry]:
    from events.access import accessible_events

    start_dt = timezone.make_aware(datetime.datetime.combine(start, datetime.time.min))
    end_dt = timezone.make_aware(datetime.datetime.combine(end, datetime.time.max))
    events_qs = accessible_events(user, bypass_staff=not strict).overlapping(start_dt, end_dt)
    return [
        CalendarEntry(
            type="event",
            title=event.title,
            subtitle=event.location,
            start=event.start.isoformat(),
            end=event.end.isoformat(),
            all_day=event.all_day,
            url=reverse("event-detail", kwargs={"pk": event.pk}),
            uid=_uid(f"event-{event.pk}", host),
        )
        for event in events_qs
    ]


def _presence_entries(start: datetime.date, end: datetime.date, host: str | None) -> list[CalendarEntry]:
    presences = PresencePSV.objects.filter(start_date__lte=end, end_date__gte=start).select_related("person", "chalet")
    return [
        CalendarEntry(
            type="presence",
            title=str(presence.person),
            subtitle=presence.chalet.name,
            start=presence.start_date.isoformat(),
            end=presence.end_date.isoformat(),
            all_day=True,
            url=reverse("chalet-detail", kwargs={"pk": presence.chalet_id}),
            uid=_uid(f"presence-{presence.pk}", host),
        )
        for presence in presences
    ]


def _birthday_entries(start: datetime.date, end: datetime.date, host: str | None) -> list[CalendarEntry]:
    """Occurrences of each non-deceased person's birthday inside [start, end],
    expanded in Python rather than as a per-day OR-chain query (fine for
    birthdays.py's 8-day window, pathological for this feature's multi-month
    one). A 29 February birth date is observed on 28 February in a common
    year -- same rule as annuaire.birthdays._observed_month_day, applied in
    the forward direction (birth date -> occurrence date) instead of the
    reverse."""
    persons = Person.objects.exclude(deceased=True).exclude(birth_date__isnull=True)
    entries = []
    for person in persons:
        birth_date = person.birth_date
        for year in range(start.year, end.year + 1):
            try:
                occurrence = datetime.date(year, birth_date.month, birth_date.day)
            except ValueError:
                if birth_date.month == 2 and birth_date.day == 29 and not calendar.isleap(year):
                    occurrence = datetime.date(year, 2, 28)
                else:
                    continue
            if start <= occurrence <= end:
                entries.append(
                    CalendarEntry(
                        type="birthday",
                        title=f"Anniversaire de {person}",
                        subtitle="",
                        start=occurrence.isoformat(),
                        end=occurrence.isoformat(),
                        all_day=True,
                        url=reverse("personne-detail", kwargs={"pk": person.pk}),
                        uid=_uid(f"birthday-{person.pk}-{year}", host),
                    )
                )
    return entries


def _uid(base: str, host: str | None) -> str:
    return f"{base}@{host}" if host else base


def build_calendar_entries(
    user,
    start: datetime.date,
    end: datetime.date,
    types: set[str] | None = None,
    host: str | None = None,
    strict: bool = False,
) -> list[CalendarEntry]:
    """Entries from every source type overlapping [start, end] (both dates
    inclusive), access-scoped per source, merged and sorted by start.

    `types`: a subset of VALID_TYPES to include, or None for all three.
    `host`: if given, embedded in each entry's uid as `<base>@<host>` -- the
    stable per-item id iCal clients use to update rather than duplicate an
    entry on refresh (see 12.5). Omit when a real host isn't available (the
    uid is still internally consistent, just not globally unique).
    `strict`: when True, a staff/superuser account does NOT get the usual
    "see everything" bypass on events -- used by the iCal feed (12.5), where
    the recipient is one specific account piping data into a third-party
    calendar service rather than browsing the site in-app.
    """
    wanted = types if types is not None else VALID_TYPES
    entries: list[CalendarEntry] = []
    if "event" in wanted:
        entries += _event_entries(user, start, end, host, strict=strict)
    if "presence" in wanted:
        entries += _presence_entries(start, end, host)
    if "birthday" in wanted:
        entries += _birthday_entries(start, end, host)
    entries.sort(key=lambda entry: entry.start)
    return entries
