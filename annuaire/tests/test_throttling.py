"""Rate limiting for unauthenticated email-sending views (9.8)."""

import pytest
from django.core import mail
from django.urls import reverse

from annuaire.throttling import GLOBAL_HOURLY_LIMIT, PER_EMAIL_HOURLY_LIMIT


def _reset_password(client, email="alice@example.com"):
    return client.post(reverse("password-reset"), {"email": email})


def _magic_link(client, email="alice@example.com"):
    return client.post(reverse("magic-link-request"), {"email": email})


@pytest.mark.django_db
def test_password_reset_is_allowed_under_the_limit(client, person):
    for _ in range(PER_EMAIL_HOURLY_LIMIT):
        response = _reset_password(client)
        assert response.status_code == 302


@pytest.mark.django_db
def test_password_reset_is_throttled_over_the_per_email_hourly_limit(client, person):
    for _ in range(PER_EMAIL_HOURLY_LIMIT):
        _reset_password(client)

    response = _reset_password(client)

    assert response.status_code == 429
    assert "Trop de tentatives" in response.content.decode()


@pytest.mark.django_db
def test_a_throttled_request_sends_no_email(client, person):
    for _ in range(PER_EMAIL_HOURLY_LIMIT):
        _reset_password(client)
    mail.outbox.clear()

    _reset_password(client)

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_the_refusal_message_is_identical_for_an_unknown_email(client, person):
    for _ in range(PER_EMAIL_HOURLY_LIMIT):
        _reset_password(client, email="alice@example.com")
    for _ in range(PER_EMAIL_HOURLY_LIMIT):
        _reset_password(client, email="nobody@example.com")

    known = _reset_password(client, email="alice@example.com")
    unknown = _reset_password(client, email="nobody@example.com")

    assert known.status_code == unknown.status_code == 429
    assert "Trop de tentatives" in known.content.decode()
    assert "Trop de tentatives" in unknown.content.decode()


@pytest.mark.django_db
def test_different_emails_have_independent_hourly_counters(client, person, other_person):
    for _ in range(PER_EMAIL_HOURLY_LIMIT):
        _reset_password(client, email=person.email)

    response = _reset_password(client, email=other_person.email)

    assert response.status_code == 302


@pytest.mark.django_db
def test_different_endpoints_have_independent_counters(client, person):
    for _ in range(PER_EMAIL_HOURLY_LIMIT):
        _reset_password(client, email=person.email)

    response = _magic_link(client, email=person.email)

    assert response.status_code == 302


@pytest.mark.django_db
def test_global_circuit_breaker_trips_across_many_distinct_emails(client, db):
    for i in range(GLOBAL_HOURLY_LIMIT):
        _reset_password(client, email=f"user{i}@example.com")

    response = _reset_password(client, email="one-more@example.com")

    assert response.status_code == 429


@pytest.mark.django_db
def test_signup_is_throttled_before_the_account_existence_check(client, db):
    payload = {"email": "unknown@example.com", "password": "StrongP@ss1!", "password_confirm": "StrongP@ss1!"}
    for _ in range(PER_EMAIL_HOURLY_LIMIT):
        client.post(reverse("signup"), payload)

    response = client.post(reverse("signup"), payload)

    assert response.status_code == 429
    assert "Trop de tentatives" in response.content.decode()
