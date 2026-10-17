"""Regression guards for the unified calendar's month-grid rewrite (#154). No JS test
runner in this project -- assert on unified_calendar.js/main.css source text, mirroring
test_carte_marker_cluster.py's approach."""

import re
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
UNIFIED_CALENDAR_JS = STATIC_DIR / "js" / "unified_calendar.js"
MAIN_CSS = STATIC_DIR / "css" / "main.css"


def _js() -> str:
    return UNIFIED_CALENDAR_JS.read_text(encoding="utf-8")


def _navigate_body() -> str:
    content = _js()
    start = content.index("function navigate(")
    end = content.index("\n        function render(")
    return content[start:end]


def test_iso_date_does_not_use_to_iso_string():
    # toISOString() converts to UTC first, which can shift local midnight to
    # the previous day and silently drop the last day of a fetch window.
    content = _js()
    start = content.index("function isoDate(")
    end = content.index("\n        function normalizeEntry(")
    body = content[start:end]
    assert "toISOString" not in body


def test_navigate_does_not_send_a_stale_types_filter():
    # Sending only the currently-active types meant re-enabling a type after
    # navigating never refetched it. Filtering happens client-side in render().
    body = _navigate_body()
    assert "types:" not in body
    assert re.search(r"types\s*[:=]", body) is None


def test_navigate_checks_the_response_and_handles_a_failed_fetch():
    body = _navigate_body()
    assert ".ok" in body
    assert ".catch(" in body


def test_weekday_header_is_built():
    content = _js()
    assert "cal-month-weekday" in content
    assert "renderWeekdayHeader" in content


def test_month_grid_adds_trailing_filler_cells():
    content = _js()
    assert "trailing" in content
    assert "cal-month-cell--empty" in content


def test_day_cells_use_titled_entries_not_bare_dots():
    content = _js()
    assert "cal-month-cell__entries" in content
    assert "cal-month-entry" in content
    assert "cal-month-cell__dots" not in content


def test_presences_are_grouped_one_chip_per_place():
    content = _js()
    assert "byPlace" in content


def test_month_label_and_weekday_names_use_the_page_language():
    content = _js()
    assert "document.documentElement.lang" in content
    assert "'fr-FR'" not in content


def test_css_defines_the_new_grid_classes_and_a_mobile_collapse():
    css = MAIN_CSS.read_text(encoding="utf-8")
    for selector in (
        ".cal-month-weekday",
        ".cal-month-cell__entries",
        ".cal-month-entry",
        ".cal-month-more",
        ".cal-month-cell--weekend",
    ):
        assert selector in css
    assert "max-width: 767.98px" in css
