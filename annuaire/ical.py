"""Hand-rolled RFC 5545 (iCalendar) writer -- no `icalendar` PyPI dependency.

Deliberate: the surface this project needs (VCALENDAR/VEVENT, CRLF line
endings, 75-octet line folding, TEXT-value escaping) is small, must stay
source-text testable like everything else here, and a dependency is one more
thing the weekly dependency-upgrade job carries forever.
"""

from __future__ import annotations

import datetime

from django.utils import timezone

from .calendar_data import CalendarEntry

_FOLD_LIMIT = 75  # octets, per RFC 5545 section 3.1


def _escape_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold_line(line: str) -> str:
    """Fold one unfolded content line to <=75 OCTETS per physical line,
    continuation lines prefixed with a single space, per RFC 5545 section 3.1.
    Folds by byte count, not character count, so a multi-byte UTF-8 sequence
    (accented French text) is never split mid-character."""
    data = line.encode("utf-8")
    if len(data) <= _FOLD_LIMIT:
        return line

    parts = []
    start = 0
    limit = _FOLD_LIMIT
    while start < len(data):
        end = min(start + limit, len(data))
        while end < len(data) and (data[end] & 0xC0) == 0x80:  # UTF-8 continuation byte
            end -= 1
        parts.append(data[start:end])
        start = end
        limit = _FOLD_LIMIT - 1  # continuation lines start with one space
    return "\r\n ".join(part.decode("utf-8") for part in parts)


def _format_datetime(dt: datetime.datetime) -> str:
    return dt.astimezone(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


def _format_date(d: datetime.date) -> str:
    return d.strftime("%Y%m%d")


def _render_event(entry: CalendarEntry, now: datetime.datetime) -> list[str]:
    lines = ["BEGIN:VEVENT", f"UID:{entry.uid}", f"DTSTAMP:{_format_datetime(now)}"]
    if entry.all_day:
        start_date = datetime.date.fromisoformat(entry.start[:10])
        # Inclusive end (calendar_data's convention) -- RFC 5545's DTEND for a
        # DATE value is EXCLUSIVE, so +1 day. This conversion happens here,
        # and only here.
        end_date = datetime.date.fromisoformat(entry.end[:10]) + datetime.timedelta(days=1)
        lines.append(f"DTSTART;VALUE=DATE:{_format_date(start_date)}")
        lines.append(f"DTEND;VALUE=DATE:{_format_date(end_date)}")
    else:
        lines.append(f"DTSTART:{_format_datetime(datetime.datetime.fromisoformat(entry.start))}")
        lines.append(f"DTEND:{_format_datetime(datetime.datetime.fromisoformat(entry.end))}")
    lines.append(f"SUMMARY:{_escape_text(entry.title)}")
    if entry.subtitle:
        lines.append(f"LOCATION:{_escape_text(entry.subtitle)}")
    if entry.url:
        lines.append(f"URL:{entry.url}")
    lines.append("END:VEVENT")
    return lines


def render_ics(entries: list[CalendarEntry]) -> bytes:
    """Render a list of CalendarEntry into a full .ics payload -- bytes,
    UTF-8, CRLF line endings, folded."""
    now = timezone.now()
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Famille Busson//Calendar//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for entry in entries:
        lines.extend(_render_event(entry, now))
    lines.append("END:VCALENDAR")
    folded = [_fold_line(line) for line in lines]
    return ("\r\n".join(folded) + "\r\n").encode("utf-8")
