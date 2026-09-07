import datetime

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from events.models import Event


def _aware(*args):
    return timezone.make_aware(datetime.datetime(*args), datetime.UTC)


@pytest.mark.django_db
def test_event_str_returns_title():
    event = Event.objects.create(title="Fête des voisins", start=_aware(2026, 6, 1, 12, 0))
    assert str(event) == "Fête des voisins"


@pytest.mark.django_db
def test_event_save_defaults_end_to_start_when_omitted():
    event = Event.objects.create(title="Sans fin précisée", start=_aware(2026, 6, 1, 12, 0))
    assert event.end == event.start


@pytest.mark.django_db
def test_event_save_keeps_explicit_end():
    start = _aware(2026, 6, 1, 12, 0)
    end = _aware(2026, 6, 1, 18, 0)
    event = Event.objects.create(title="Avec fin", start=start, end=end)
    assert event.end == end


@pytest.mark.django_db
def test_event_save_all_day_snaps_to_local_day_bounds():
    start = _aware(2026, 6, 1, 14, 30)
    event = Event.objects.create(title="Journée entière", start=start, all_day=True)
    local_start = timezone.localtime(event.start)
    local_end = timezone.localtime(event.end)
    assert (local_start.hour, local_start.minute, local_start.second) == (0, 0, 0)
    assert (local_end.hour, local_end.minute, local_end.second) == (23, 59, 59)
    assert local_start.date() == local_end.date()


@pytest.mark.django_db
def test_event_clean_rejects_end_before_start():
    event = Event(title="Incohérent", start=_aware(2026, 6, 2, 12, 0), end=_aware(2026, 6, 1, 12, 0))
    with pytest.raises(ValidationError):
        event.full_clean()


@pytest.mark.django_db
def test_event_queryset_upcoming_excludes_past_events():
    past = Event.objects.create(title="Passé", start=_aware(2020, 1, 1, 12, 0))
    future = Event.objects.create(title="Futur", start=_aware(2030, 1, 1, 12, 0))
    now = _aware(2026, 1, 1, 0, 0)
    upcoming_titles = set(Event.objects.upcoming(now).values_list("title", flat=True))
    assert future.title in upcoming_titles
    assert past.title not in upcoming_titles


@pytest.mark.django_db
def test_event_queryset_past_excludes_future_events():
    past = Event.objects.create(title="Passé", start=_aware(2020, 1, 1, 12, 0))
    future = Event.objects.create(title="Futur", start=_aware(2030, 1, 1, 12, 0))
    now = _aware(2026, 1, 1, 0, 0)
    past_titles = set(Event.objects.past(now).values_list("title", flat=True))
    assert past.title in past_titles
    assert future.title not in past_titles


@pytest.mark.django_db
def test_event_queryset_overlapping_finds_events_spanning_the_window():
    event = Event.objects.create(title="Weekend", start=_aware(2026, 6, 5, 9, 0), end=_aware(2026, 6, 7, 18, 0))
    matches = Event.objects.overlapping(_aware(2026, 6, 6, 0, 0), _aware(2026, 6, 6, 23, 59))
    assert event in matches


@pytest.mark.django_db
def test_event_meta_ordering_is_by_start():
    later = Event.objects.create(title="Plus tard", start=_aware(2026, 6, 10, 12, 0))
    earlier = Event.objects.create(title="Plus tôt", start=_aware(2026, 6, 1, 12, 0))
    assert list(Event.objects.all()) == [earlier, later]
