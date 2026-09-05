"""Upcoming-birthday lookup for the home page hub banner.

Kept out of views.py so the window logic can be tested against a fixed date
instead of whatever day the suite happens to run on -- hence `today` being an
explicit parameter rather than read from the clock here.
"""

from __future__ import annotations

import calendar
import datetime
from typing import NamedTuple

from django.db.models import Q

from annuaire.models import Person

BIRTHDAY_WINDOW_DAYS = 8


class UpcomingBirthday(NamedTuple):
    person: Person
    date: datetime.date
    """The occurrence inside the window -- this year's, not the birth date."""
    days_until: int


def _observed_month_day(day: datetime.date) -> tuple[int, int] | None:
    """The extra (month, day) a given window day stands in for, if any.

    A 29 February birthday has no real date in a common year, so it is observed
    on 28 February -- the same rule `send_birthday_reminders` applies.
    """
    if day.month == 2 and day.day == 28 and not calendar.isleap(day.year):
        return (2, 29)
    return None


def upcoming_birthdays(today: datetime.date, days: int = BIRTHDAY_WINDOW_DAYS) -> list[UpcomingBirthday]:
    """People with a birthday in the `days`-day window starting today (today included).

    Ordered by proximity, then by name. Deceased people are excluded.
    """
    if days <= 0:
        # Guard: an empty Q() is a match-everything filter, not a match-nothing one.
        return []

    window = [today + datetime.timedelta(days=offset) for offset in range(days)]

    # Matching on (month, day) rather than a date range is what makes the
    # December-to-January rollover work without any special casing.
    birthday_filter = Q()
    occurrence_of: dict[tuple[int, int], datetime.date] = {}
    for day in window:
        birthday_filter |= Q(birth_date__month=day.month, birth_date__day=day.day)
        occurrence_of.setdefault((day.month, day.day), day)
        observed = _observed_month_day(day)
        if observed is not None:
            birthday_filter |= Q(birth_date__month=observed[0], birth_date__day=observed[1])
            occurrence_of.setdefault(observed, day)

    entries = [
        UpcomingBirthday(
            person=person,
            date=occurrence_of[(person.birth_date.month, person.birth_date.day)],
            days_until=(occurrence_of[(person.birth_date.month, person.birth_date.day)] - today).days,
        )
        for person in Person.objects.filter(birthday_filter).exclude(deceased=True)
    ]
    entries.sort(key=lambda entry: (entry.days_until, entry.person.last_name, entry.person.first_name))
    return entries
