from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

import annuaire.management.commands.geocode_person_addresses as command_module


def run_command():
    out = StringIO()
    call_command("geocode_person_addresses", stdout=out)
    return out.getvalue()


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.mark.django_db
def test_geocodes_addresses_missing_coordinates(person, monkeypatch):
    person.postal_address = "8 Boulevard du Port, 80000 Amiens"
    person.save()

    def fake_get(url, params=None, timeout=None):
        return _FakeResponse({"features": [{"geometry": {"coordinates": [2.062821, 49.031624]}}]})

    monkeypatch.setattr(command_module.requests, "get", fake_get)

    run_command()

    person.refresh_from_db()
    assert person.longitude == Decimal("2.062821")
    assert person.latitude == Decimal("49.031624")


@pytest.mark.django_db
def test_skips_persons_already_geocoded(person, monkeypatch):
    person.postal_address = "8 Boulevard du Port, 80000 Amiens"
    person.latitude = Decimal("1.0")
    person.longitude = Decimal("1.0")
    person.save()

    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        return _FakeResponse({"features": []})

    monkeypatch.setattr(command_module.requests, "get", fake_get)

    run_command()

    assert calls == []


@pytest.mark.django_db
def test_skips_persons_without_an_address(person, monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        return _FakeResponse({"features": []})

    monkeypatch.setattr(command_module.requests, "get", fake_get)

    run_command()

    assert calls == []


@pytest.mark.django_db
def test_handles_unresolved_address(person, monkeypatch):
    person.postal_address = "adresse imaginaire"
    person.save()

    def fake_get(url, params=None, timeout=None):
        return _FakeResponse({"features": []})

    monkeypatch.setattr(command_module.requests, "get", fake_get)

    output = run_command()

    person.refresh_from_db()
    assert person.latitude is None
    assert person.longitude is None
    assert "Non résolu" in output


@pytest.mark.django_db
def test_handles_request_failure_gracefully(person, monkeypatch):
    import requests

    person.postal_address = "8 Boulevard du Port, 80000 Amiens"
    person.save()

    def fake_get(url, params=None, timeout=None):
        raise requests.RequestException("network down")

    monkeypatch.setattr(command_module.requests, "get", fake_get)

    output = run_command()

    person.refresh_from_db()
    assert person.latitude is None
    assert "Non résolu" in output
