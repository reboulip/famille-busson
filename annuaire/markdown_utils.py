import html
import re

import markdown as _markdown
import nh3

MAX_MARKDOWN_LENGTH = 100_000

_MARKDOWN_EXTENSIONS = ["nl2br", "fenced_code", "tables", "sane_lists"]
_ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}

_TAG_RE = re.compile(r"<[^>]+>")


def render_markdown(text: str | None) -> str:
    """Render Markdown source to sanitized HTML. Never raises on None/empty input."""
    if not text:
        return ""
    rendered_html = _markdown.markdown(text, extensions=_MARKDOWN_EXTENSIONS)
    return nh3.clean(rendered_html, url_schemes=_ALLOWED_URL_SCHEMES)


def markdown_to_text(text: str | None) -> str:
    """Render Markdown then strip all tags, for plain-text excerpts (cards, tiles)."""
    if not text:
        return ""
    rendered = render_markdown(text)
    stripped = _TAG_RE.sub(" ", rendered)
    return re.sub(r"\s+", " ", html.unescape(stripped)).strip()
