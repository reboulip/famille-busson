from datetime import datetime, timedelta

import pytest
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator

from annuaire.tokens import (
    AnyOfTokenChecker,
    magic_link_token_generator,
    password_setup_token_checker,
    self_service_reset_token_generator,
)


@pytest.mark.django_db
def test_self_service_token_is_accepted_by_its_own_generator(account):
    token = self_service_reset_token_generator.make_token(account)
    assert self_service_reset_token_generator.check_token(account, token)


@pytest.mark.django_db
def test_self_service_token_expires_after_its_own_timeout(account, monkeypatch):
    token = self_service_reset_token_generator.make_token(account)
    future = datetime.now() + timedelta(seconds=settings.SELF_SERVICE_RESET_TIMEOUT + 60)
    monkeypatch.setattr(self_service_reset_token_generator, "_now", lambda: future)
    assert not self_service_reset_token_generator.check_token(account, token)


@pytest.mark.django_db
def test_self_service_token_rejected_by_magic_link_generator(account):
    token = self_service_reset_token_generator.make_token(account)
    assert not magic_link_token_generator.check_token(account, token)


@pytest.mark.django_db
def test_magic_link_token_rejected_by_self_service_generator(account):
    token = magic_link_token_generator.make_token(account)
    assert not self_service_reset_token_generator.check_token(account, token)


@pytest.mark.django_db
def test_any_of_token_checker_accepts_either_wrapped_generator(account):
    checker = AnyOfTokenChecker(default_token_generator, self_service_reset_token_generator)
    default_token = default_token_generator.make_token(account)
    self_service_token = self_service_reset_token_generator.make_token(account)
    assert checker.check_token(account, default_token)
    assert checker.check_token(account, self_service_token)


@pytest.mark.django_db
def test_any_of_token_checker_rejects_a_token_from_neither_generator(account):
    checker = AnyOfTokenChecker(default_token_generator, self_service_reset_token_generator)
    magic_token = magic_link_token_generator.make_token(account)
    assert not checker.check_token(account, magic_token)


@pytest.mark.django_db
def test_password_setup_token_checker_wraps_default_and_self_service(account):
    default_token = default_token_generator.make_token(account)
    self_service_token = self_service_reset_token_generator.make_token(account)
    assert password_setup_token_checker.check_token(account, default_token)
    assert password_setup_token_checker.check_token(account, self_service_token)
