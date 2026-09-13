"""Address search and geocoding, shared by the address-picker autocomplete
endpoint (`address_search_ajax`) and the `geocode_person_addresses` /
`geocode_place_addresses` backfill commands.

BAN (Base Adresse Nationale, France-only) is the primary/authoritative
provider by default (settings.GEOCODER_PRIMARY = "ban") -- queried first, and
used whenever it returns a confident match, so existing French behaviour is
unchanged byte-for-byte. Photon (OpenStreetMap-based, worldwide, keyless) is
the fallback, queried when the primary comes up empty or unconfident. A
non-French deployment can flip GEOCODER_PRIMARY to "photon" to swap the
roles -- see search_addresses() below.

Both `geocode()` and `search_addresses()` return (latitude, longitude) --
the OPPOSITE order of the GeoJSON `coordinates: [lon, lat]` arrays both
providers respond with. Getting this backwards silently misplaces every
member on the map.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import requests
from django.conf import settings

BAN_SEARCH_URL = "https://api-adresse.data.gouv.fr/search/"
PHOTON_SEARCH_URL = "https://photon.komoot.io/api/"
REQUEST_TIMEOUT_SECONDS = 2
# Below this BAN confidence score, a foreign/unmatched query is worth trying
# against Photon instead of accepting a weak French guess.
BAN_SCORE_FALLBACK_THRESHOLD = 0.4


@dataclass(frozen=True)
class AddressSuggestion:
    label: str
    context: str
    address: str
    lat: Decimal
    lon: Decimal
    source: str  # "ban" or "worldwide"


def _get_features(url: str, params: dict) -> list[dict]:
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json().get("features", [])
    except (requests.RequestException, ValueError):
        return []


def _ban_search(query: str, limit: int) -> list[dict]:
    return _get_features(BAN_SEARCH_URL, {"q": query, "limit": limit})


def _photon_search(query: str, limit: int) -> list[dict]:
    return _get_features(PHOTON_SEARCH_URL, {"q": query, "limit": limit, "lang": "fr"})


def _ban_needs_fallback(features: list[dict]) -> bool:
    if not features:
        return True
    score = features[0].get("properties", {}).get("score")
    return score is not None and score < BAN_SCORE_FALLBACK_THRESHOLD


def _compose_ban_address(properties: dict) -> str:
    name = properties.get("name")
    postcode = properties.get("postcode")
    city = properties.get("city")
    if name and postcode and city:
        return f"{name}, {postcode} {city}"
    return properties.get("label", "")


def _feature_to_suggestion(feature: dict, *, source: str) -> AddressSuggestion | None:
    coordinates = feature.get("geometry", {}).get("coordinates")
    if not coordinates:
        return None
    lon, lat = coordinates[0], coordinates[1]
    properties = feature.get("properties", {})
    if source == "ban":
        label = properties.get("label", "")
        context = properties.get("context", "")
        address = _compose_ban_address(properties)
    else:
        name = properties.get("name", "")
        context = ", ".join(
            part
            for part in (
                properties.get("postcode"),
                properties.get("city"),
                properties.get("state"),
                properties.get("country"),
            )
            if part
        )
        label = ", ".join(part for part in (name, properties.get("city"), properties.get("country")) if part) or name
        address = ", ".join(part for part in (name, context) if part) or label
    return AddressSuggestion(
        label=label,
        context=context,
        address=address,
        lat=Decimal(str(lat)),
        lon=Decimal(str(lon)),
        source=source,
    )


def search_addresses(query: str, limit: int = 5) -> list[AddressSuggestion]:
    """Primary provider first (settings.GEOCODER_PRIMARY, default "ban"); the
    other provider only as a fallback when the primary comes up empty or
    unconfident.

    Read from settings at call time, not cached at import -- so tests can
    @override_settings(GEOCODER_PRIMARY=...) and see it take effect.

    BAN's fallback trigger is a confidence-score threshold (_ban_needs_fallback);
    Photon has no equivalent score, so when Photon is primary the only fallback
    trigger is an empty result set -- the two directions are not symmetric.
    """
    if settings.GEOCODER_PRIMARY == "photon":
        photon_features = _photon_search(query, limit)
        if photon_features:
            return [s for f in photon_features if (s := _feature_to_suggestion(f, source="worldwide")) is not None]

        ban_features = _ban_search(query, limit)
        if ban_features:
            return [s for f in ban_features if (s := _feature_to_suggestion(f, source="ban")) is not None]

        # Both empty -- nothing to fall back to.
        return []

    ban_features = _ban_search(query, limit)
    if not _ban_needs_fallback(ban_features):
        return [s for f in ban_features if (s := _feature_to_suggestion(f, source="ban")) is not None]

    photon_features = _photon_search(query, limit)
    if photon_features:
        return [s for f in photon_features if (s := _feature_to_suggestion(f, source="worldwide")) is not None]

    # Photon also failed/empty -- fall back to whatever BAN gave us, even if weak,
    # rather than returning nothing.
    return [s for f in ban_features if (s := _feature_to_suggestion(f, source="ban")) is not None]


def geocode(address: str) -> tuple[Decimal, Decimal] | None:
    """Best-effort single geocode for management-command backfills. Returns
    (latitude, longitude), or None if neither provider could resolve it."""
    suggestions = search_addresses(address, limit=1)
    if not suggestions:
        return None
    return suggestions[0].lat, suggestions[0].lon
