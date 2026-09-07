import pytest
from django import template
from django.template import Context, Template

from annuaire.templatetags.icons import _PATHS, icon


def _render(source: str, **context) -> str:
    return Template("{% load icons %}" + source).render(Context(context))


def test_icon_renders_an_inline_svg():
    html = icon("mail")
    assert html.startswith("<svg")
    assert html.endswith("</svg>")
    assert 'viewBox="0 0 24 24"' in html


def test_icon_uses_currentcolor_so_it_follows_the_theme():
    # The whole point of dropping emoji: a glyph that takes its colour from the text
    # around it works in Alpenglow and Nightfall without a second asset.
    assert 'stroke="currentColor"' in icon("home")
    assert "fill=" not in icon("home").split(">")[0].replace('fill="none"', "")


def test_icon_is_hidden_from_assistive_tech_without_a_label():
    html = icon("phone")
    assert 'aria-hidden="true"' in html
    assert "aria-label" not in html


def test_icon_with_a_label_is_exposed_as_an_image():
    html = icon("trash", label="Supprimer")
    assert 'role="img"' in html
    assert 'aria-label="Supprimer"' in html
    assert "aria-hidden" not in html


def test_icon_label_is_escaped():
    html = icon("trash", label='Supprimer "tout" <maintenant>')
    assert "<maintenant>" not in html
    assert "&lt;maintenant&gt;" in html


def test_icon_size_sets_both_dimensions():
    html = icon("plus", size=16)
    assert 'width="16"' in html
    assert 'height="16"' in html


def test_icon_merges_extra_classes_with_the_base_class():
    html = icon("cake", css_class="fb-contact__icon")
    assert 'class="fb-icon fb-contact__icon"' in html


def test_unknown_icon_raises_rather_than_rendering_nothing():
    # A typo that silently rendered an invisible glyph would be found in production,
    # not in dev.
    with pytest.raises(template.TemplateSyntaxError) as excinfo:
        icon("definitely-not-an-icon")
    assert "definitely-not-an-icon" in str(excinfo.value)


def test_icon_tag_is_usable_from_a_template():
    assert "<svg" in _render('{% icon "search" %}')


def test_icon_tag_accepts_css_class_and_label_from_a_template():
    html = _render('{% icon "lock" size=16 css_class="x" label="Verrouillé" %}')
    assert 'class="fb-icon x"' in html
    assert 'aria-label="Verrouillé"' in html


@pytest.mark.parametrize("name", sorted(_PATHS))
def test_every_icon_in_the_set_renders(name):
    html = icon(name)
    assert html.startswith("<svg")
    assert len(html) > 60  # not an empty shell


def test_the_set_covers_every_glyph_the_templates_ask_for():
    """Guard against a template referencing an icon that was never drawn -- that
    raises at render time, i.e. a 500 on a page nobody happened to open in dev."""
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent.parent
    used: set[str] = set()
    for template_dir in ("annuaire", "publications", "documents", "photos", "events"):
        for path in (root / template_dir).rglob("*.html"):
            used |= set(re.findall(r'{%\s*icon\s+"([\w-]+)"', path.read_text(encoding="utf-8")))

    assert used, "no {% icon %} usages found -- has the tag been renamed?"
    assert used <= set(_PATHS), f"templates use undrawn icons: {sorted(used - set(_PATHS))}"
