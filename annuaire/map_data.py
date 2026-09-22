"""Serialize Person/Place records into map marker groups for carte.html.

Records sharing (near-)identical coordinates are grouped into a single marker so
the map shows one pin per address instead of one per person/place. See
docs/data_model.md for the underlying models.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from decimal import Decimal

from django.templatetags.static import static
from django.urls import reverse

from .models import Person, Place

# ~1.1m precision -- distinguishes separate buildings while absorbing geocoder
# jitter (different providers can return the same address with coordinates that
# differ in the 5th/6th decimal).
_QUANTIZE = Decimal("0.00001")

# Places without a photo carry this sentinel instead of an image URL (there's no
# default place photo asset the way there is a default person avatar) -- map_init.js
# draws the ridge mark for it, the same placeholder used everywhere else in the app.
# Was "emoji::🏔️" until the Alpenglow design pass: an emoji renders as a tofu box on
# any system without an emoji font, and cannot follow the theme's colours.
PLACEHOLDER_PREFIX = "placeholder::"
PLACE_PLACEHOLDER = f"{PLACEHOLDER_PREFIX}place"
# Keep this suffix in sync with map_init.js's own PLACEHOLDER_PREFIX branch --
# both files carry a comment saying so.
EVENT_PLACEHOLDER = f"{PLACEHOLDER_PREFIX}event"


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_QUANTIZE)


def _group_by_coordinates[T](
    items: Iterable[T],
    key_func: Callable[[T], tuple[Decimal, Decimal]],
    entry_func: Callable[[T], dict],
) -> list[dict]:
    """Group items sharing a quantized (lat, lon) key. `items` must already be in
    deterministic order -- groups come out ordered by their first member's position,
    entries within a group keep the source order."""
    groups: dict[tuple[Decimal, Decimal], list[dict]] = {}
    order: list[tuple[Decimal, Decimal]] = []
    for item in items:
        key = key_func(item)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(entry_func(item))
    return [{"lat": float(key[0]), "lon": float(key[1]), "entries": groups[key]} for key in order]


def build_person_map_groups() -> list[dict]:
    persons = (
        Person.objects.exclude(latitude__isnull=True)
        .exclude(longitude__isnull=True)
        .order_by("last_name", "first_name", "pk")
    )
    return _group_by_coordinates(
        persons,
        key_func=lambda person: (_quantize(person.latitude), _quantize(person.longitude)),
        entry_func=lambda person: {
            "name": f"{person.first_name} {person.last_name}",
            "url": reverse("personne-detail", kwargs={"pk": person.pk}),
            "avatar": person.profile_photo.url if person.profile_photo else static("default_profile_picture.png"),
        },
    )


def build_place_map_groups() -> list[dict]:
    places = Place.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True).order_by("name", "pk")
    return _group_by_coordinates(
        places,
        key_func=lambda place: (_quantize(place.latitude), _quantize(place.longitude)),
        entry_func=lambda place: {
            "name": place.name,
            "url": reverse("place-detail", kwargs={"pk": place.pk}),
            "avatar": place.photo.url if place.photo else PLACE_PLACEHOLDER,
        },
    )


def build_event_map_groups(user) -> list[dict]:
    """Unlike persons/places, events are access-restricted -- takes `user` and
    scopes through events.access.accessible_events(), lazy-imported so
    `annuaire` gains no hard top-level dependency on `events`. Events with no
    geocoded coordinates (a free-text-only location the address picker never
    resolved) are excluded entirely, never plotted at (0, 0)."""
    from events.access import accessible_events

    events = (
        accessible_events(user).exclude(latitude__isnull=True).exclude(longitude__isnull=True).order_by("start", "pk")
    )
    return _group_by_coordinates(
        events,
        key_func=lambda event: (_quantize(event.latitude), _quantize(event.longitude)),
        entry_func=lambda event: {
            "name": event.title,
            "url": reverse("event-detail", kwargs={"pk": event.pk}),
            "avatar": EVENT_PLACEHOLDER,
        },
    )
