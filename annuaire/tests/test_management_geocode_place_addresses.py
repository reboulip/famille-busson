from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command


def run_command():
    out = StringIO()
    call_command("geocode_place_addresses", stdout=out)
    return out.getvalue()


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.mark.django_db
def test_geocodes_addresses_missing_coordinates(place, monkeypatch):
    place.address = "8 Boulevard du Port, 80000 Amiens"
    place.save()

    def fake_get(url, params=None, timeout=None):
        return _FakeResponse({"features": [{"geometry": {"coordinates": [2.062821, 49.031624]}}]})

    monkeypatch.setattr("annuaire.geocoding.requests.get", fake_get)

    run_command()

    place.refresh_from_db()
    assert place.longitude == Decimal("2.062821")
    assert place.latitude == Decimal("49.031624")


@pytest.mark.django_db
def test_skips_places_already_geocoded(place, monkeypatch):
    place.address = "8 Boulevard du Port, 80000 Amiens"
    place.latitude = Decimal("1.0")
    place.longitude = Decimal("1.0")
    place.save()

    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        return _FakeResponse({"features": []})

    monkeypatch.setattr("annuaire.geocoding.requests.get", fake_get)

    run_command()

    assert calls == []


@pytest.mark.django_db
def test_skips_places_without_an_address(db, monkeypatch):
    from annuaire.models import Place

    Place.objects.create(name="Résidence sans adresse", address="")

    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        return _FakeResponse({"features": []})

    monkeypatch.setattr("annuaire.geocoding.requests.get", fake_get)

    run_command()

    assert calls == []


@pytest.mark.django_db
def test_handles_unresolved_address(place, monkeypatch):
    place.address = "adresse imaginaire"
    place.save()

    def fake_get(url, params=None, timeout=None):
        return _FakeResponse({"features": []})

    monkeypatch.setattr("annuaire.geocoding.requests.get", fake_get)

    output = run_command()

    place.refresh_from_db()
    assert place.latitude is None
    assert place.longitude is None
    assert "Non résolu" in output


@pytest.mark.django_db
def test_handles_request_failure_gracefully(place, monkeypatch):
    import requests

    place.address = "8 Boulevard du Port, 80000 Amiens"
    place.save()

    def fake_get(url, params=None, timeout=None):
        raise requests.RequestException("network down")

    monkeypatch.setattr("annuaire.geocoding.requests.get", fake_get)

    output = run_command()

    place.refresh_from_db()
    assert place.latitude is None
    assert "Non résolu" in output
