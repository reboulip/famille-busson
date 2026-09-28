"""Template helpers for rendering a bulletin (ported from
design/bulletins/prototype/bulletin_tags.py).

Everything user-visible is built from escaped strings: package content can never
inject markup, whatever the transcription agent wrote.
"""

from __future__ import annotations

import re
from datetime import date

from django import template
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

from annuaire.templatetags.icons import icon as site_icon

register = template.Library()


@register.simple_tag
def bicon(name: str, size: int = 20) -> str:
    """Alias of the site's {% icon %} -- kept so the block templates lifted
    from the prototype (which use {% bicon %}) don't need editing."""
    return site_icon(name, size=size)


@register.filter
def get(mapping: dict, key: str):
    return mapping.get(key)


MARK_TAGS = {"bold": "strong", "italic": "em", "underline": "u", "strike": "s", "superscript": "sup"}
MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
MONTHS_LONG = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]

# French typography, display only: no line break before ; : ! ? » or after «.
_NBSP_BEFORE = re.compile(r" ([;:!?»])")
_NBSP_AFTER = re.compile(r"(«) ")


def fr_typography(text: str) -> str:
    text = _NBSP_BEFORE.sub("\u00a0\\1", text)
    return _NBSP_AFTER.sub("\\1\u00a0", text)


def _text(value: str) -> str:
    return escape(fr_typography(value))


def _wrap(html: str, marks) -> str:
    for mark in marks or ():
        tag = MARK_TAGS[mark]
        html = f"<{tag}>{html}</{tag}>"
    return html


def render_inline(value, images: dict) -> str:
    """Render an inline_text value (string or list of runs) to safe HTML."""
    if value is None:
        return ""
    if isinstance(value, str):
        return _text(value)
    parts = []
    for run in value:
        if isinstance(run, str):
            parts.append(_text(run))
            continue
        kind = run.get("kind")
        if kind == "break":
            parts.append("<br>")
        elif kind == "illegible":
            img = images[run["image"]]
            parts.append(
                format_html(
                    '<img class="fb-bulletin-ink fb-bulletin-illegible" src="{}" alt="{}" width="{}" height="{}">',
                    img["file"],
                    img["alt"],
                    img["width"] // 2,
                    img["height"] // 2,
                )
            )
        elif kind == "uncertain":
            alternatives = run.get("alternatives") or []
            hint = "Lecture incertaine"
            if alternatives:
                hint += " — autre lecture possible : " + ", ".join(alternatives)
            parts.append(
                '<span class="fb-bulletin-uncertain" tabindex="0" title="{hint}">{text}'
                '<span class="fb-bulletin-uncertain__mark" aria-hidden="true">?</span>'
                '<span class="visually-hidden"> ({hint})</span></span>'.format(
                    hint=escape(hint), text=_wrap(_text(run["text"]), run.get("marks"))
                )
            )
        else:
            parts.append(_wrap(_text(run["text"]), run.get("marks")))
    return "".join(parts)


@register.simple_tag(takes_context=True)
def inline(context, value):
    return mark_safe(render_inline(value, context["images"]))  # noqa: S308 -- escaped in render_inline


@register.filter
def typo(value: str) -> str:
    """Escape + French typography for plain-string fields (titles, captions...)."""
    return mark_safe(_text(value or ""))  # noqa: S308 -- escaped above


@register.filter
def pages_label(pages: list[int]) -> str:
    if not pages:
        return ""
    if len(pages) == 1:
        return f"p. {pages[0]}"
    if pages == list(range(pages[0], pages[-1] + 1)):
        return f"p. {pages[0]}–{pages[-1]}"
    return "p. " + ", ".join(str(p) for p in pages)


def _parse(value: str) -> date:
    return date.fromisoformat(value[:10])


@register.simple_tag
def event_badge(event: dict) -> str:
    """Tear-off-calendar badge: '11–12 nov. 1995' / '8–10 mai 1995' / '3 juin 1996'."""
    starts = [_parse(d["start"]) for d in event["dates"] if d.get("start")]
    ends = [_parse(d.get("end") or d["start"]) for d in event["dates"] if d.get("start")]
    if not starts:
        return ""
    first, last = min(starts), max(ends)
    if (first.year, first.month) == (last.year, last.month):
        days = f"{first.day}" if first == last else f"{first.day}–{last.day}"
        month = MONTHS[first.month - 1]
    else:
        days = f"{first.day}/{first.month}–{last.day}/{last.month}"
        month = ""
    return format_html(
        '<span class="fb-bulletin-event__badge" aria-hidden="true">'
        '<span class="fb-bulletin-event__month">{}</span><span class="fb-bulletin-event__days">{}</span>'
        '<span class="fb-bulletin-event__year">{}</span></span>',
        month,
        days,
        last.year,
    )


@register.filter
def long_date(partial: str) -> str:
    """'1995-04' -> 'avril 1995'; '2014-04-29' -> '29 avril 2014'; '1995' -> '1995'."""
    parts = partial.split("-")
    if len(parts) == 1:
        return parts[0]
    month = MONTHS_LONG[int(parts[1]) - 1]
    if len(parts) == 2:
        return f"{month} {parts[0]}"
    return f"{int(parts[2])} {month} {parts[0]}"


@register.filter
def heading_tag(level: int, base: int) -> str:
    return f"h{min(6, int(base) + int(level))}"


@register.filter
def join_names(names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " et " + names[-1]
