"""CACHES configuration and the accompanying warning system check (9.5) -- every
gunicorn worker held its own independent LocMemCache until this item."""

import environ
from django.core.checks import Warning
from django.test import override_settings

from annuaire.checks import cache_backend_check


def test_env_cache_resolves_a_redis_url_to_djangos_built_in_backend():
    # No django_redis installed in this project -- django-environ must fall back to
    # Django's own built-in RedisCache, not require the third-party package.
    env = environ.Env()
    config = env.cache_url_config("redis://cache:6379/0")
    assert config["BACKEND"] == "django.core.cache.backends.redis.RedisCache"
    assert config["LOCATION"] == "redis://cache:6379/0"


def test_env_cache_resolves_the_default_to_locmem():
    env = environ.Env()
    config = env.cache_url_config("locmemcache://")
    assert config["BACKEND"] == "django.core.cache.backends.locmem.LocMemCache"


@override_settings(DEBUG=False, CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
def test_check_warns_when_still_locmem_in_production():
    warnings = cache_backend_check(None)
    assert len(warnings) == 1
    assert isinstance(warnings[0], Warning)
    assert warnings[0].id == "annuaire.W002"


@override_settings(DEBUG=False, CACHES={"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache"}})
def test_check_is_silent_with_a_shared_backend_in_production():
    assert cache_backend_check(None) == []


@override_settings(DEBUG=True, CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
def test_check_is_silent_under_debug():
    assert cache_backend_check(None) == []
