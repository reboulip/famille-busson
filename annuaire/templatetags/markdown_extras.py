from django import template
from django.utils.safestring import mark_safe

from annuaire.markdown_utils import markdown_to_text, render_markdown

register = template.Library()


@register.filter(name="markdown")
def markdown_filter(text):
    return mark_safe(render_markdown(text))


@register.filter(name="markdown_plain")
def markdown_plain_filter(text):
    return markdown_to_text(text)
