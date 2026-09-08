from annuaire.calendar_data import CalendarEntry
from annuaire.ical import render_ics


def _entry(
    *,
    type="event",
    title="Barbecue",
    subtitle="",
    start="2026-07-14",
    end="2026-07-14",
    all_day=True,
    url="/annuaire/evenements/1/",
    uid="event-1@example.com",
):
    return CalendarEntry(
        type=type, title=title, subtitle=subtitle, start=start, end=end, all_day=all_day, url=url, uid=uid
    )


def test_render_ics_produces_crlf_line_endings():
    body = render_ics([_entry()])
    text = body.decode("utf-8")
    assert "\r\n" in text
    # No bare LF -- every line ending is CRLF.
    assert "\n" not in text.replace("\r\n", "")


def test_render_ics_wraps_in_vcalendar():
    body = render_ics([_entry()]).decode("utf-8")
    assert "BEGIN:VCALENDAR" in body
    assert "VERSION:2.0" in body
    assert "END:VCALENDAR" in body


def test_render_ics_one_vevent_per_entry():
    body = render_ics([_entry(uid="a"), _entry(uid="b")]).decode("utf-8")
    assert body.count("BEGIN:VEVENT") == 2
    assert body.count("END:VEVENT") == 2


def test_render_ics_all_day_dtend_is_exclusive():
    """Inclusive end (calendar_data's convention) -> exclusive DTEND;VALUE=DATE
    per RFC 5545. This is the single most likely bug in this item."""
    body = render_ics([_entry(start="2026-07-14", end="2026-07-14", all_day=True)]).decode("utf-8")
    assert "DTSTART;VALUE=DATE:20260714" in body
    assert "DTEND;VALUE=DATE:20260715" in body


def test_render_ics_all_day_multi_day_dtend():
    body = render_ics([_entry(start="2026-07-14", end="2026-07-16", all_day=True)]).decode("utf-8")
    assert "DTSTART;VALUE=DATE:20260714" in body
    assert "DTEND;VALUE=DATE:20260717" in body


def test_render_ics_datetime_entry_uses_utc():
    body = render_ics(
        [_entry(start="2026-07-14T12:00:00+02:00", end="2026-07-14T14:00:00+02:00", all_day=False)]
    ).decode("utf-8")
    assert "DTSTART:20260714T100000Z" in body
    assert "DTEND:20260714T120000Z" in body


def test_render_ics_escapes_comma_semicolon_and_newline_in_summary():
    body = render_ics([_entry(title="Réunion; famille, annuelle\ndeux parties")]).decode("utf-8")
    assert "Réunion\\; famille\\, annuelle\\ndeux parties" in body.replace("\r\n ", "")


def test_render_ics_includes_location_when_subtitle_present():
    body = render_ics([_entry(subtitle="Chalet des Alpes")]).decode("utf-8")
    assert "LOCATION:Chalet des Alpes" in body


def test_render_ics_omits_location_when_no_subtitle():
    body = render_ics([_entry(subtitle="")]).decode("utf-8")
    assert "LOCATION:" not in body


def test_render_ics_uid_is_preserved():
    body = render_ics([_entry(uid="event-42@example.com")]).decode("utf-8")
    assert "UID:event-42@example.com" in body


def test_render_ics_folds_long_lines_under_75_octets():
    long_title = "Un titre extrêmement long qui dépasse largement soixante-quinze octets pour tester le pliage"
    body = render_ics([_entry(title=long_title)]).decode("utf-8")
    for line in body.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75 or line.startswith(" ")
