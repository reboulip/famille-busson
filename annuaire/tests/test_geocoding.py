from decimal import Decimal

import pytest
import requests

from annuaire import geocoding


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _ban_feature(lon, lat, *, score=0.9, label="8 Boulevard du Port 80000 Amiens", context="Somme, Hauts-de-France"):
    return {
        "geometry": {"coordinates": [lon, lat]},
        "properties": {"label": label, "context": context, "score": score, "name": "8 Boulevard du Port"},
    }


def _photon_feature(lon, lat, *, name="Pariser Platz", city="Berlin", country="Allemagne"):
    return {
        "geometry": {"coordinates": [lon, lat]},
        "properties": {"name": name, "city": city, "country": country, "postcode": "10117"},
    }


def test_geocode_returns_none_when_no_provider_resolves(monkeypatch):
    monkeypatch.setattr("annuaire.geocoding.requests.get", lambda *a, **k: _FakeResponse({"features": []}))
    assert geocoding.geocode("adresse imaginaire") is None


def test_geocode_uses_ban_result_when_confident(monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(url)
        return _FakeResponse({"features": [_ban_feature(2.062821, 49.031624)]})

    monkeypatch.setattr("annuaire.geocoding.requests.get", fake_get)
    result = geocoding.geocode("8 Boulevard du Port, 80000 Amiens")
    assert result == (Decimal("49.031624"), Decimal("2.062821"))
    # Photon must not be queried when BAN already returned a confident match.
    assert calls == [geocoding.BAN_SEARCH_URL]


def test_geocode_coordinate_order_is_lat_lon_not_lon_lat(monkeypatch):
    monkeypatch.setattr(
        "annuaire.geocoding.requests.get",
        lambda *a, **k: _FakeResponse({"features": [_ban_feature(2.062821, 49.031624)]}),
    )
    result = geocoding.geocode("8 Boulevard du Port, 80000 Amiens")
    assert result is not None
    lat, lon = result
    assert lat == Decimal("49.031624")
    assert lon == Decimal("2.062821")


def test_search_addresses_falls_back_to_photon_when_ban_empty(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        if url == geocoding.BAN_SEARCH_URL:
            return _FakeResponse({"features": []})
        return _FakeResponse({"features": [_photon_feature(13.3777, 52.5163)]})

    monkeypatch.setattr("annuaire.geocoding.requests.get", fake_get)
    results = geocoding.search_addresses("Pariser Platz, Berlin")
    assert len(results) == 1
    assert results[0].source == "worldwide"
    assert results[0].lat == Decimal("52.5163")
    assert results[0].lon == Decimal("13.3777")


def test_search_addresses_falls_back_to_photon_when_ban_score_low(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        if url == geocoding.BAN_SEARCH_URL:
            return _FakeResponse({"features": [_ban_feature(2.0, 49.0, score=0.1)]})
        return _FakeResponse({"features": [_photon_feature(13.3777, 52.5163)]})

    monkeypatch.setattr("annuaire.geocoding.requests.get", fake_get)
    results = geocoding.search_addresses("Pariser Platz, Berlin")
    assert results[0].source == "worldwide"


def test_search_addresses_keeps_weak_ban_result_when_photon_also_empty(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        if url == geocoding.BAN_SEARCH_URL:
            return _FakeResponse({"features": [_ban_feature(2.0, 49.0, score=0.1)]})
        return _FakeResponse({"features": []})

    monkeypatch.setattr("annuaire.geocoding.requests.get", fake_get)
    results = geocoding.search_addresses("adresse ambigüe")
    assert len(results) == 1
    assert results[0].source == "ban"


def test_search_addresses_swallows_provider_failure(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        raise requests.RequestException("network down")

    monkeypatch.setattr("annuaire.geocoding.requests.get", fake_get)
    assert geocoding.search_addresses("peu importe") == []


def test_search_addresses_swallows_bad_json(monkeypatch):
    class _BadJsonResponse:
        def raise_for_status(self):
            pass

        def json(self):
            raise ValueError("not json")

    monkeypatch.setattr("annuaire.geocoding.requests.get", lambda *a, **k: _BadJsonResponse())
    assert geocoding.search_addresses("peu importe") == []


@pytest.mark.parametrize("limit", [1, 5])
def test_geocode_uses_limit_one_regardless_of_search_addresses_default(monkeypatch, limit):
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["limit"] = params.get("limit")
        return _FakeResponse({"features": [_ban_feature(2.0, 49.0)]})

    monkeypatch.setattr("annuaire.geocoding.requests.get", fake_get)
    geocoding.geocode("une adresse")
    assert captured["limit"] == 1
