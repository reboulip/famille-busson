import html
import re

import markdown as _markdown
import nh3
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

MAX_MARKDOWN_LENGTH = 100_000

# Bullets (*, +, -) always start a list; ordered lists only on an exact "1." marker
# (never "1)", never e.g. "1999.") -- mirrors CommonMark and avoids turning a line like
# "il est né en\n1999. C'était..." into an <ol start="1999">. Requires whitespace then a
# non-whitespace character after the marker so "*italique*" alone on a line is untouched.
_LIST_MARKER_RE = re.compile(r"^ {0,3}(?:[*+\-]|1\.)[ \t]+\S")


class _ListInterruptsParagraphPreprocessor(Preprocessor):
    """Inserts a blank line before a list-marker line that directly follows a
    non-blank, non-list-marker line. Python-Markdown's block parser splits input on
    blank lines *before* any list-specific processor runs, so "Texte\\n- item" is a
    single block that a list marker can never interrupt -- no extension flag changes
    this, only pre-splitting the blocks does."""

    def run(self, lines):
        new_lines = []
        previous_line = None
        for line in lines:
            if (
                _LIST_MARKER_RE.match(line)
                and previous_line is not None
                and previous_line.strip() != ""
                and not _LIST_MARKER_RE.match(previous_line)
            ):
                new_lines.append("")
            new_lines.append(line)
            previous_line = line
        return new_lines


class _ListInterruptsParagraphExtension(Extension):
    def extendMarkdown(self, md):
        # Priority 19: after fenced_code_block (25) and html_block (20) have already
        # stashed their content -- so fenced code and raw HTML are immune for free --
        # but before reference (15).
        md.preprocessors.register(_ListInterruptsParagraphPreprocessor(md), "list_interrupts_paragraph", 19)


_MARKDOWN_EXTENSIONS = ["nl2br", "fenced_code", "tables", "sane_lists", _ListInterruptsParagraphExtension()]
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
