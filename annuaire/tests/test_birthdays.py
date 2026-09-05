"""Window logic for the home page's upcoming-birthdays widget (#120).

`upcoming_birthdays` takes `today` as a parameter precisely so these can pin a
fixed date instead of depending on the day the suite runs -- note in particular
the rollover and 29 February cases, which are unreachable otherwise.
"""

import datetime

import pytest

from annuaire.birthdays import upcoming_birthdays
from annuaire.models import Person

# A leap year, so 29 February is constructible. Never build a fixture date as
# today.replace(year=...): that raises on 29 February in a common year.
LEAP_YEAR = 1992


def _person(first_name, birth_date, **kwargs):
    return Person.objects.create(
        first_name=first_name,
        last_name=kwargs.pop("last_name", "Busson"),
        birth_date=birth_date,
        **kwargs,
    )


@pytest.mark.django_db
def test_a_birthday_today_is_included():
    today = datetime.date(2026, 6, 10)
    person = _person("Alice", datetime.date(1980, 6, 10))
    entries = upcoming_birthdays(today)
    assert [entry.person for entry in entries] == [person]
    assert entries[0].days_until == 0
    assert entries[0].date == today


@pytest.mark.django_db
def test_the_last_day_of_the_window_is_included_and_the_next_one_is_not():
    today = datetime.date(2026, 6, 10)
    inside = _person("Inside", datetime.date(1980, 6, 17))
    _person("Outside", datetime.date(1980, 6, 18))
    entries = upcoming_birthdays(today)
    assert [entry.person for entry in entries] == [inside]
    assert entries[0].days_until == 7


@pytest.mark.django_db
def test_the_window_rolls_over_into_the_next_year():
    today = datetime.date(2026, 12, 28)
    person = _person("Alice", datetime.date(1980, 1, 2))
    entries = upcoming_birthdays(today)
    assert [entry.person for entry in entries] == [person]
    assert entries[0].date == datetime.date(2027, 1, 2)
    assert entries[0].days_until == 5


@pytest.mark.django_db
def test_a_29_february_birthday_is_observed_on_28_february_in_a_common_year():
    today = datetime.date(2026, 2, 25)  # 2026 is not a leap year
    person = _person("Alice", datetime.date(LEAP_YEAR, 2, 29))
    entries = upcoming_birthdays(today)
    assert [entry.person for entry in entries] == [person]
    assert entries[0].date == datetime.date(2026, 2, 28)


@pytest.mark.django_db
def test_a_29_february_birthday_falls_on_its_own_date_in_a_leap_year():
    today = datetime.date(2028, 2, 25)  # 2028 is a leap year
    person = _person("Alice", datetime.date(LEAP_YEAR, 2, 29))
    entries = upcoming_birthdays(today)
    assert [entry.person for entry in entries] == [person]
    assert entries[0].date == datetime.date(2028, 2, 29)


@pytest.mark.django_db
def test_deceased_people_are_excluded():
    today = datetime.date(2026, 6, 10)
    _person("Alice", datetime.date(1900, 6, 11), deceased=True)
    assert upcoming_birthdays(today) == []


@pytest.mark.django_db
def test_people_without_a_birth_date_are_never_matched():
    today = datetime.date(2026, 6, 10)
    Person.objects.create(first_name="Alice", last_name="Busson")
    assert upcoming_birthdays(today) == []


@pytest.mark.django_db
def test_entries_are_ordered_by_proximity_then_name():
    today = datetime.date(2026, 6, 10)
    later = _person("Zoe", datetime.date(1980, 6, 12))
    sooner_b = _person("Bob", datetime.date(1980, 6, 11), last_name="Bernard")
    sooner_a = _person("Ana", datetime.date(1980, 6, 11), last_name="Alard")
    entries = upcoming_birthdays(today)
    assert [entry.person for entry in entries] == [sooner_a, sooner_b, later]


@pytest.mark.django_db
def test_a_non_positive_window_matches_nobody_rather_than_everybody():
    # An empty Q() is a match-everything filter -- without the guard this would
    # put the whole directory in the widget.
    today = datetime.date(2026, 6, 10)
    _person("Alice", datetime.date(1980, 6, 10))
    assert upcoming_birthdays(today, days=0) == []
    assert upcoming_birthdays(today, days=-3) == []


@pytest.mark.django_db
def test_the_window_length_is_configurable():
    today = datetime.date(2026, 6, 10)
    _person("Alice", datetime.date(1980, 6, 14))
    assert upcoming_birthdays(today, days=3) == []
    assert len(upcoming_birthdays(today, days=5)) == 1
