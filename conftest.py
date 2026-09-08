import pytest
from django.conf import settings
from django.core.cache import cache


def pytest_configure():
    # The default PBKDF2 hasher is deliberately slow (~100-300ms/hash) for
    # production security. Tests don't need that strength and create many
    # accounts (populate_dev_data alone creates ~22 per call), so swap in a
    # fast hasher for the whole test session.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

    # Force LocMemCache for the whole test session regardless of a developer's local
    # CACHE_URL -- the suite must never depend on a real Valkey/Redis being reachable.
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

    # Force django-q2 into sync mode: async_task() runs the task inline, in-process,
    # instead of pushing it onto a real broker -- the suite must never need a real
    # Valkey/Redis queue either.
    settings.Q_CLUSTER = {**settings.Q_CLUSTER, "sync": True}


@pytest.fixture(autouse=True)
def _clear_cache():
    # LocMemCache persists across tests within one process, so without this a value
    # written by one test (e.g. a throttle counter) would leak into the next test that
    # happens to use the same key.
    cache.clear()
    yield
    cache.clear()
