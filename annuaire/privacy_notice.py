"""Privacy notice acceptance tracking (14.3). A simple version string, not
semver -- has_accepted() only ever does an equality check, so there is no
need to compare versions as anything but opaque strings. Bump
PRIVACY_NOTICE_VERSION whenever the notice's substance changes; every
member's stored version then stops matching and they see the banner again."""

from __future__ import annotations

from django.utils import timezone

from .models import Account

PRIVACY_NOTICE_VERSION = "1"


def has_accepted(account: Account) -> bool:
    if not account or not account.is_authenticated:
        return False
    return bool(account.privacy_notice_accepted_at) and account.privacy_notice_version == PRIVACY_NOTICE_VERSION


def record_acceptance(account: Account) -> None:
    account.privacy_notice_accepted_at = timezone.now()
    account.privacy_notice_version = PRIVACY_NOTICE_VERSION
    account.save(update_fields=["privacy_notice_accepted_at", "privacy_notice_version"])
