"""The annuaire.W004 check -- warns when a configured language has a .po but no compiled .mo."""

import tempfile
from pathlib import Path

from django.core.checks import Warning
from django.test import override_settings

from annuaire.checks import compiled_locale_check


def _locale_dir_with(*, po: bool, mo: bool) -> Path:
    tmp = Path(tempfile.mkdtemp())
    lc_messages = tmp / "fr" / "LC_MESSAGES"
    lc_messages.mkdir(parents=True)
    if po:
        (lc_messages / "django.po").write_text("")
    if mo:
        (lc_messages / "django.mo").write_text("")
    return tmp


def test_warns_when_po_exists_without_compiled_mo_in_production():
    locale_dir = _locale_dir_with(po=True, mo=False)
    with override_settings(DEBUG=False, LOCALE_PATHS=[locale_dir], LANGUAGES=[("fr", "Français")]):
        warnings = compiled_locale_check(None)
    assert len(warnings) == 1
    assert isinstance(warnings[0], Warning)
    assert warnings[0].id == "annuaire.W004"


def test_silent_when_mo_is_compiled_in_production():
    locale_dir = _locale_dir_with(po=True, mo=True)
    with override_settings(DEBUG=False, LOCALE_PATHS=[locale_dir], LANGUAGES=[("fr", "Français")]):
        assert compiled_locale_check(None) == []


def test_silent_when_po_is_absent_in_production():
    locale_dir = _locale_dir_with(po=False, mo=False)
    with override_settings(DEBUG=False, LOCALE_PATHS=[locale_dir], LANGUAGES=[("fr", "Français")]):
        assert compiled_locale_check(None) == []


def test_silent_under_debug():
    locale_dir = _locale_dir_with(po=True, mo=False)
    with override_settings(DEBUG=True, LOCALE_PATHS=[locale_dir], LANGUAGES=[("fr", "Français")]):
        assert compiled_locale_check(None) == []
