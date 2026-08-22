"""Serialize Person/Chalet records into map marker groups for carte.html.

Records sharing (near-)identical coordinates are grouped into a single marker so
the map shows one pin per address instead of one per person/chalet. See
docs/data_model.md for the underlying models.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from decimal import Decimal

from django.templatetags.static import static
from django.urls import reverse

from .models import Chalet, Person

# ~1.1m precision -- distinguishes separate buildings while absorbing geocoder
# jitter (different providers can return the same address with coordinates that
# differ in the 5th/6th decimal).
_QUANTIZE = Decimal("0.00001")

# Chalets without a photo carry this sentinel instead of an image URL (there's no
# default chalet photo asset the way there is a default person avatar) -- map_init.js
# renders the 🏔️ placeholder used everywhere else in the app for this prefix.
EMOJI_PREFIX = "emoji::"


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


def build_chalet_map_groups() -> list[dict]:
    chalets = Chalet.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True).order_by("name", "pk")
    return _group_by_coordinates(
        chalets,
        key_func=lambda chalet: (_quantize(chalet.latitude), _quantize(chalet.longitude)),
        entry_func=lambda chalet: {
            "name": chalet.name,
            "url": reverse("chalet-detail", kwargs={"pk": chalet.pk}),
            "avatar": chalet.photo.url if chalet.photo else f"{EMOJI_PREFIX}🏔️",
        },
    )
