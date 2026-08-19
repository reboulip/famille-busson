from django.conf import settings


def pytest_configure():
    # The default PBKDF2 hasher is deliberately slow (~100-300ms/hash) for
    # production security. Tests don't need that strength and create many
    # accounts (populate_dev_data alone creates ~22 per call), so swap in a
    # fast hasher for the whole test session.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
