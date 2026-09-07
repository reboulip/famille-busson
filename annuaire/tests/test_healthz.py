"""Deepened /healthz (9.10) -- annuaire.health."""

import json
from pathlib import Path

import pytest
from django.test import RequestFactory, override_settings
from django.urls import reverse

from annuaire import health


@pytest.mark.django_db
def test_reverse_healthz_resolves():
    assert reverse("healthz") == "/healthz"


@pytest.mark.django_db
def test_all_checks_ok_returns_200_with_ok_status(monkeypatch):
    monkeypatch.setitem(health.CHECKS, "queue", lambda: None)
    response = health.healthz(RequestFactory().get("/healthz"))
    payload = json.loads(response.content)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    assert response["Cache-Control"] == "no-store"
    assert payload["status"] == "ok"
    assert payload["version"] == health.settings.APP_VERSION
    for name in ("database", "cache", "queue", "media_storage", "documents_storage"):
        assert payload["checks"][name]["status"] == "ok"
        assert isinstance(payload["checks"][name]["duration_ms"], float)


@pytest.mark.django_db
def test_a_critical_failure_returns_503_with_error_status(monkeypatch):
    monkeypatch.setitem(health.CHECKS, "queue", lambda: None)
    monkeypatch.setitem(health.CHECKS, "database", lambda: (_ for _ in ()).throw(RuntimeError("db is down")))

    response = health.healthz(RequestFactory().get("/healthz"))
    payload = json.loads(response.content)

    assert response.status_code == 503
    assert payload["status"] == "error"
    assert payload["checks"]["database"]["status"] == "error"
    # Never the raw exception text in the body.
    assert "db is down" not in response.content.decode()


@pytest.mark.django_db
def test_a_non_critical_failure_returns_200_with_degraded_status(monkeypatch):
    monkeypatch.setitem(health.CHECKS, "queue", lambda: "broker-ping-failed")

    response = health.healthz(RequestFactory().get("/healthz"))
    payload = json.loads(response.content)

    assert response.status_code == 200
    assert payload["status"] == "degraded"
    assert payload["checks"]["queue"]["status"] == "error"


@pytest.mark.django_db
def test_a_non_critical_check_raising_an_exception_is_also_degraded_not_error(monkeypatch):
    monkeypatch.setitem(health.CHECKS, "queue", lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    response = health.healthz(RequestFactory().get("/healthz"))
    payload = json.loads(response.content)

    assert response.status_code == 200
    assert payload["status"] == "degraded"
    assert payload["checks"]["queue"]["status"] == "error"


@pytest.mark.django_db
def test_a_critical_check_returning_an_error_code_is_also_a_503(monkeypatch):
    monkeypatch.setitem(health.CHECKS, "queue", lambda: None)
    monkeypatch.setitem(health.CHECKS, "media_storage", lambda: "disk-full")

    response = health.healthz(RequestFactory().get("/healthz"))
    payload = json.loads(response.content)

    assert response.status_code == 503
    assert payload["status"] == "error"
    assert payload["checks"]["media_storage"]["status"] == "error"


@pytest.mark.django_db
def test_cache_probe_detects_a_roundtrip_mismatch(monkeypatch):
    monkeypatch.setitem(health.CHECKS, "queue", lambda: None)
    monkeypatch.setattr(health.cache, "get", lambda key: "wrong-value")

    response = health.healthz(RequestFactory().get("/healthz"))
    payload = json.loads(response.content)

    assert response.status_code == 200
    assert payload["status"] == "degraded"
    assert payload["checks"]["cache"]["status"] == "error"


@pytest.mark.django_db
def test_queue_probe_ok_when_broker_ping_succeeds(monkeypatch):
    monkeypatch.setattr("django_q.brokers.get_broker", lambda: type("B", (), {"ping": lambda self: True})())

    assert health._check_queue() is None


@pytest.mark.django_db
def test_queue_probe_reports_a_failed_ping(monkeypatch):
    monkeypatch.setattr("django_q.brokers.get_broker", lambda: type("B", (), {"ping": lambda self: False})())

    assert health._check_queue() == "broker-ping-failed"


@pytest.mark.django_db
@override_settings(MEDIA_ROOT="/nonexistent-healthz-probe-dir")
def test_media_storage_probe_fails_on_an_unwritable_root(monkeypatch):
    monkeypatch.setitem(health.CHECKS, "queue", lambda: None)

    response = health.healthz(RequestFactory().get("/healthz"))
    payload = json.loads(response.content)

    assert response.status_code == 503
    assert payload["checks"]["media_storage"]["status"] == "error"


@pytest.mark.django_db
@override_settings(DOCUMENTS_ROOT="/nonexistent-healthz-probe-dir")
def test_documents_storage_probe_fails_on_an_unwritable_root(monkeypatch):
    monkeypatch.setitem(health.CHECKS, "queue", lambda: None)

    response = health.healthz(RequestFactory().get("/healthz"))
    payload = json.loads(response.content)

    assert response.status_code == 503
    assert payload["checks"]["documents_storage"]["status"] == "error"


def test_media_storage_probe_leaves_no_file_behind():
    health._check_media_storage()
    leftovers = list(Path(health.settings.MEDIA_ROOT).glob(".healthz-*"))
    assert leftovers == []
