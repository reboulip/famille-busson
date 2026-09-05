"""Inline SVG icon set.

Replaces the emoji previously used as iconography (📧 ☎️ 🏠 🎂 ✝ 📎 📥 ⛶ 🏔️).
Emoji render as tofu boxes wherever the system has no emoji font — visible in
the project's own screenshots — and they cannot be recoloured with the theme.

Every glyph is drawn on a 24×24 grid with `stroke="currentColor"`, so it takes
its colour from whatever it sits in and follows Alpenglow/Nightfall for free.
They are inlined rather than served as a sprite file so they cost no extra
request and no `collectstatic` url() reference.

Usage::

    {% load icons %}
    {% icon "mail" %}
    {% icon "home" css_class="fb-contact__icon" %}
    {% icon "trash" size=16 label="Supprimer" %}

(`css_class`, not `class` — the latter is a Python keyword and cannot be a
keyword argument name.)

`label` makes the glyph a labelled image for assistive tech; without it the
icon is marked `aria-hidden` and is assumed to sit next to real text.
"""

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

# Path data only — the wrapping <svg> is assembled in `icon()` below.
# Stroked (not filled) paths throughout, for one consistent weight.
_PATHS: dict[str, str] = {
    "mail": '<path d="M3 6.5h18v11H3z"/><path d="m3 7 9 6 9-6"/>',
    "phone": (
        '<path d="M8 3H5.5A1.5 1.5 0 0 0 4 4.6C4 13 11 20 19.4 20a1.5 1.5 0 0 0 1.6-1.5V16l-4-1.5'
        '-2 2A13 13 0 0 1 9.5 11l2-2z"/>'
    ),
    "home": '<path d="M4 10.5 12 4l8 6.5"/><path d="M6 10v10h12V10"/><path d="M10 20v-5h4v5"/>',
    "cake": (
        '<path d="M4 20h16"/><path d="M5 20v-6.5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2V20"/>'
        '<path d="M12 11.5V8"/><path d="M12 5.5a1.5 1.5 0 0 0 0-2c-.6.8-1 1.3-1 1.8a1 1 0 0 0 1 .2z"/>'
    ),
    "cross": '<path d="M12 21V5"/><path d="M7.5 9h9"/>',
    "clip": ('<path d="M18 8.5 10.5 16a3.5 3.5 0 0 1-5-5l8-8a2.5 2.5 0 0 1 3.5 3.5l-8 8"/>'),
    "download": '<path d="M12 4v11"/><path d="m7.5 10.5 4.5 4.5 4.5-4.5"/><path d="M4 20h16"/>',
    "expand": ('<path d="M4 9V4h5"/><path d="M20 9V4h-5"/><path d="M4 15v5h5"/><path d="M20 15v5h-5"/>'),
    "search": '<circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 4.5 4.5"/>',
    "link": (
        '<path d="M10 13.5a3.5 3.5 0 0 0 5 0l3-3a3.5 3.5 0 0 0-5-5l-1.5 1.5"/>'
        '<path d="M14 10.5a3.5 3.5 0 0 0-5 0l-3 3a3.5 3.5 0 0 0 5 5l1.5-1.5"/>'
    ),
    "image": ('<path d="M3 5.5h18v13H3z"/><circle cx="8.5" cy="10" r="1.5"/><path d="m3 16 5-4 4 3.5 3.5-3 5.5 5"/>'),
    "file": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/>',
    "folder": '<path d="M3 6h6l2 2.5h10V19H3z"/>',
    "lock": '<path d="M7 11V8a5 5 0 0 1 10 0v3"/><path d="M5 11h14v9H5z"/>',
    "tree": (
        '<circle cx="12" cy="5.5" r="2.5"/><circle cx="6" cy="18.5" r="2.5"/>'
        '<circle cx="18" cy="18.5" r="2.5"/><path d="M12 8v3.5"/><path d="M6 16v-2h12v2"/>'
    ),
    "trash": ('<path d="M4 7h16"/><path d="M9 7V4.5h6V7"/><path d="M6.5 7 7.5 20h9L17.5 7"/>'),
    "edit": '<path d="m4 20 1-4L16.5 4.5a2.1 2.1 0 0 1 3 3L8 19z"/><path d="M14.5 6.5l3 3"/>',
    "plus": '<path d="M12 5v14"/><path d="M5 12h14"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7"/>',
    "alert": '<path d="M12 4 2.5 20h19z"/><path d="M12 10v4"/><path d="M12 17h.01"/>',
    "info": '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5"/><path d="M12 8h.01"/>',
    "sun": (
        '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2"/><path d="M12 19.5v2"/>'
        '<path d="M2.5 12h2"/><path d="M19.5 12h2"/><path d="m5.2 5.2 1.4 1.4"/>'
        '<path d="m17.4 17.4 1.4 1.4"/><path d="m18.8 5.2-1.4 1.4"/><path d="m6.6 17.4-1.4 1.4"/>'
    ),
    "moon": '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z"/>',
    "menu": '<path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h16"/>',
    "logout": '<path d="M14 5H5v14h9"/><path d="M17 8.5 20.5 12 17 15.5"/><path d="M20 12h-9"/>',
    "chevron-left": '<path d="m14.5 5.5-6 6.5 6 6.5"/>',
    "chevron-right": '<path d="m9.5 5.5 6 6.5-6 6.5"/>',
}


@register.simple_tag(name="icon")
def icon(name: str, size: int = 20, css_class: str = "", label: str = "") -> str:
    """Render one glyph from the set as an inline ``<svg>``."""
    paths = _PATHS.get(name)
    if paths is None:  # A typo should be loud in dev, not silently invisible.
        raise template.TemplateSyntaxError(f"Unknown icon {name!r}. Known icons: {', '.join(sorted(_PATHS))}")

    classes = f"fb-icon {css_class}".strip()
    if label:
        a11y = f'role="img" aria-label="{escape(label)}"'
    else:
        a11y = 'aria-hidden="true" focusable="false"'

    return mark_safe(  # noqa: S308 — every part is either literal or escaped above.
        f'<svg class="{escape(classes)}" width="{int(size)}" height="{int(size)}" '
        f'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        f'stroke-linecap="round" stroke-linejoin="round" {a11y}>{paths}</svg>'
    )
