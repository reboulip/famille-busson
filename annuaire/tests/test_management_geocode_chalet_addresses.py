from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

import annuaire.management.commands.geocode_chalet_addresses as command_module


def run_command():
    out = StringIO()
    call_command("geocode_chalet_addresses", stdout=out)
    return out.getvalue()


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.mark.django_db
def test_geocodes_addresses_missing_coordinates(chalet, monkeypatch):
    chalet.address = "8 Boulevard du Port, 80000 Amiens"
    chalet.save()

    def fake_get(url, params=None, timeout=None):
        return _FakeResponse({"features": [{"geometry": {"coordinates": [2.062821, 49.031624]}}]})

    monkeypatch.setattr(command_module.requests, "get", fake_get)

    run_command()

    chalet.refresh_from_db()
    assert chalet.longitude == Decimal("2.062821")
    assert chalet.latitude == Decimal("49.031624")


@pytest.mark.django_db
def test_skips_chalets_already_geocoded(chalet, monkeypatch):
    chalet.address = "8 Boulevard du Port, 80000 Amiens"
    chalet.latitude = Decimal("1.0")
    chalet.longitude = Decimal("1.0")
    chalet.save()

    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        return _FakeResponse({"features": []})

    monkeypatch.setattr(command_module.requests, "get", fake_get)

    run_command()

    assert calls == []


@pytest.mark.django_db
def test_skips_chalets_without_an_address(db, monkeypatch):
    from annuaire.models import Chalet

    Chalet.objects.create(name="Chalet sans adresse", address="")

    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        return _FakeResponse({"features": []})

    monkeypatch.setattr(command_module.requests, "get", fake_get)

    run_command()

    assert calls == []


@pytest.mark.django_db
def test_handles_unresolved_address(chalet, monkeypatch):
    chalet.address = "adresse imaginaire"
    chalet.save()

    def fake_get(url, params=None, timeout=None):
        return _FakeResponse({"features": []})

    monkeypatch.setattr(command_module.requests, "get", fake_get)

    output = run_command()

    chalet.refresh_from_db()
    assert chalet.latitude is None
    assert chalet.longitude is None
    assert "Non résolu" in output


@pytest.mark.django_db
def test_handles_request_failure_gracefully(chalet, monkeypatch):
    import requests

    chalet.address = "8 Boulevard du Port, 80000 Amiens"
    chalet.save()

    def fake_get(url, params=None, timeout=None):
        raise requests.RequestException("network down")

    monkeypatch.setattr(command_module.requests, "get", fake_get)

    output = run_command()

    chalet.refresh_from_db()
    assert chalet.latitude is None
    assert "Non résolu" in output
